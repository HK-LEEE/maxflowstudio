"""
Type conversion utilities for data flow between nodes
"""

import json
from typing import Any, Optional, Union


class TypeConverter:
    """Convert data between different types based on handle type definitions"""
    
    @staticmethod
    def convert(value: Any, target_type: str) -> Any:
        """
        Convert value to target type
        
        Args:
            value: Value to convert
            target_type: Target type (string, number, boolean, object, array, any)
            
        Returns:
            Converted value
        """
        if target_type == 'any' or value is None:
            return value
            
        try:
            if target_type == 'string':
                return TypeConverter._to_string(value)
            elif target_type == 'number':
                return TypeConverter._to_number(value)
            elif target_type == 'boolean':
                return TypeConverter._to_boolean(value)
            elif target_type == 'object':
                return TypeConverter._to_object(value)
            elif target_type == 'array':
                return TypeConverter._to_array(value)
            else:
                return value
        except Exception:
            # If conversion fails, return original value
            return value
    
    @staticmethod
    def _to_string(value: Any) -> str:
        """Convert to string"""
        if isinstance(value, str):
            return value
        elif isinstance(value, (dict, list)):
            return json.dumps(value)
        else:
            return str(value)
    
    @staticmethod
    def _to_number(value: Any) -> Union[int, float]:
        """Convert to number"""
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, str):
            # Try int first, then float
            if '.' in value:
                return float(value)
            else:
                return int(value)
        elif isinstance(value, bool):
            return 1 if value else 0
        else:
            raise ValueError(f"Cannot convert {type(value)} to number")
    
    @staticmethod
    def _to_boolean(value: Any) -> bool:
        """Convert to boolean"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        elif isinstance(value, (int, float)):
            return value != 0
        elif isinstance(value, (list, dict)):
            return len(value) > 0
        else:
            return bool(value)
    
    @staticmethod
    def _to_object(value: Any) -> dict:
        """Convert to object/dict"""
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return {"value": parsed}
            except:
                return {"value": value}
        elif isinstance(value, list):
            return {str(i): v for i, v in enumerate(value)}
        else:
            return {"value": value}
    
    @staticmethod
    def _to_array(value: Any) -> list:
        """Convert to array/list"""
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [parsed]
            except:
                # Try comma-separated values
                if ',' in value:
                    return [v.strip() for v in value.split(',')]
                else:
                    return [value]
        elif isinstance(value, dict):
            return list(value.values())
        else:
            return [value]
    
    @staticmethod
    def validate_type(value: Any, expected_type: str) -> bool:
        """
        Validate if value matches expected type
        
        Args:
            value: Value to validate
            expected_type: Expected type
            
        Returns:
            True if value matches expected type
        """
        if expected_type == 'any':
            return True
            
        type_map = {
            'string': str,
            'number': (int, float),
            'boolean': bool,
            'object': dict,
            'array': list
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True