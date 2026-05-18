from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.container import ServiceContainer


@lru_cache
def get_service_container() -> ServiceContainer:
    return ServiceContainer(get_settings())


def get_services() -> ServiceContainer:
    return get_service_container()
