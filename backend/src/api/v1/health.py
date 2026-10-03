from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone

from ...db.session import get_db
from ...core.config import get_settings


router = APIRouter()
settings = get_settings()

@router.get('/health', status_code=status.HTTP_200_OK)
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "Ok"
    try:
        # Check if the database is reachable
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"Error: {str(e)}"

    return {
        "status": "Ok" if db_status == "Ok" else "Degraded",
        "database": db_status,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }