"""
Transform Node Worker
"""

import json
import re
from typing import Dict, Any
from jsonpath_ng import parse
from .base_worker import BaseWorker, ExecutionContext


class TransformWorker(BaseWorker):
    """Worker for transform nodes"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Transform input data based on configuration
        """
        self.logger.info("Executing transform node", node_id=context.node_id)
        
        # Validate required inputs
        self.validate_inputs(inputs, ['input'])
        
        input_data = inputs.get('input')
        transform_type = config.get('transform_type', 'json_path')
        expression = config.get('transform_expression', '')
        
        try:
            if transform_type == 'json_path':
                result = self._json_path_transform(input_data, expression)
            elif transform_type == 'regex':
                result = self._regex_transform(input_data, expression)
            elif transform_type == 'template':
                result = self._template_transform(input_data, expression)
            elif transform_type == 'custom':
                result = self._custom_transform(input_data, expression)
            else:
                result = input_data
                
            self.logger.info(
                "Transform completed",
                node_id=context.node_id,
                transform_type=transform_type
            )
            
            return self.format_output(output=result)
            
        except Exception as e:
            self.logger.error(
                "Transform failed",
                node_id=context.node_id,
                error=str(e)
            )
            raise
    
    def _json_path_transform(self, data: Any, expression: str) -> Any:
        """Apply JSONPath transformation"""
        if not expression:
            return data
            
        try:
            jsonpath_expr = parse(expression)
            matches = jsonpath_expr.find(data)
            
            if not matches:
                return None
            elif len(matches) == 1:
                return matches[0].value
            else:
                return [match.value for match in matches]
        except Exception as e:
            self.logger.error(f"JSONPath error: {e}")
            raise ValueError(f"Invalid JSONPath expression: {expression}")
    
    def _regex_transform(self, data: Any, pattern: str) -> Any:
        """Apply regex transformation"""
        if not pattern or not isinstance(data, str):
            return data
            
        try:
            matches = re.findall(pattern, data)
            if not matches:
                return None
            elif len(matches) == 1:
                return matches[0]
            else:
                return matches
        except Exception as e:
            self.logger.error(f"Regex error: {e}")
            raise ValueError(f"Invalid regex pattern: {pattern}")
    
    def _template_transform(self, data: Any, template: str) -> str:
        """Apply template transformation"""
        if not template:
            return str(data)
            
        try:
            # Simple template replacement
            result = template
            if isinstance(data, dict):
                for key, value in data.items():
                    result = result.replace(f"{{{key}}}", str(value))
                    result = result.replace(f"${{{key}}}", str(value))
            else:
                result = result.replace("{value}", str(data))
                result = result.replace("${value}", str(data))
            
            return result
        except Exception as e:
            self.logger.error(f"Template error: {e}")
            raise ValueError(f"Template transformation failed: {e}")
    
    def _custom_transform(self, data: Any, code: str) -> Any:
        """Apply custom Python transformation"""
        if not code:
            return data
            
        try:
            # Create a safe execution environment
            safe_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'reversed': reversed,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                }
            }
            
            # Execute the transformation
            exec(f"result = {code}", safe_globals, {'data': data})
            return safe_globals.get('result', data)
            
        except Exception as e:
            self.logger.error(f"Custom transform error: {e}")
            raise ValueError(f"Custom transformation failed: {e}")