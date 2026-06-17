import logging

from .config import get_settings


settings = get_settings()

logger = logging.getLogger(settings.APP_NAME)


async def lifespan(app):
    """FastAPI lifespan runs on startup and shutdown"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"Debug mode: {settings.DEBUG}")


    yield


    logger.info("Shutting down...")