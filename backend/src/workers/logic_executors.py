"""
Logic Node Executors
Flow: Logic Config -> Evaluation -> Result
"""

import asyncio
import json
import re
from typing import Dict, Any, Union

import structlog

from .base_worker import BaseNodeExecutor

logger = structlog.get_logger(__name__)


class ConditionExecutor(BaseNodeExecutor):
    """Executor for conditional logic nodes."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate condition configuration."""
        condition_type = config.get('condition_type')
        return condition_type in ['equals', 'contains', 'greater_than', 'less_than', 'custom']
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conditional logic."""
        condition_type = config.get('condition_type', 'equals')
        condition_value = config.get('condition_value', '')
        custom_expression = config.get('custom_expression', '')
        
        # Get the first input value as the main input
        main_input = None
        if inputs:
            main_input = list(inputs.values())[0]
        
        try:
            if condition_type == 'equals':
                result = str(main_input) == str(condition_value)
            elif condition_type == 'contains':
                result = str(condition_value) in str(main_input)
            elif condition_type == 'greater_than':
                result = float(main_input) > float(condition_value)
            elif condition_type == 'less_than':
                result = float(main_input) < float(condition_value)
            elif condition_type == 'custom':
                # Safe evaluation of custom expressions
                result = self._evaluate_custom_expression(custom_expression, inputs)
            else:
                raise ValueError(f"Unsupported condition type: {condition_type}")
            
            return {
                'condition_result': result,
                'condition_type': condition_type,
                'evaluated_value': main_input,
                'condition_value': condition_value,
                'inputs': inputs
            }
            
        except Exception as e:
            self.logger.error("Condition evaluation failed", error=str(e))
            return {
                'condition_result': False,
                'error': str(e),
                'inputs': inputs
            }
    
    def _evaluate_custom_expression(self, expression: str, inputs: Dict[str, Any]) -> bool:
        """Safely evaluate custom expressions."""
        # For security, only allow simple expressions
        # In production, use a proper expression parser
        
        # Replace input references
        safe_expression = expression
        for key, value in inputs.items():
            safe_expression = safe_expression.replace(f"input.{key}", str(value))
        
        # Simple regex-based evaluation for demo
        # This is NOT secure for production use
        if ">" in safe_expression:
            parts = safe_expression.split(">")
            if len(parts) == 2:
                try:
                    left = float(parts[0].strip())
                    right = float(parts[1].strip())
                    return left > right
                except ValueError:
                    return False
        
        # Default to false for safety
        return False


class FunctionExecutor(BaseNodeExecutor):
    """Executor for custom function nodes."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate function configuration."""
        return 'function_code' in config
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom function code."""
        function_code = config.get('function_code', '')
        timeout = int(config.get('timeout', 30))
        
        # For security reasons, we'll simulate function execution
        # In production, this would need proper sandboxing
        return await self._simulate_function_execution(function_code, inputs, timeout)
    
    async def _simulate_function_execution(self, code: str, inputs: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Simulate function execution for security."""
        # Simulate processing time
        await asyncio.sleep(min(1.0, timeout / 30))
        
        # Basic code analysis for demo
        lines = code.split('\n')
        has_return = any('return' in line for line in lines)
        
        result = {
            'executed': True,
            'code_lines': len(lines),
            'has_return_statement': has_return,
            'inputs_received': list(inputs.keys()),
            'simulated_result': f"Function processed {len(inputs)} inputs",
            'note': 'This is a simulated execution for security reasons'
        }
        
        # If there are numeric inputs, simulate some processing
        numeric_inputs = {k: v for k, v in inputs.items() if isinstance(v, (int, float))}
        if numeric_inputs:
            result['numeric_sum'] = sum(numeric_inputs.values())
            result['numeric_average'] = sum(numeric_inputs.values()) / len(numeric_inputs)
        
        return result


class TransformExecutor(BaseNodeExecutor):
    """Executor for data transformation nodes."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate transform configuration."""
        transform_type = config.get('transform_type')
        return transform_type in ['json_path', 'regex', 'template', 'custom']
    
    async def execute(self, config: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation."""
        transform_type = config.get('transform_type', 'json_path')
        expression = config.get('transform_expression', '')
        
        try:
            if transform_type == 'json_path':
                result = self._apply_json_path(expression, inputs)
            elif transform_type == 'regex':
                result = self._apply_regex(expression, inputs)
            elif transform_type == 'template':
                result = self._apply_template(expression, inputs)
            elif transform_type == 'custom':
                result = self._apply_custom_transform(expression, inputs)
            else:
                raise ValueError(f"Unsupported transform type: {transform_type}")
            
            return {
                'transformed_data': result,
                'transform_type': transform_type,
                'expression': expression,
                'original_inputs': inputs
            }
            
        except Exception as e:
            self.logger.error("Transform execution failed", error=str(e))
            return {
                'error': str(e),
                'transform_type': transform_type,
                'original_inputs': inputs
            }
    
    def _apply_json_path(self, path: str, inputs: Dict[str, Any]) -> Any:
        """Apply JSON path transformation."""
        # Simple JSON path implementation for demo
        if path.startswith('$.'):
            path = path[2:]  # Remove $.
        
        # Navigate through the inputs
        current = inputs
        for part in path.split('.'):
            if part == '*':
                # Return all values if wildcard
                if isinstance(current, dict):
                    return list(current.values())
                elif isinstance(current, list):
                    return current
            elif isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        
        return current
    
    def _apply_regex(self, pattern: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply regex transformation."""
        results = {}
        
        for key, value in inputs.items():
            if isinstance(value, str):
                matches = re.findall(pattern, value)
                results[key] = matches
            else:
                results[key] = None
        
        return results
    
    def _apply_template(self, template: str, inputs: Dict[str, Any]) -> str:
        """Apply template transformation."""
        result = template
        
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        
        return result
    
    def _apply_custom_transform(self, expression: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom transformation."""
        # For demo purposes, just return a processed version
        return {
            'expression_applied': expression,
            'input_count': len(inputs),
            'processed_keys': list(inputs.keys()),
            'note': 'Custom transformation simulated'
        }