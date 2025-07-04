"""
Production RAG Agent
LangGraph 기반의 고도화된 RAG 시스템
"""

import hashlib
import json
import logging
import os
import time
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

from flashrank import Ranker, RerankRequest
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import structlog

from src.config.rag_config import RAGConfig
from src.schemas.rag import RAGSearchResult, RAGSearchStep, RAGSearchDocument

# 구조화된 로깅 설정
logger = structlog.get_logger()


# ============ LangGraph 상태 정의 ============

class GraphState(TypedDict):
    """LangGraph 상태 정의"""
    question: str
    documents: List[Document]
    generation: str
    iterations: int
    search_steps: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# ============ 안정적인 LLM 출력을 위한 Pydantic 모델 ============

class GradeDocuments(BaseModel):
    """문서 품질 평가 모델"""
    is_relevant: bool = Field(description="문서가 질문에 답변하기에 관련성이 높으면 True")
    reason: str = Field(description="관련성 판단에 대한 간략한 이유")
    confidence: float = Field(ge=0.0, le=1.0, description="판단 신뢰도 (0-1)")


class SearchMetadata(BaseModel):
    """검색 메타데이터"""
    total_execution_time: float
    retrieval_time: float
    rerank_time: float
    generation_time: float
    retrieved_count: int
    reranked_count: int
    iterations: int


# ============ Production RAG Agent ============

