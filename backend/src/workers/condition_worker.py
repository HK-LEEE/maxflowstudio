"""
Condition Node Worker - Enhanced with regex and JSON path support
"""

import re
import json
from typing import Dict, Any, Union
from .base_worker import BaseWorker, ExecutionContext

try:
    from jsonpath_ng import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False


class ConditionWorker(BaseWorker):
    """Worker for condition nodes"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Evaluate condition and route to true/false outputs with enhanced features
        """
        self.logger.info("Executing condition node", node_id=context.node_id)
        
        # Validate required inputs
        self.validate_inputs(inputs, ['input'])
        
        input_value = inputs.get('input')
        condition_type = config.get('condition_type', 'equals')
        condition_value = config.get('condition_value')
        custom_expression = config.get('custom_expression')
        
        # Advanced configuration
        case_sensitive = config.get('case_sensitive', True)
        regex_flags = config.get('regex_flags', 0)
        jsonpath_query = config.get('jsonpath_query', '')
        
        try:
            # Evaluate condition based on type
            result = await self._evaluate_condition(
                input_value=input_value,
                condition_type=condition_type,
                condition_value=condition_value,
                custom_expression=custom_expression,
                case_sensitive=case_sensitive,
                regex_flags=regex_flags,
                jsonpath_query=jsonpath_query,
                context=context
            )
            
            self.logger.info(
                "Condition evaluated",
                node_id=context.node_id,
                condition_type=condition_type,
                result=result
            )
            
            # Return data on appropriate output handle
            if result:
                return self.format_output(true=input_value, false=None, result=True)
            else:
                return self.format_output(true=None, false=input_value, result=False)
                
        except Exception as e:
            self.logger.error(
                "Condition evaluation failed",
                node_id=context.node_id,
                error=str(e)
            )
            raise ValueError(f"Condition evaluation failed: {e}")
    
    async def _evaluate_condition(
        self,
        input_value: Any,
        condition_type: str,
        condition_value: Any,
        custom_expression: str,
        case_sensitive: bool,
        regex_flags: int,
        jsonpath_query: str,
        context: ExecutionContext
    ) -> bool:
        """Evaluate the condition based on type"""
        
        if condition_type == 'equals':
            return self._equals_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'not_equals':
            return not self._equals_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'contains':
            return self._contains_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'not_contains':
            return not self._contains_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'starts_with':
            return self._starts_with_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'ends_with':
            return self._ends_with_condition(input_value, condition_value, case_sensitive)
            
        elif condition_type == 'regex_match':
            return self._regex_match_condition(input_value, condition_value, regex_flags)
            
        elif condition_type == 'regex_search':
            return self._regex_search_condition(input_value, condition_value, regex_flags)
            
        elif condition_type == 'greater_than':
            return self._numeric_condition(input_value, condition_value, '>')
            
        elif condition_type == 'less_than':
            return self._numeric_condition(input_value, condition_value, '<')
            
        elif condition_type == 'greater_equal':
            return self._numeric_condition(input_value, condition_value, '>=')
            
        elif condition_type == 'less_equal':
            return self._numeric_condition(input_value, condition_value, '<=')
            
        elif condition_type == 'between':
            return self._between_condition(input_value, condition_value)
            
        elif condition_type == 'is_empty':
            return self._is_empty_condition(input_value)
            
        elif condition_type == 'is_not_empty':
            return not self._is_empty_condition(input_value)
            
        elif condition_type == 'is_null':
            return input_value is None
            
        elif condition_type == 'is_not_null':
            return input_value is not None
            
        elif condition_type == 'json_path':
            return self._jsonpath_condition(input_value, jsonpath_query, condition_value, case_sensitive)
            
        elif condition_type == 'array_contains':
            return self._array_contains_condition(input_value, condition_value)
            
        elif condition_type == 'array_length':
            return self._array_length_condition(input_value, condition_value)
            
        elif condition_type == 'custom' and custom_expression:
            return self._custom_expression_condition(input_value, custom_expression)
            
        else:
            raise ValueError(f"Unknown condition type: {condition_type}")
    
    def _equals_condition(self, input_value: Any, condition_value: Any, case_sensitive: bool) -> bool:
        """Check equality with optional case sensitivity"""
        if not case_sensitive and isinstance(input_value, str) and isinstance(condition_value, str):
            return input_value.lower() == condition_value.lower()
        return input_value == condition_value
    
    def _contains_condition(self, input_value: Any, condition_value: Any, case_sensitive: bool) -> bool:
        """Check if input contains the condition value"""
        input_str = str(input_value)
        condition_str = str(condition_value)
        
        if not case_sensitive:
            input_str = input_str.lower()
            condition_str = condition_str.lower()
            
        return condition_str in input_str
    
    def _starts_with_condition(self, input_value: Any, condition_value: Any, case_sensitive: bool) -> bool:
        """Check if input starts with condition value"""
        input_str = str(input_value)
        condition_str = str(condition_value)
        
        if not case_sensitive:
            input_str = input_str.lower()
            condition_str = condition_str.lower()
            
        return input_str.startswith(condition_str)
    
    def _ends_with_condition(self, input_value: Any, condition_value: Any, case_sensitive: bool) -> bool:
        """Check if input ends with condition value"""
        input_str = str(input_value)
        condition_str = str(condition_value)
        
        if not case_sensitive:
            input_str = input_str.lower()
            condition_str = condition_str.lower()
            
        return input_str.endswith(condition_str)
    
    def _regex_match_condition(self, input_value: Any, pattern: str, flags: int) -> bool:
        """Check if input matches regex pattern (full match)"""
        input_str = str(input_value)
        try:
            return bool(re.match(pattern, input_str, flags))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def _regex_search_condition(self, input_value: Any, pattern: str, flags: int) -> bool:
        """Check if input contains regex pattern (search)"""
        input_str = str(input_value)
        try:
            return bool(re.search(pattern, input_str, flags))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def _numeric_condition(self, input_value: Any, condition_value: Any, operator: str) -> bool:
        """Compare numeric values"""
        try:
            input_num = float(input_value)
            condition_num = float(condition_value)
            
            if operator == '>':
                return input_num > condition_num
            elif operator == '<':
                return input_num < condition_num
            elif operator == '>=':
                return input_num >= condition_num
            elif operator == '<=':
                return input_num <= condition_num
            else:
                raise ValueError(f"Unknown numeric operator: {operator}")
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric comparison: {e}")
    
    def _between_condition(self, input_value: Any, condition_value: Any) -> bool:
        """Check if value is between two numbers"""
        try:
            input_num = float(input_value)
            
            if isinstance(condition_value, (list, tuple)) and len(condition_value) == 2:
                min_val, max_val = float(condition_value[0]), float(condition_value[1])
                return min_val <= input_num <= max_val
            else:
                raise ValueError("Between condition requires array of two numbers [min, max]")
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid between comparison: {e}")
    
    def _is_empty_condition(self, input_value: Any) -> bool:
        """Check if value is empty"""
        if input_value is None:
            return True
        if isinstance(input_value, str):
            return len(input_value.strip()) == 0
        if isinstance(input_value, (list, dict, tuple)):
            return len(input_value) == 0
        return False
    
    def _jsonpath_condition(self, input_value: Any, jsonpath_query: str, condition_value: Any, case_sensitive: bool) -> bool:
        """Evaluate JSONPath query and compare result"""
        if not JSONPATH_AVAILABLE:
            raise ValueError("JSONPath functionality requires 'jsonpath-ng' package")
        
        try:
            # If input is string, try to parse as JSON
            if isinstance(input_value, str):
                try:
                    input_data = json.loads(input_value)
                except json.JSONDecodeError:
                    raise ValueError("Input value is not valid JSON for JSONPath query")
            else:
                input_data = input_value
            
            # Parse and execute JSONPath query
            jsonpath_expr = jsonpath_parse(jsonpath_query)
            matches = jsonpath_expr.find(input_data)
            
            if not matches:
                return False
            
            # Compare first match with condition value
            match_value = matches[0].value
            return self._equals_condition(match_value, condition_value, case_sensitive)
            
        except Exception as e:
            raise ValueError(f"JSONPath evaluation failed: {e}")
    
    def _array_contains_condition(self, input_value: Any, condition_value: Any) -> bool:
        """Check if array contains specific value"""
        if not isinstance(input_value, (list, tuple)):
            try:
                # Try to parse as JSON array
                if isinstance(input_value, str):
                    input_value = json.loads(input_value)
                    if not isinstance(input_value, list):
                        return False
                else:
                    return False
            except json.JSONDecodeError:
                return False
        
        return condition_value in input_value
    
    def _array_length_condition(self, input_value: Any, condition_value: Any) -> bool:
        """Check array length"""
        if not isinstance(input_value, (list, tuple)):
            try:
                # Try to parse as JSON array
                if isinstance(input_value, str):
                    input_value = json.loads(input_value)
                    if not isinstance(input_value, list):
                        return False
                else:
                    return False
            except json.JSONDecodeError:
                return False
        
        try:
            expected_length = int(condition_value)
            return len(input_value) == expected_length
        except (ValueError, TypeError):
            raise ValueError("Array length condition requires integer value")
    
    def _custom_expression_condition(self, input_value: Any, custom_expression: str) -> bool:
        """Evaluate custom Python expression"""
        safe_globals = {
            '__builtins__': {},
            'input': input_value,
            'value': input_value,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            're': re,
            'json': json,
            'any': any,
            'all': all,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
        }
        
        try:
            result = eval(custom_expression, safe_globals)
            return bool(result)
        except Exception as e:
            raise ValueError(f"Custom expression evaluation failed: {e}")