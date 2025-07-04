"""
┌──────────────────────────────────────────────────────────────┐
│                    Exception Handling Flow                  │
│                                                              │
│  [Error] → [Classify] → [Log] → [Response] → [Client]      │
│     ↓         ↓         ↓         ↓          ↓             │
│  오류발생   타입분류    로그기록   응답생성    클라이언트      │
│                                                              │
│  Error Types: Validation → Not Found → Auth → Server       │
│  HTTP Status: 400 → 404 → 401/403 → 500                   │
└──────────────────────────────────────────────────────────────┘

Exception classes for MAX Flowstudio
Flow: Error occurrence → Classification → Logging → HTTP response → Client handling
"""

from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger()


class MAXFlowstudioException(Exception):
    """
    Base exception class for MAX Flowstudio.
    
    Exception Handling Flow:
    1. error_occurred() → Capture error details and context
    2. classify_error() → Determine error type and severity
    3. log_error() → Record error with structured logging
    4. format_response() → Create appropriate HTTP response
    5. send_to_client() → Return error to user
    
    Features:
    - Structured error context
    - HTTP status code mapping
    - Detailed error messages
    - Optional error codes
    - Nested exception support
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """Initialize base exception."""
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        
        # Log the exception
        logger.error(
            "MAXFlowstudio exception occurred",
            error_type=self.__class__.__name__,
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )


class ValidationError(MAXFlowstudioException):
    """
    Validation error for input/configuration validation.
    
    Validation Error Flow:
    1. Input validation fails
    2. Capture validation details
    3. Return 400 Bad Request
    4. Client corrects input
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        error_code: str = "VALIDATION_ERROR"
    ):
        """Initialize validation error."""
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=400
        )
        self.field = field
        self.value = value


class NotFoundError(MAXFlowstudioException):
    """
    Resource not found error.
    
    Not Found Error Flow:
    1. Resource lookup fails
    2. Capture resource details
    3. Return 404 Not Found
    4. Client handles missing resource
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        error_code: str = "NOT_FOUND"
    ):
        """Initialize not found error."""
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=404
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthenticationError(MAXFlowstudioException):
    """
    Authentication error for unauthorized access.
    
    Authentication Error Flow:
    1. Authentication check fails
    2. Capture auth context
    3. Return 401 Unauthorized
    4. Client provides credentials
    """
    
    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "AUTHENTICATION_REQUIRED"
    ):
        """Initialize authentication error."""
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401
        )


class AuthorizationError(MAXFlowstudioException):
    """
    Authorization error for forbidden access.
    
    Authorization Error Flow:
    1. Permission check fails
    2. Capture permission context
    3. Return 403 Forbidden
    4. Client requests proper access
    """
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        error_code: str = "INSUFFICIENT_PERMISSIONS"
    ):
        """Initialize authorization error."""
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=403
        )
        self.required_permission = required_permission


# Alias for backward compatibility
PermissionError = AuthorizationError


class ConflictError(MAXFlowstudioException):
    """
    Conflict error for resource conflicts.
    
    Conflict Error Flow:
    1. Resource conflict detected
    2. Capture conflict details
    3. Return 409 Conflict
    4. Client resolves conflict
    """
    
    def __init__(
        self,
        message: str,
        conflicting_resource: Optional[str] = None,
        error_code: str = "RESOURCE_CONFLICT"
    ):
        """Initialize conflict error."""
        details = {}
        if conflicting_resource:
            details["conflicting_resource"] = conflicting_resource
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=409
        )
        self.conflicting_resource = conflicting_resource


class ExternalServiceError(MAXFlowstudioException):
    """
    External service error for third-party service failures.
    
    External Service Error Flow:
    1. External API call fails
    2. Capture service details
    3. Return 502 Bad Gateway
    4. Client retries or uses fallback
    """
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        error_code: str = "EXTERNAL_SERVICE_ERROR"
    ):
        """Initialize external service error."""
        details = {}
        if service_name:
            details["service_name"] = service_name
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=502
        )
        self.service_name = service_name


class ComponentExecutionError(MAXFlowstudioException):
    """
    Component execution error for workflow component failures.
    
    Component Execution Error Flow:
    1. Component execution fails
    2. Capture component details
    3. Return 500 Internal Server Error
    4. Client handles execution failure
    """
    
    def __init__(
        self,
        message: str,
        component_id: Optional[str] = None,
        component_type: Optional[str] = None,
        execution_id: Optional[str] = None,
        error_code: str = "COMPONENT_EXECUTION_ERROR"
    ):
        """Initialize component execution error."""
        details = {}
        if component_id:
            details["component_id"] = component_id
        if component_type:
            details["component_type"] = component_type
        if execution_id:
            details["execution_id"] = execution_id
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=500
        )
        self.component_id = component_id
        self.component_type = component_type
        self.execution_id = execution_id


class WorkflowExecutionError(MAXFlowstudioException):
    """
    Workflow execution error for flow execution failures.
    
    Workflow Execution Error Flow:
    1. Workflow execution fails
    2. Capture workflow details
    3. Return 500 Internal Server Error
    4. Client handles workflow failure
    """
    
    def __init__(
        self,
        message: str,
        flow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        failed_node_id: Optional[str] = None,
        error_code: str = "WORKFLOW_EXECUTION_ERROR"
    ):
        """Initialize workflow execution error."""
        details = {}
        if flow_id:
            details["flow_id"] = flow_id
        if execution_id:
            details["execution_id"] = execution_id
        if failed_node_id:
            details["failed_node_id"] = failed_node_id
            
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=500
        )
        self.flow_id = flow_id
        self.execution_id = execution_id
        self.failed_node_id = failed_node_id