class ProductionRAGAgent:
    """Production-Level RAG Agent"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.llm = ChatOllama(
            model=self.config.llm_model,
            base_url=self.config.ollama_base_url,
            temperature=0,
            format="json"
        )
        self.generation_llm = ChatOllama(
            model=self.config.llm_model,
            base_url=self.config.ollama_base_url,
            temperature=0.1
        )
        self.embeddings = OllamaEmbeddings(
            model=self.config.embedding_model,
            base_url=self.config.ollama_base_url
        )
        
        # Re-ranker 초기화
        try:
            self.reranker = Ranker(
                model_name=self.config.reranker_model,
                cache_dir=self.config.reranker_cache_dir
            )
            logger.info(f"Re-ranker '{self.config.reranker_model}' 초기화 완료")
        except Exception as e:
            logger.warning(f"Re-ranker 초기화 실패: {e}. 재순위화 없이 진행")
            self.reranker = None
        
        self.workflow = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        logger.info("LangGraph 워크플로우 구성 시작")
        
        workflow = StateGraph(GraphState)
        
        # 노드 추가
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("rerank", self.rerank)
        workflow.add_node("generate", self.generate)
        workflow.add_node("transform_query", self.transform_query)
        
        # 엣지 연결
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("transform_query", "retrieve")
        workflow.add_edge("generate", END)
        
        # 조건부 엣지 (품질 검사)
        workflow.add_conditional_edges(
            "rerank",
            self.grade_documents,
            {
                "generate": "generate",
                "transform_query": "transform_query",
            }
        )
        
        app = workflow.compile()
        logger.info("LangGraph 워크플로우 컴파일 완료")
        return app
    
    async def create_collection(self, collection_name: str) -> bool:
        """Qdrant 컬렉션 생성"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams
            
            client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key
            )
            
            # 임베딩 차원 확인 (bge-m3는 1024 차원)
            vector_size = 1024
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Qdrant 컬렉션 '{collection_name}' 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant 컬렉션 생성 실패: {e}")
            return False
    
    async def upload_and_process_document(
        self,
        collection_name: str,
        file_path: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """문서 업로드 및 처리"""
        start_time = time.time()
        
        try:
            # 문서 로드
            logger.info(f"문서 로드 시작: {file_path}")
            
            # 파일 확장자에 따른 로더 선택
            docs = None
            if file_path.lower().endswith('.pdf'):
                try:
                    from langchain_community.document_loaders import PyPDFLoader
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                except ImportError:
                    logger.warning("PyPDFLoader 사용 불가, docling 사용")
                    docs = self._load_with_docling(file_path)
            else:
                # docling으로 다양한 문서 타입 처리
                docs = self._load_with_docling(file_path)
            
            if not docs:
                raise ValueError("문서를 로드할 수 없습니다")
            
            # 문서 분할
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
            splits = text_splitter.split_documents(docs)
            
            # 메타데이터 추가
            for split in splits:
                if document_metadata:
                    split.metadata.update(document_metadata)
                
                # 파일 해시 추가
                split.metadata['file_path'] = file_path
                split.metadata['chunk_id'] = hashlib.md5(
                    (split.page_content + str(split.metadata)).encode()
                ).hexdigest()
            
            # Qdrant에 저장
            logger.info(f"벡터 저장 시작: {len(splits)}개 청크")
            
            from qdrant_client import QdrantClient
            
            client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key
            )
            
            vectorstore = Qdrant.from_documents(
                splits,
                self.embeddings,
                client=client,
                collection_name=collection_name,
                force_recreate=False
            )
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "chunks_created": len(splits),
                "vectors_stored": len(splits),
                "processing_time": processing_time,
                "file_path": file_path
            }
            
            logger.info(f"문서 처리 완료: {result}")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "file_path": file_path
            }
            logger.error(f"문서 처리 실패: {error_result}")
            return error_result
    
    async def search(
        self,
        collection_name: str,
        query: str,
        include_metadata: bool = True
    ) -> RAGSearchResult:
        """RAG 검색 실행"""
        start_time = time.time()
        
        try:
            # Qdrant 벡터 스토어 연결
            from qdrant_client import QdrantClient
            
            client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key
            )
            
            vectorstore = Qdrant(
                client=client,
                collection_name=collection_name,
                embeddings=self.embeddings
            )
            
            # Retriever 설정
            retriever = vectorstore.as_retriever(
                search_kwargs={"k": self.config.retriever_k}
            )
            
            # 워크플로우 실행
            inputs = {
                "question": query,
                "documents": [],
                "generation": "",
                "iterations": 0,
                "search_steps": [],
                "metadata": {"collection_name": collection_name}
            }
            
            # Retriever를 상태에 추가
            self._current_retriever = retriever
            
            final_state = self.workflow.invoke(inputs)
            
            total_time = time.time() - start_time
            
            # 검색된 문서 변환
            search_documents = []
            for doc in final_state.get("documents", []):
                # NumPy 타입을 Python 기본 타입으로 변환
                score = doc.metadata.get("score", 0.0)
                if hasattr(score, 'item'):  # NumPy 타입인 경우
                    score = float(score.item())
                else:
                    score = float(score)
                
                # 메타데이터의 모든 NumPy 타입 변환
                clean_metadata = self._convert_numpy_in_dict(doc.metadata) if include_metadata else {}
                
                search_doc = RAGSearchDocument(
                    document_id=doc.metadata.get("chunk_id", "unknown"),
                    filename=doc.metadata.get("file_path", "unknown"),
                    content=doc.page_content,
                    score=score,
                    metadata=clean_metadata
                )
                search_documents.append(search_doc)
            
            # 검색 단계 변환
            search_steps = []
            for step_data in final_state.get("search_steps", []):
                # 단계 데이터의 NumPy 타입 변환
                clean_step_data = self._convert_numpy_in_dict(step_data)
                step = RAGSearchStep(**clean_step_data)
                search_steps.append(step)
            
            # 메타데이터 구성
            metadata = SearchMetadata(
                total_execution_time=total_time,
                retrieval_time=sum(s.execution_time for s in search_steps if s.step_name == "retrieve"),
                rerank_time=sum(s.execution_time for s in search_steps if s.step_name == "rerank"),
                generation_time=sum(s.execution_time for s in search_steps if s.step_name == "generate"),
                retrieved_count=len([s for s in search_steps if s.step_name == "retrieve"]),
                reranked_count=len(search_documents),
                iterations=final_state.get("iterations", 0)
            )
            
            # 메타데이터 딕셔너리에서도 NumPy 타입 변환
            clean_metadata_dict = self._convert_numpy_in_dict(metadata.dict())
            
            result = RAGSearchResult(
                query=query,
                response=final_state.get("generation", ""),
                retrieved_documents=search_documents,
                search_steps=search_steps,
                total_execution_time=total_time,
                metadata=clean_metadata_dict
            )
            
            logger.info(f"RAG 검색 완료: {query[:50]}... (실행시간: {total_time:.2f}초)")
            return result
            
        except Exception as e:
            logger.error(f"RAG 검색 실패: {e}")
            raise
    
    def _convert_numpy_in_dict(self, data):
        """딕셔너리 내의 모든 NumPy 타입을 Python 기본 타입으로 변환"""
        if isinstance(data, dict):
            return {k: self._convert_numpy_in_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_numpy_in_dict(item) for item in data]
        elif hasattr(data, 'item'):  # NumPy 타입인 경우
            return data.item()
        else:
            return data
    
    async def delete_document_vectors(
        self,
        collection_name: str,
        document_id: str
    ) -> bool:
        """특정 문서의 벡터 데이터를 Qdrant에서 삭제"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            
            client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key
            )
            
            # 문서 ID로 벡터 검색 및 삭제
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            # 삭제할 벡터 ID 조회
            search_result = client.scroll(
                collection_name=collection_name,
                scroll_filter=filter_condition,
                limit=10000,  # 충분히 큰 수
                with_payload=True,
                with_vectors=False
            )
            
            if search_result[0]:  # 벡터가 존재하는 경우
                vector_ids = [point.id for point in search_result[0]]
                
                # 벡터 삭제
                client.delete(
                    collection_name=collection_name,
                    points_selector=vector_ids
                )
                
                logger.info(f"문서 {document_id}의 벡터 {len(vector_ids)}개 삭제 완료")
                return True
            else:
                logger.info(f"문서 {document_id}에 해당하는 벡터가 없습니다")
                return True
            
        except Exception as e:
            logger.error(f"벡터 삭제 실패: {e}")
            return False
    
    # ============ 그래프 노드 구현 ============
    
    def retrieve(self, state: GraphState) -> GraphState:
        """문서 검색 노드"""
        start_time = time.time()
        
        logger.info(f"문서 검색 시작: '{state['question']}'")
        
        try:
            documents = self._current_retriever.invoke(state["question"])
            
            execution_time = time.time() - start_time
            
            step_data = {
                "step_name": "retrieve",
                "description": "초기 문서 검색",
                "input_data": {"query": state["question"], "k": self.config.retriever_k},
                "output_data": {"documents_found": len(documents)},
                "execution_time": execution_time,
                "status": "completed"
            }
            
            search_steps = state.get("search_steps", [])
            search_steps.append(step_data)
            
            return {
                "documents": documents,
                "question": state["question"],
                "iterations": state.get("iterations", 0) + 1,
                "search_steps": search_steps,
                "metadata": state.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return state
    
    def rerank(self, state: GraphState) -> GraphState:
        """문서 재순위화 노드"""
        start_time = time.time()
        
        logger.info("문서 재순위화 시작")
        
        question = state["question"]
        documents = state["documents"]
        
        try:
            if not documents or not self.reranker:
                logger.warning("재순위화할 문서가 없거나 re-ranker를 사용할 수 없음")
                return state
            
            # FlashRank 재순위화
            passages = [
                {"id": i, "text": doc.page_content}
                for i, doc in enumerate(documents)
            ]
            
            rerank_request = RerankRequest(query=question, passages=passages)
            reranked_results = self.reranker.rerank(rerank_request)
            
            # 상위 N개 선택
            reranked_docs = [
                documents[res['id']] for res in reranked_results
            ][:self.config.rerank_top_n]
            
            # 점수 메타데이터 추가
            for i, doc in enumerate(reranked_docs):
                if i < len(reranked_results):
                    doc.metadata['score'] = reranked_results[i]['score']
            
            execution_time = time.time() - start_time
            
            step_data = {
                "step_name": "rerank",
                "description": "문서 재순위화",
                "input_data": {"documents_count": len(documents)},
                "output_data": {"reranked_count": len(reranked_docs)},
                "execution_time": execution_time,
                "status": "completed"
            }
            
            search_steps = state.get("search_steps", [])
            search_steps.append(step_data)
            
            logger.info(f"재순위화 완료: {len(reranked_docs)}개 문서 선택")
            
            return {
                "documents": reranked_docs,
                "question": question,
                "iterations": state["iterations"],
                "search_steps": search_steps,
                "metadata": state.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"재순위화 실패: {e}")
            return state
    
    def generate(self, state: GraphState) -> GraphState:
        """답변 생성 노드"""
        start_time = time.time()
        
        logger.info("답변 생성 시작")
        
        question = state["question"]
        documents = state["documents"]
        
        try:
            prompt = PromptTemplate(
                template="""다음 문서를 바탕으로 한국어로 친절하고 상세하게 답변하세요.
                답변은 정확하고 근거를 바탕으로 해야 하며, 문서에 없는 내용은 추측하지 마세요.

