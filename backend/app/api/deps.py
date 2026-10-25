"""FastAPI dependency that provides the singleton ModelManager."""
from __future__ import annotations

from app.models.manager import ModelManager, get_model_manager


def dep_model_manager() -> ModelManager:
    """
    FastAPI dependency that returns the singleton :class:`ModelManager`.

    Usage in a route::

        @router.post("/something")
        async def my_route(manager: ModelManager = Depends(dep_model_manager)):
            ...
    """
    return get_model_manager()
