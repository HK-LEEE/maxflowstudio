"""
Template Worker - 템플릿 포맷팅 워커
"""

from typing import Dict, Any
import re
from .base_worker import BaseWorker, ExecutionContext


class TemplateWorker(BaseWorker):
    """템플릿 포맷팅을 처리하는 워커"""
    
    def __init__(self):
        super().__init__()
        
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        템플릿 포맷팅 실행
        
        입력:
        - template: 템플릿 문자열
        - 다양한 입력 변수들
        
        출력:
        - formatted_text: 포맷팅된 결과
        """
        self.logger.info("Executing template worker", node_id=context.node_id)
        
        # 템플릿 가져오기
        template = inputs.get("template", "")
        if not template:
            # config에서 템플릿 가져오기 시도
            template = config.get("template", "")
            
        if not template:
            raise ValueError("템플릿이 제공되지 않았습니다")
            
        # 템플릿에서 변수 추출
        import re
        template_vars = re.findall(r'\{([^}|]+)(?:\|[^}]+)?\}', template)
        template_vars = [var.strip() for var in template_vars]
        
        # 변수 수집 - 직접 매핑 방식
        variables = {}
        
        # inputs에서 모든 변수 수집 (template 제외)
        for key, value in inputs.items():
            if key != "template" and value is not None:
                # Extract actual value if it's wrapped in a dict with 'output' key
                if isinstance(value, dict) and 'output' in value:
                    actual_value = value['output']
                else:
                    actual_value = value
                
                # 직접 매핑: Variable1 → {Variable1}, Variable2 → {Variable2} 등
                variables[key] = actual_value
        
        # config에서 추가 변수 수집
        if "variables" in config:
            variables.update(config["variables"])
            
        # 템플릿 모드 확인
        template_mode = config.get("template_mode", "simple")
        
        self.logger.info(
            "Template processing details",
            node_id=context.node_id,
            template=template,
            variables=variables,
            template_mode=template_mode
        )
        
        # 템플릿 처리
        if template_mode == "simple":
            formatted_text = self._simple_format(template, variables)
        else:
            # 고급 모드 (기본값 지원)
            formatted_text = self._advanced_format(template, variables)
            
        self.logger.info(
            "Template formatting completed",
            node_id=context.node_id,
            template_length=len(template),
            result_length=len(formatted_text),
            variables_count=len(variables)
        )
        
        return {
            "output": formatted_text,
            "used_variables": list(variables.keys())
        }
        
    def _simple_format(self, template: str, variables: Dict[str, Any]) -> str:
        """단순 변수 치환"""
        result = template
        
        # {var_name} 형식 치환
        for var_name, value in variables.items():
            result = result.replace(f"{{{var_name}}}", str(value))
            # ${var_name} 형식도 지원
            result = result.replace(f"${{{var_name}}}", str(value))
            
        return result
        
    def _advanced_format(self, template: str, variables: Dict[str, Any]) -> str:
        """고급 변수 치환 (기본값 지원)"""
        
        def replace_var(match):
            var_expr = match.group(1)
            
            # 기본값 처리 (var_name|default:value)
            if '|default:' in var_expr:
                var_name, default_value = var_expr.split('|default:', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = var_expr.strip()
                default_value = ""
                
            # 변수 값 가져오기
            if var_name in variables:
                return str(variables[var_name])
            else:
                return default_value
                
        # {var_name} 및 {var_name|default:value} 패턴 치환
        result = re.sub(r'\{([^}]+)\}', replace_var, template)
        
        return result