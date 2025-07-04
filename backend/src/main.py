"""
MAX Flowstudio Backend Main Application
Flow: main.py -> config -> middleware -> routers -> services -> database
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.config.settings import get_settings
from src.core.database import engine
from src.middleware.auth import auth_middleware
from src.middleware.logging import LoggingMiddleware
from src.workers import initialize_workers
from src.core.message_queue import message_queue
from src.core.queued_workflow_engine import initialize_queued_orchestrator
from src.services.deployment_service import deployment_service
from src.services.monitoring_service import monitoring_service

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    logger.info("Starting MAX Flowstudio Backend", version=settings.APP_VERSION)
    
    # Startup
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
        
        # Initialize workers
        initialize_workers()
        logger.info("Workers initialized")
        
        # Initialize message queue (optional)
        try:
            await message_queue.connect()
            await initialize_queued_orchestrator(message_queue)
            logger.info("Message queue connected and queued orchestrator initialized")
        except Exception as e:
            logger.warning("Failed to connect to message queue, using direct execution", error=str(e))
            # Application can still work without RabbitMQ
        
        # Load active deployments
        from src.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await deployment_service.load_active_deployments(db)
        logger.info("Active deployments loaded")
        
        # Start monitoring service (temporarily disabled due to MessageQueue issue)
        # await monitoring_service.start_monitoring()
        logger.info("Monitoring service disabled temporarily")
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MAX Flowstudio Backend")
    # await monitoring_service.stop_monitoring()  # Disabled
    await message_queue.disconnect()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )
    
    # Add middlewares
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Add custom auth middleware
    app.middleware("http")(auth_middleware)
    
    # Include routers
    from src.api import health, auth, flows, nodes, executions, api_keys, system, deployments, deployed, workspaces, flow_versions, test_execution, environment_variables, admin, flow_templates, rag
    from src.api.websocket_handlers import websocket_flow_test
    
    app.include_router(health.router, prefix="/api/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
    app.include_router(flow_versions.router, tags=["flow-versions"])
    app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])
    app.include_router(executions.router, prefix="/api/executions", tags=["executions"])
    app.include_router(api_keys.router, prefix="/api/api-keys", tags=["api-keys"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(deployments.router, tags=["deployments"])
    app.include_router(deployed.router, tags=["deployed-apis"])
    app.include_router(workspaces.router, tags=["workspaces"])
    app.include_router(environment_variables.router, prefix="/api/environment-variables", tags=["environment-variables"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    app.include_router(test_execution.router, prefix="/api/test", tags=["test"])
    app.include_router(flow_templates.router, tags=["flow-templates"])
    app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
    
    # Add WebSocket endpoint
    app.websocket("/ws/flow-test/{flow_id}")(websocket_flow_test)
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
        log_config=None,  # Use structlog instead
    )