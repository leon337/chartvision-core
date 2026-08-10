from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="ChartVision Core API",
    version="0.1.0",
    debug=settings.debug,
)
app.include_router(api_router)
