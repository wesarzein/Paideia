from collections.abc import Callable

from fastapi import HTTPException, status


def require_roles(*allowed_roles: str) -> Callable[[], None]:
    def dependency() -> None:
        if not allowed_roles:
            return
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="RBAC preparado para implementarse en el sprint de autenticacion.",
        )

    return dependency