[문서]
{context}

[질문]
{question}

[답변]""",
                input_variables=["context", "question"],
            )
            
            rag_chain = prompt | self.generation_llm | StrOutputParser()
            
            context = "\n---\n".join([doc.page_content for doc in documents])
            generation = rag_chain.invoke({
                "context": context,
                "question": question
            })
            
            execution_time = time.time() - start_time
            
            step_data = {
                "step_name": "generate",
                "description": "최종 답변 생성",
                "input_data": {"context_length": len(context), "question": question},
                "output_data": {"response_length": len(generation)},
                "execution_time": execution_time,
                "status": "completed"
            }
            
            search_steps = state.get("search_steps", [])
            search_steps.append(step_data)
            
            logger.info(f"답변 생성 완료: {generation[:100]}...")
            
            return {
                "generation": generation,
                "search_steps": search_steps,
                **state
            }
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return {**state, "generation": "답변 생성 중 오류가 발생했습니다."}
    
    def transform_query(self, state: GraphState) -> GraphState:
        """질문 재구성 노드"""
        start_time = time.time()
        
        logger.info("질문 재구성 시작")
        
        question = state["question"]
        
        try:
            prompt = PromptTemplate(
                template="""당신은 사용자의 의도를 파악하여 더 나은 검색 결과를 얻을 수 있도록 
