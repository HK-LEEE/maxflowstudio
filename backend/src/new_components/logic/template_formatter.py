"""
Template Formatter Component - 템플릿 기반 텍스트 포맷팅
"""

import re
from typing import Dict, Any, List, Optional, Union
from jinja2 import Template, TemplateSyntaxError, UndefinedError

from src.core.component_base import BaseComponent, ComponentInput, ComponentOutput, ComponentConfig


class TemplateFormatterComponent(BaseComponent):
    """
    템플릿 문자열과 변수를 결합하여 포맷팅된 텍스트를 생성하는 컴포넌트
    
    주요 기능:
    - 다양한 템플릿 문법 지원 ({var}, ${var}, {{var}})
    - 다중 입력 변수 지원
    - 조건부 렌더링 및 반복문 지원 (Jinja2 모드)
    - 기본값 처리 및 에러 처리 옵션
    """
    
    def __init__(self):
        super().__init__(
            name="Template Formatter",
            description="템플릿과 변수를 결합하여 동적 텍스트 생성",
            category="logic"
        )
        
    def get_inputs(self) -> List[ComponentInput]:
        return [
            ComponentInput(
                name="template",
                data_type="string",
                description="템플릿 문자열 (예: 안녕하세요 {name}님, 오늘은 {day}입니다)",
                required=True
            ),
            ComponentInput(
                name="var_1",
                data_type="any",
                description="첫 번째 변수",
                required=False
            ),
            ComponentInput(
                name="var_2",
                data_type="any",
                description="두 번째 변수",
                required=False
            ),
            ComponentInput(
                name="var_3",
                data_type="any",
                description="세 번째 변수",
                required=False
            ),
            ComponentInput(
                name="var_4",
                data_type="any",
                description="네 번째 변수",
                required=False
            ),
            ComponentInput(
                name="var_5",
                data_type="any",
                description="다섯 번째 변수",
                required=False
            ),
            ComponentInput(
                name="variables",
                data_type="object",
                description="추가 변수 객체 (key-value 형태)",
                required=False
            ),
            ComponentInput(
                name="template_override",
                data_type="string",
                description="동적으로 템플릿을 변경할 때 사용",
                required=False
            )
        ]
        
    def get_outputs(self) -> List[ComponentOutput]:
        return [
            ComponentOutput(
                name="formatted_text",
                data_type="string",
                description="포맷팅된 결과 텍스트"
            ),
            ComponentOutput(
                name="used_variables",
                data_type="array",
                description="실제로 사용된 변수 목록"
            ),
            ComponentOutput(
                name="formatting_info",
                data_type="object",
                description="포맷팅 정보 (템플릿 타입, 변수 개수 등)"
            )
        ]
        
    def get_config(self) -> ComponentConfig:
        return ComponentConfig(
            parameters={
                "template_mode": {
                    "type": "select",
                    "label": "템플릿 모드",
                    "options": [
                        {"value": "simple", "label": "단순 치환 ({var})"},
                        {"value": "advanced", "label": "고급 치환 (기본값 지원)"},
                        {"value": "jinja2", "label": "Jinja2 (조건문/반복문 지원)"}
                    ],
                    "default": "simple"
                },
                "undefined_behavior": {
                    "type": "select",
                    "label": "정의되지 않은 변수 처리",
                    "options": [
                        {"value": "empty", "label": "빈 문자열로 치환"},
                        {"value": "keep", "label": "원본 유지"},
                        {"value": "error", "label": "에러 발생"}
                    ],
                    "default": "empty"
                },
                "strip_whitespace": {
                    "type": "boolean",
                    "label": "공백 문자 제거",
                    "default": False
                },
                "variable_mapping": {
                    "type": "object",
                    "label": "변수 이름 매핑",
                    "description": "입력 변수를 템플릿의 다른 이름으로 매핑 (예: {\"var_1\": \"name\"})",
                    "default": {}
                }
            }
        )
        
    async def process(self, inputs: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """템플릿 포맷팅 처리"""
        
        # 템플릿 가져오기
        template_str = inputs.get("template_override") or inputs.get("template", "")
        if not template_str:
            raise ValueError("템플릿이 제공되지 않았습니다")
            
        # 설정 가져오기
        template_mode = config.get("template_mode", "simple")
        undefined_behavior = config.get("undefined_behavior", "empty")
        strip_whitespace = config.get("strip_whitespace", False)
        variable_mapping = config.get("variable_mapping", {})
        
        # 변수 수집
        variables = self._collect_variables(inputs, variable_mapping)
        
        # 템플릿 처리
        if template_mode == "jinja2":
            formatted_text, used_vars = self._process_jinja2(
                template_str, variables, undefined_behavior
            )
        elif template_mode == "advanced":
            formatted_text, used_vars = self._process_advanced(
                template_str, variables, undefined_behavior
            )
        else:  # simple
            formatted_text, used_vars = self._process_simple(
                template_str, variables, undefined_behavior
            )
            
        # 공백 처리
        if strip_whitespace:
            formatted_text = formatted_text.strip()
            
        # 포맷팅 정보 생성
        formatting_info = {
            "template_mode": template_mode,
            "total_variables": len(variables),
            "used_variables_count": len(used_vars),
            "template_length": len(template_str),
            "result_length": len(formatted_text)
        }
        
        return {
            "formatted_text": formatted_text,
            "used_variables": list(used_vars),
            "formatting_info": formatting_info
        }
        
    def _collect_variables(self, inputs: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """입력에서 변수 수집 및 매핑"""
        variables = {}
        
        # 개별 변수 수집 (var_1 ~ var_5)
        for i in range(1, 6):
            var_key = f"var_{i}"
            if var_key in inputs and inputs[var_key] is not None:
                # 매핑이 있으면 적용
                mapped_name = mapping.get(var_key, var_key)
                variables[mapped_name] = inputs[var_key]
                
        # 변수 객체에서 추가 변수 수집
        if "variables" in inputs and isinstance(inputs["variables"], dict):
            variables.update(inputs["variables"])
            
        return variables
        
    def _process_simple(self, template: str, variables: Dict[str, Any], 
                       undefined_behavior: str) -> tuple[str, set]:
        """단순 치환 처리 ({var_name} 형식)"""
        used_vars = set()
        
        def replace_var(match):
            var_name = match.group(1)
            used_vars.add(var_name)
            
            if var_name in variables:
                return str(variables[var_name])
            elif undefined_behavior == "keep":
                return match.group(0)
            elif undefined_behavior == "error":
                raise ValueError(f"정의되지 않은 변수: {var_name}")
            else:  # empty
                return ""
                
        # {var_name} 패턴 치환
        result = re.sub(r'\{([^}]+)\}', replace_var, template)
        
        # ${var_name} 패턴도 지원
        result = re.sub(r'\$\{([^}]+)\}', replace_var, result)
        
        return result, used_vars
        
    def _process_advanced(self, template: str, variables: Dict[str, Any], 
                         undefined_behavior: str) -> tuple[str, set]:
        """고급 치환 처리 (기본값 지원)"""
        used_vars = set()
        
        def replace_var(match):
            var_expr = match.group(1)
            
            # 기본값 처리 (var_name|default:value)
            if '|default:' in var_expr:
                var_name, default_value = var_expr.split('|default:', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = var_expr.strip()
                default_value = None
                
            used_vars.add(var_name)
            
            if var_name in variables:
                return str(variables[var_name])
            elif default_value is not None:
                return default_value
            elif undefined_behavior == "keep":
                return match.group(0)
            elif undefined_behavior == "error":
                raise ValueError(f"정의되지 않은 변수: {var_name}")
            else:  # empty
                return ""
                
        # {var_name} 및 {var_name|default:value} 패턴 치환
        result = re.sub(r'\{([^}]+)\}', replace_var, template)
        
        return result, used_vars
        
    def _process_jinja2(self, template: str, variables: Dict[str, Any], 
                       undefined_behavior: str) -> tuple[str, set]:
        """Jinja2 템플릿 처리 (조건문, 반복문 지원)"""
        used_vars = set()
        
        try:
            # Jinja2 템플릿 생성
            jinja_template = Template(template)
            
            # undefined 처리 설정
            if undefined_behavior == "error":
                jinja_template.undefined = 'strict'
                
            # 사용된 변수 추적을 위한 커스텀 함수
            def track_var(var_name):
                used_vars.add(var_name)
                return variables.get(var_name, "" if undefined_behavior == "empty" else f"{{{var_name}}}")
                
            # 변수에 추적 함수 추가
            template_vars = variables.copy()
            template_vars['get_var'] = track_var
            
            # 템플릿 렌더링
            result = jinja_template.render(**template_vars)
            
            # 템플릿에서 직접 참조된 변수도 추적
            for var_name in variables:
                if f"{{{var_name}}}" in template or f"{{{{ {var_name}" in template:
                    used_vars.add(var_name)
                    
        except TemplateSyntaxError as e:
            raise ValueError(f"템플릿 문법 오류: {str(e)}")
        except UndefinedError as e:
            if undefined_behavior == "error":
                raise ValueError(f"정의되지 않은 변수: {str(e)}")
            else:
                result = template  # 원본 반환
                
        return result, used_vars