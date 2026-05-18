from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.schemas.contracts import ContactRequest
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/about")
def about(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.marketing.get_about_page()


@router.get("/methodology")
def methodology(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.marketing.get_methodology_page()


@router.get("/contact")
def contact_meta(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.marketing.get_contact_meta()


@router.get("/execute")
def execute_meta(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.marketing.get_execute_page()


@router.post("/contact")
def submit_contact(payload: ContactRequest, services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.marketing.submit_contact(payload)
