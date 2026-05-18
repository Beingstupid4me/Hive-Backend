from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/regime")
async def macro_regime(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    payload = await services.macro.get_summary()
    return {
        "regime": payload["regime"],
        "macro": payload["macro"],
    }


@router.get("/history")
def macro_history(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {
        "regime": {
            "history": services.macro.get_history(limit=90),
        }
    }


@router.get("/latent-factors")
def macro_latent(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {
        "macro": {
            "latent_factors": services.macro.get_latent_factors(),
        }
    }


@router.get("/cross-asset")
async def macro_cross_asset(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {
        "macro": {
            "cross_asset_context": await services.macro.get_cross_asset_context(),
        }
    }


@router.get("/transitions")
async def macro_transitions(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    summary = await services.macro.get_summary()
    return {
        "regime": {
            "transition_events": services.macro.get_transition_events(limit=40),
            "transition_matrix": summary["regime"]["transition_matrix"],
        }
    }


@router.get("/all")
async def macro_all(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return await services.macro.get_macro_payload()
