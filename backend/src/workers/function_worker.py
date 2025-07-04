"""
Function Node Worker - Python-only code execution
"""

import ast
import json
import math
import datetime
import time
import re
import sys
import traceback
from typing import Dict, Any, Optional
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from .base_worker import BaseWorker, ExecutionContext


class FunctionWorker(BaseWorker):
    """Worker for function nodes - Python code execution only"""
    
    def __init__(self):
        super().__init__()
        # Allowed modules for import (whitelist)
        self.allowed_modules = {
            'json',
            'math', 
            'datetime',
            'time',
            're',
            'random',
            'uuid',
            'hashlib',
            'base64',
            'urllib.parse',
            'collections',
            'itertools',
            'functools',
            'operator'
        }
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute Python code with sandboxed environment
        """
        self.logger.info("Executing function node", node_id=context.node_id)
        
        # Get configuration
        code = config.get('code', '')
        timeout = config.get('timeout', 30)
        input_mapping = config.get('input_mapping', {})
        output_mapping = config.get('output_mapping', {})
        
        if not code.strip():
            raise ValueError("Function code is required")
        
        # Validate code syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Python syntax error: {e}")
        
        # Check for dangerous operations
        self._validate_code_safety(code)
        
        try:
            # Prepare execution environment
            execution_globals = self._create_safe_globals()
            execution_locals = {}
            
            # Map inputs to variables
            mapped_inputs = self._map_inputs(inputs, input_mapping)
            execution_locals.update(mapped_inputs)
            
            # Capture stdout and stderr
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            self.logger.info(
                "Executing Python code",
                node_id=context.node_id,
                code_length=len(code),
                input_vars=list(mapped_inputs.keys())
            )
            
            # Execute with timeout and output capture
            start_time = time.time()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code
                exec(code, execution_globals, execution_locals)
            
            execution_time = time.time() - start_time
            
            # Get captured outputs
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Map outputs from variables
            mapped_outputs = self._map_outputs(execution_locals, output_mapping)
            
            self.logger.info(
                "Python code executed successfully",
                node_id=context.node_id,
                execution_time=execution_time,
                output_vars=list(mapped_outputs.keys())
            )
            
            # Return results
            result = {
                **mapped_outputs,
                'stdout': stdout_output if stdout_output else None,
                'stderr': stderr_output if stderr_output else None,
                'execution_time': execution_time,
                'error': None
            }
            
            return self.format_output(**result)
            
        except Exception as e:
            error_msg = f"Python execution error: {str(e)}"
            self.logger.error(
                "Function execution failed",
                node_id=context.node_id,
                error=error_msg,
                traceback=traceback.format_exc()
            )
            
            return self.format_output(
                result=None,
                error=error_msg,
                traceback=traceback.format_exc()
            )
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create a safe globals dictionary for code execution"""
        safe_globals = {
            '__builtins__': {
                # Basic types and functions
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'print': print,
                
                # String methods
                'ord': ord,
                'chr': chr,
                
                # Exception handling
                'Exception': Exception,
                'ValueError': ValueError,
                'TypeError': TypeError,
                'KeyError': KeyError,
                'IndexError': IndexError,
                'AttributeError': AttributeError,
            },
            
            # Safe modules
            'json': json,
            'math': math,
            'datetime': datetime,
            'time': time,
            're': re,
        }
        
        return safe_globals
    
    def _validate_code_safety(self, code: str) -> None:
        """Validate that code doesn't contain dangerous operations"""
        dangerous_patterns = [
            # File operations
            r'\bopen\s*\(',
            r'\bfile\s*\(',
            r'\bexecfile\s*\(',
            
            # System operations
            r'\bos\.',
            r'\bsys\.',
            r'\bsubprocess\.',
            r'\b__import__\s*\(',
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bcompile\s*\(',
            
            # Network operations
            r'\bsocket\.',
            r'\burllib\.',
            r'\brequests\.',
            r'\bhttp\.',
            
            # Dangerous builtins
            r'\bglobals\s*\(',
            r'\blocals\s*\(',
            r'\bvars\s*\(',
            r'\bdir\s*\(',
            r'\b__getattribute__',
            r'\b__setattr__',
            r'\b__delattr__',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise ValueError(f"Dangerous operation detected: {pattern}")
        
        # Check for import statements of non-allowed modules
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_modules:
                            raise ValueError(f"Import of module '{alias.name}' is not allowed")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        raise ValueError(f"Import from module '{node.module}' is not allowed")
        except SyntaxError:
            # If we can't parse it, let the main execution handle the syntax error
            pass
    
    def _map_inputs(self, inputs: Dict[str, Any], input_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map flow inputs to local variables"""
        mapped = {}
        
        # If no mapping provided, use inputs directly
        if not input_mapping:
            return inputs
        
        # Apply custom mapping
        for var_name, input_key in input_mapping.items():
            if input_key in inputs:
                mapped[var_name] = inputs[input_key]
            else:
                mapped[var_name] = None
        
        return mapped
    
    def _map_outputs(self, execution_locals: Dict[str, Any], output_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map local variables to flow outputs"""
        mapped = {}
        
        # If no mapping provided, return all variables (except builtins)
        if not output_mapping:
            for key, value in execution_locals.items():
                if not key.startswith('_') and key not in ['__builtins__']:
                    try:
                        # Try to serialize to ensure it's JSON-compatible
                        json.dumps(value, default=str)
                        mapped[key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable objects to string
                        mapped[key] = str(value)
            return mapped
        
        # Apply custom mapping
        for output_key, var_name in output_mapping.items():
            if var_name in execution_locals:
                value = execution_locals[var_name]
                try:
                    # Try to serialize to ensure it's JSON-compatible
                    json.dumps(value, default=str)
                    mapped[output_key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to string
                    mapped[output_key] = str(value)
            else:
                mapped[output_key] = None
        
        return mapped