#!/usr/bin/env python3
"""
Simple integration test for the newly implemented components
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.component_base import ComponentInput, ComponentOutput, InputType, OutputType, ComponentMetadata
from src.core.component_registry import ComponentRegistry
from src.core.graph_executor import GraphExecutor, FlowDefinition, FlowNode, FlowEdge
from src.components.data_sources.text_input import TextInputComponent
from src.components.logic.text_combiner import TextCombinerComponent


async def test_component_base():
    """Test basic component functionality"""
    print("Testing TextInputComponent...")
    
    # Create text input component
    text_component = TextInputComponent(default_text="Hello, World!")
    
    # Test metadata
    metadata = text_component.metadata
    print(f"  Metadata: {metadata.name} - {metadata.display_name}")
    
    # Test execution
    result = await text_component.execute({})
    print(f"  Result: {result.outputs}")
    
    assert result.status.value == "completed"
    assert "text" in result.outputs
    assert result.outputs["text"] == "Hello, World!"
    
    print("  ✅ TextInputComponent test passed")


async def test_text_combiner():
    """Test text combiner component"""
    print("Testing TextCombinerComponent...")
    
    # Create text combiner component
    combiner = TextCombinerComponent(combination_method="join", separator=" | ")
    
    # Test execution
    inputs = {
        "input_1": "First",
        "input_2": "Second", 
        "input_3": "Third"
    }
    
    result = await combiner.execute(inputs)
    print(f"  Result: {result.outputs}")
    
    assert result.status.value == "completed"
    assert "combined_text" in result.outputs
    assert result.outputs["combined_text"] == "First | Second | Third"
    
    print("  ✅ TextCombinerComponent test passed")


async def test_component_registry():
    """Test component registry functionality"""
    print("Testing ComponentRegistry...")
    
    # Create registry
    registry = ComponentRegistry()
    
    # Register components manually
    registry.register_component("text_input", TextInputComponent)
    registry.register_component("text_combiner", TextCombinerComponent)
    
    # Test component creation
    text_comp = await registry.create_component_instance("text_input", default_text="Test")
    assert text_comp is not None
    
    combiner_comp = await registry.create_component_instance("text_combiner")
    assert combiner_comp is not None
    
    # Test registry stats
    stats = registry.get_registry_stats()
    print(f"  Registry stats: {stats.total_components} components")
    
    assert stats.total_components == 2
    
    print("  ✅ ComponentRegistry test passed")


async def test_graph_executor():
    """Test graph executor with simple flow"""
    print("Testing GraphExecutor...")
    
    # Create component registry
    registry = ComponentRegistry()
    registry.register_component("text_input", TextInputComponent)
    registry.register_component("text_combiner", TextCombinerComponent)
    
    # Create graph executor
    executor = GraphExecutor(registry.get_component_types())
    executor.component_registry = {
        "text_input": TextInputComponent,
        "text_combiner": TextCombinerComponent
    }
    
    # Create simple flow: two text inputs -> combiner
    flow_definition = FlowDefinition(
        id="test_flow",
        name="Test Flow",
        description="Simple test flow",
        nodes=[
            FlowNode(
                id="input1",
                component_type="text_input",
                display_name="Input 1",
                config={"default_text": "Hello"},
                inputs={}
            ),
            FlowNode(
                id="input2", 
                component_type="text_input",
                display_name="Input 2",
                config={"default_text": "World"},
                inputs={}
            ),
            FlowNode(
                id="combiner",
                component_type="text_combiner",
                display_name="Combiner",
                config={"combination_method": "join", "separator": " "},
                inputs={}
            )
        ],
        edges=[
            FlowEdge(
                id="edge1",
                source_node_id="input1",
                target_node_id="combiner",
                source_handle="text",
                target_handle="input_1"
            ),
            FlowEdge(
                id="edge2",
                source_node_id="input2", 
                target_node_id="combiner",
                source_handle="text",
                target_handle="input_2"
            )
        ],
        global_variables={}
    )
    
    # Execute flow
    try:
        context = await executor.execute_flow(flow_definition)
        print(f"  Execution status: {context.status}")
        print(f"  Node executions: {len(context.node_executions)}")
        
        # Check results
        for node_id, node_exec in context.node_executions.items():
            print(f"    {node_id}: {node_exec.status}")
            if node_exec.outputs:
                print(f"      Outputs: {list(node_exec.outputs.keys())}")
        
        assert context.status.value == "completed"
        print("  ✅ GraphExecutor test passed")
    
    except Exception as e:
        print(f"  ❌ GraphExecutor test failed: {e}")
        raise


async def main():
    """Run all integration tests"""
    print("🚀 Starting MAXFlowstudio Integration Tests\n")
    
    try:
        await test_component_base()
        print()
        
        await test_text_combiner()
        print()
        
        await test_component_registry()
        print()
        
        await test_graph_executor()
        print()
        
        print("🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())