"""
Output Node Worker
"""

from typing import Dict, Any
from .base_worker import BaseWorker, ExecutionContext


class OutputWorker(BaseWorker):
    """Worker for output nodes"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Output nodes collect and format final results
        """
        self.logger.info("Executing output node", node_id=context.node_id)
        
        # Validate required input
        self.validate_inputs(inputs, ['input'])
        
        # Get the input data
        output_data = inputs.get('input')
        
        # Apply any formatting from config
        if config.get('format'):
            format_type = config['format']
            if format_type == 'json' and isinstance(output_data, dict):
                # Already in JSON format
                pass
            elif format_type == 'string':
                output_data = str(output_data)
            elif format_type == 'number' and isinstance(output_data, str):
                try:
                    output_data = float(output_data)
                except ValueError:
                    self.logger.warning("Failed to convert to number", value=output_data)
        
        self.logger.info(
            "Output node result",
            node_id=context.node_id,
            output_type=type(output_data).__name__
        )
        
        # Output nodes return their data as 'result'
        return self.format_output(result=output_data)