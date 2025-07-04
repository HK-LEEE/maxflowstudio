"""
Input Node Worker
"""

from typing import Dict, Any
from .base_worker import BaseWorker, ExecutionContext


class InputWorker(BaseWorker):
    """Worker for input nodes"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Input nodes pass through their configured data or flow inputs
        """
        self.logger.info("Executing input node", node_id=context.node_id)
        
        # Input nodes receive their data from the flow execution inputs
        # or from their configuration
        output_data = None
        
        # Check if data is provided in inputs (from flow execution)
        if inputs:
            output_data = inputs.get('default') or inputs.get('input') or next(iter(inputs.values()), None)
        
        # Otherwise use configured default value
        if output_data is None and config:
            output_data = config.get('default_value') or config.get('value')
        
        self.logger.info(
            "Input node output",
            node_id=context.node_id,
            has_output=output_data is not None
        )
        
        return self.format_output(output=output_data)