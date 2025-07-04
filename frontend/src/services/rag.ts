/**
 * RAG API Service
 * RAG 컬렉션, 문서, 검색 관련 API 클라이언트
 */

import { apiClient } from './api';

// ============ Types ============

export enum RAGCollectionStatus {
  ACTIVE = 'active',
  LEARNING = 'learning',
  ERROR = 'error',
  INACTIVE = 'inactive'
}

export enum RAGDocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  ERROR = 'error',
  DELETED = 'deleted'
}

export enum RAGDocumentType {
  PDF = 'pdf',
  DOCX = 'docx',
  TXT = 'txt',
  MD = 'md',
  HTML = 'html'
}

export interface RAGCollection {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  status: RAGCollectionStatus;
  document_count: number;
  vector_count: number;
  qdrant_collection_name: string;
  created_by: string;
  updated_by?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface RAGDocument {
  id: string;
  collection_id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: RAGDocumentType;
  mime_type?: string;
  chunk_count: number;
  vector_count: number;
  status: RAGDocumentStatus;
  error_message?: string;
  uploaded_by: string;
  uploaded_at: string;
  processed_at?: string;
  file_size_mb: number;
}

export interface RAGSearchDocument {
  document_id: string;
  filename: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface RAGSearchStep {
  step_name: string;
  description: string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  execution_time: number;
  status: string;
}

export interface RAGSearchResult {
  query: string;
  response: string;
  retrieved_documents: RAGSearchDocument[];
  search_steps: RAGSearchStep[];
  total_execution_time: number;
  relevance_score?: number;
  confidence_score?: number;
  metadata: Record<string, any>;
}

export interface RAGSearchResponse {
  search_id: string;
  result: RAGSearchResult;
  created_at: string;
}

export interface RAGSearchHistory {
  id: string;
  collection_id: string;
  query: string;
  response: string;
  execution_time?: number;
  retrieved_documents_count?: number;
  reranked_documents_count?: number;
  relevance_score?: number;
  confidence_score?: number;
  user_id: string;
  user_rating?: number;
  user_feedback?: string;
  created_at: string;
}

export interface RAGCollectionStats {
  total_collections: number;
  active_collections: number;
  total_documents: number;
  total_vectors: number;
  average_documents_per_collection: number;
  total_file_size_mb: number;
}

export interface RAGWorkspaceStats {
  workspace_id: string;
  collection_stats: RAGCollectionStats;
  recent_searches: number;
  popular_queries: string[];
}

// ============ Request/Response Types ============

export interface CreateCollectionRequest {
  name: string;
  description?: string;
}

export interface UpdateCollectionRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface SearchRequest {
  query: string;
  include_metadata?: boolean;
}

export interface UserFeedbackRequest {
  rating?: number;
  feedback?: string;
}

export interface CollectionListResponse {
  collections: RAGCollection[];
  total: number;
}

export interface DocumentListResponse {
  documents: RAGDocument[];
  total: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  status: RAGDocumentStatus;
  message: string;
}

export interface SearchHistoryListResponse {
  history: RAGSearchHistory[];
  total: number;
}

// ============ RAG Service Class ============

class RAGService {
  private baseUrl = '/api/rag';

  // ============ Collection APIs ============

  /**
   * 워크스페이스의 RAG 컬렉션 목록 조회
   */
  async getCollections(
    workspaceId: string,
    params?: {
      page?: number;
      limit?: number;
      search?: string;
      status?: RAGCollectionStatus;
    }
  ): Promise<CollectionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);

    const response = await apiClient.get(
      `${this.baseUrl}/workspaces/${workspaceId}/collections?${searchParams}`
    );
    return response.data;
  }

  /**
   * 새 RAG 컬렉션 생성
   */
  async createCollection(
    workspaceId: string,
    data: CreateCollectionRequest
  ): Promise<RAGCollection> {
    const response = await apiClient.post(
      `${this.baseUrl}/workspaces/${workspaceId}/collections`,
      data
    );
    return response.data;
  }

  /**
   * RAG 컬렉션 상세 조회
   */
  async getCollection(collectionId: string): Promise<RAGCollection> {
    const response = await apiClient.get(`${this.baseUrl}/collections/${collectionId}`);
    return response.data;
  }

  /**
   * RAG 컬렉션 수정
   */
  async updateCollection(
    collectionId: string,
    data: UpdateCollectionRequest
  ): Promise<RAGCollection> {
    const response = await apiClient.put(`${this.baseUrl}/collections/${collectionId}`, data);
    return response.data;
  }

  /**
   * RAG 컬렉션 삭제
   */
  async deleteCollection(collectionId: string): Promise<{ message: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/collections/${collectionId}`);
    return response.data;
  }

  // ============ Document APIs ============

  /**
   * 컬렉션의 문서 목록 조회
   */
  async getDocuments(
    collectionId: string,
    params?: {
      page?: number;
      limit?: number;
      status?: RAGDocumentStatus;
    }
  ): Promise<DocumentListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.status) searchParams.append('status', params.status);

    const response = await apiClient.get(
      `${this.baseUrl}/collections/${collectionId}/documents?${searchParams}`
    );
    return response.data;
  }

  /**
   * 문서 업로드
   */
  async uploadDocument(
    collectionId: string,
    file: File
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(
      `${this.baseUrl}/collections/${collectionId}/documents/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  /**
   * 문서 삭제
   */
  async deleteDocument(
    collectionId: string,
    documentId: string
  ): Promise<{ message: string }> {
    const response = await apiClient.delete(
      `${this.baseUrl}/collections/${collectionId}/documents/${documentId}`
    );
    return response.data;
  }

  // ============ Search APIs ============

  /**
   * RAG 검색 실행
   */
  async search(
    collectionId: string,
    searchRequest: SearchRequest
  ): Promise<RAGSearchResponse> {
    const response = await apiClient.post(
      `${this.baseUrl}/collections/${collectionId}/search`,
      searchRequest,
      {
        timeout: 120000, // 2분으로 증가 (기본 30초에서 변경)
      }
    );
    return response.data;
  }

  /**
   * 검색 기록 조회
   */
  async getSearchHistory(
    collectionId: string,
    params?: {
      page?: number;
      limit?: number;
      user_filter?: boolean;
    }
  ): Promise<SearchHistoryListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.user_filter) searchParams.append('user_filter', params.user_filter.toString());

    const response = await apiClient.get(
      `${this.baseUrl}/collections/${collectionId}/search/history?${searchParams}`
    );
    return response.data;
  }

  // ============ Statistics APIs ============

  /**
   * 워크스페이스 RAG 통계 조회
   */
  async getWorkspaceStats(workspaceId: string): Promise<RAGWorkspaceStats> {
    const response = await apiClient.get(`${this.baseUrl}/workspaces/${workspaceId}/stats`);
    return response.data;
  }

  /**
   * 컬렉션 통계 조회
   */
  async getCollectionStats(collectionId: string): Promise<RAGCollectionStats> {
    const response = await apiClient.get(`${this.baseUrl}/collections/${collectionId}/stats`);
    return response.data;
  }

  // ============ Feedback APIs ============

  /**
   * 검색 결과에 대한 사용자 피드백 제출
   */
  async submitFeedback(
    searchHistoryId: string,
    feedback: UserFeedbackRequest
  ): Promise<{ message: string }> {
    const response = await apiClient.post(
      `${this.baseUrl}/search/${searchHistoryId}/feedback`,
      feedback
    );
    return response.data;
  }
}

// Export singleton instance
export const ragService = new RAGService();
export default ragService;