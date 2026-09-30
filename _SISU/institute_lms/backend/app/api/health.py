from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "backend": "FastAPI", "database": "Supabase PostgreSQL"}
