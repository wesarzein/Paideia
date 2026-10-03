from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_roles
from app.models.user import User

router = APIRouter()


@router.get("")
def calculate_kpis(
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> dict[str, str]:
    raise HTTPException(status_code=501, detail="El módulo de analítica aún no está habilitado")