질문을 재구성하는 전문가입니다.

이전 검색 결과가 만족스럽지 않았습니다. 사용자의 원래 질문을 바탕으로, 
벡터 데이터베이스에서 더 관련성 높은 문서를 찾을 수 있도록 질문을 한국어로 다시 작성하세요.

원래 질문의 핵심 의미는 유지하되, 더 명확하고 구체적인 키워드를 포함시켜주세요.
다른 설명 없이 재구성된 질문만 생성하세요.

원래 질문: {question}""",
                input_variables=["question"],
            )
            
            chain = prompt | self.generation_llm | StrOutputParser()
            better_question = chain.invoke({"question": question})
            
            execution_time = time.time() - start_time
            
            step_data = {
                "step_name": "transform_query",
                "description": "질문 재구성",
                "input_data": {"original_question": question},
                "output_data": {"transformed_question": better_question},
                "execution_time": execution_time,
                "status": "completed"
            }
            
            search_steps = state.get("search_steps", [])
            search_steps.append(step_data)
            
            logger.info(f"질문 재구성 완료: {better_question}")
            
            return {
                "question": better_question,
                "documents": [],
                "iterations": state["iterations"],
                "search_steps": search_steps,
                "metadata": state.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"질문 재구성 실패: {e}")
            return state
    
    def grade_documents(self, state: GraphState) -> str:
        """문서 품질 평가"""
        logger.info("문서 품질 평가 시작")
        
        # 무한 루프 방지
        if state["iterations"] > 3:
            logger.warning("최대 반복 횟수 초과, 답변 생성으로 이동")
            return "generate"
        
        question = state["question"]
        documents = state["documents"]
        
        if not documents:
            logger.warning("평가할 문서가 없음, 질문 재구성으로 이동")
            return "transform_query"
        
        try:
            prompt = PromptTemplate(
                template="""당신은 주어진 문서가 사용자의 질문에 답변하기에 충분한 정보를 
포함하고 있는지 평가하는 AI입니다.
제공된 JSON 형식에 맞춰 응답해주세요.

[사용자 질문]
{question}

[검색된 문서]
{documents}

[출력 형식]
{format_instructions}
""",
                input_variables=["question", "documents"],
                partial_variables={
                    "format_instructions": JsonOutputParser(
                        pydantic_object=GradeDocuments
                    ).get_format_instructions()
                },
            )
            
            parser = JsonOutputParser(pydantic_object=GradeDocuments)
            chain = prompt | self.llm | parser
            
            grade = chain.invoke({
                "question": question,
                "documents": "\n---\n".join([doc.page_content for doc in documents])
            })
            
            if grade['is_relevant']:
                logger.info(f"문서 품질 평가: 관련성 높음 - {grade['reason']}")
                return "generate"
            else:
                logger.info(f"문서 품질 평가: 관련성 낮음 - {grade['reason']}")
                return "transform_query"
                
        except Exception as e:
            logger.error(f"문서 품질 평가 실패: {e}, 질문 재구성으로 이동")
            return "transform_query"
    
    def _load_with_docling(self, file_path: str) -> List[Document]:
        """Docling을 사용하여 문서 로드"""
        try:
            from docling.document_converter import DocumentConverter
            
            logger.info(f"Docling으로 문서 로드: {file_path}")
            
            # DocumentConverter 초기화
            converter = DocumentConverter()
            
            # 문서 변환
            conv_result = converter.convert(file_path)
            
            # LangChain Document 형태로 변환
            documents = []
            
            # 문서의 각 페이지를 별도 Document로 생성
            for page_no, page in enumerate(conv_result.document.pages):
                page_content = ""
                
                # 페이지의 모든 텍스트 요소 수집
                for element in page.elements:
                    if hasattr(element, 'text') and element.text:
                        page_content += element.text + "\n"
                
                if page_content.strip():
                    doc = Document(
                        page_content=page_content.strip(),
                        metadata={
                            "source": file_path,
                            "page": page_no + 1,
                            "total_pages": len(conv_result.document.pages),
                            "loader": "docling"
                        }
                    )
                    documents.append(doc)
            
            logger.info(f"Docling 문서 로드 완료: {len(documents)}개 페이지")
            return documents
            
        except Exception as e:
            logger.error(f"Docling 문서 로드 실패: {e}")
            # 폴백: UnstructuredFileLoader 사용
            try:
                from langchain_community.document_loaders import UnstructuredFileLoader
                logger.warning("Docling 실패, UnstructuredFileLoader 사용")
                loader = UnstructuredFileLoader(file_path)
                return loader.load()
            except Exception as fallback_error:
                logger.error(f"폴백 로더도 실패: {fallback_error}")
                raise ValueError(f"문서 로드 실패: {e}")