"""
OpenAI Prompt Processing
Flow: Input text → Template application → Message formatting → API preparation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class PromptTemplate:
    """
    Template for formatting prompts with variable substitution.
    
    Template Process:
    1. define_template() → Set template string with placeholders
    2. validate_variables() → Check required variables are provided
    3. substitute_variables() → Replace placeholders with actual values
    4. format_output() → Apply final formatting rules
    
    Responsibilities:
    - Template string management and validation
    - Variable substitution and escaping
    - Dynamic prompt generation
    - Context preservation across interactions
    """
    
    def __init__(self, template: str, required_vars: List[str] = None):
        """Initialize prompt template."""
        self.template = template
        self.required_vars = required_vars or []
        self.logger = logger.bind(component="prompt_template")
    
    def format(self, **variables) -> str:
        """Format template with provided variables."""
        # Validate required variables
        missing_vars = [var for var in self.required_vars if var not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        try:
            return self.template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Template variable not found: {e}")
        except Exception as e:
            raise ValueError(f"Template formatting error: {e}")


class OpenAIPromptProcessor:
    """
    Processes and formats prompts for OpenAI API calls.
    
    Processor Flow:
    1. prepare_messages() → Convert input to OpenAI message format
    2. apply_system_prompt() → Add system instructions and context
    3. format_user_input() → Clean and structure user messages
    4. add_conversation_history() → Include previous interactions
    5. validate_message_format() → Ensure API compatibility
    
    Responsibilities:
    - Message formatting for OpenAI API
    - System prompt management
    - Conversation history handling
    - Input validation and sanitization
    """
    
    def __init__(self):
        """Initialize prompt processor."""
        self.logger = logger.bind(component="openai_prompt")
        self.conversation_history: List[Dict[str, str]] = []
        
        # Default templates
        self.system_template = PromptTemplate(
            "You are {role}. {instructions}\n\nCurrent context: {context}",
            required_vars=["role", "instructions"]
        )
    
    def prepare_messages(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        role: str = "a helpful AI assistant",
        instructions: str = "Provide helpful, accurate, and detailed responses.",
        context: str = "",
        include_history: bool = True,
        max_history: int = 10
    ) -> List[Dict[str, str]]:
        """
        Prepare messages for OpenAI API call.
        
        Args:
            user_input: User's input text
            system_prompt: Custom system prompt (overrides template)
            role: AI role description
            instructions: Specific instructions for the AI
            context: Additional context information
            include_history: Whether to include conversation history
            max_history: Maximum number of history messages to include
            
        Returns:
            List of message dictionaries in OpenAI format
        """
        messages = []
        
        # Add system message
        if system_prompt:
            system_message = system_prompt
        else:
            system_message = self.system_template.format(
                role=role,
                instructions=instructions,
                context=context or "No specific context provided"
            )
        
        messages.append({
            "role": "system",
            "content": system_message
        })
        
        # Add conversation history if requested
        if include_history and self.conversation_history:
            # Limit history to max_history messages
            recent_history = self.conversation_history[-max_history:]
            messages.extend(recent_history)
        
        # Add current user input
        messages.append({
            "role": "user", 
            "content": self._sanitize_input(user_input)
        })
        
        return messages
    
    def add_to_history(self, user_message: str, assistant_response: str) -> None:
        """Add interaction to conversation history."""
        self.conversation_history.extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ])
        
        # Keep history manageable (last 50 messages)
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        self.logger.info("Conversation history cleared")
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent issues."""
        if not isinstance(text, str):
            text = str(text)
        
        # Remove potential harmful content
        text = text.strip()
        
        # Limit input length (prevent extremely long inputs)
        max_length = 50000  # ~50k characters
        if len(text) > max_length:
            text = text[:max_length] + "... [truncated]"
            self.logger.warning("Input truncated due to length", original_length=len(text))
        
        return text
    
    def create_chat_template(self, template_str: str, required_vars: List[str] = None) -> PromptTemplate:
        """Create a new prompt template."""
        return PromptTemplate(template_str, required_vars)
    
    def format_response_for_output(self, response_content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format API response for component output.
        
        Args:
            response_content: Content from OpenAI API
            metadata: Additional response metadata
            
        Returns:
            Formatted output dictionary
        """
        output = {
            "response": response_content.strip(),
            "timestamp": datetime.utcnow().isoformat(),
            "length": len(response_content),
            "word_count": len(response_content.split()),
        }
        
        if metadata:
            output.update({
                "model": metadata.get("model"),
                "usage": metadata.get("usage", {}),
                "finish_reason": metadata.get("finish_reason"),
                "response_time": metadata.get("response_time")
            })
        
        return output