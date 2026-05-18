from __future__ import annotations

from app.schemas.contracts import ContactRequest


class MarketingService:
    def get_about_page(self) -> dict[str, object]:
        return {
            "about": {
                "hero": {
                    "title": "Research-First Infrastructure For Institutional Capital",
                },
                "principles": [
                    "Feature engineering before architecture complexity",
                    "Risk controls before return maximization",
                    "Ensemble intelligence over monolithic models",
                    "Glass-box interpretability over opaque black boxes",
                ],
                "highlights": [
                    {
                        "title": "Meta-Quant Pipeline",
                        "body": "Cross-sectional ranking, meta-labeling, and regime-aware sizing.",
                    },
                    {
                        "title": "Institutional Risk Engine",
                        "body": "HRP, dynamic leverage overlays, and transaction-cost-aware rebalancing.",
                    },
                    {
                        "title": "Operational Explainability",
                        "body": "Every recommendation ships with feature-level rationale and audit trail.",
                    },
                ],
            }
        }

    def get_methodology_page(self) -> dict[str, object]:
        return {
            "methodology": {
                "hero": {
                    "title": "From Data To Decision",
                },
                "stages": [
                    {
                        "title": "Data Foundation",
                        "detail": "Adjusted OHLCV ingestion with survivorship-aware universe handling.",
                    },
                    {
                        "title": "Feature Factory",
                        "detail": "Rolling rank IC filtering, orthogonalization, and feature diagnostics.",
                    },
                    {
                        "title": "Meta-Quant Modeling",
                        "detail": "Ensemble LightGBM actors with meta-labeling and calibrated probabilities.",
                    },
                    {
                        "title": "Risk & Deployment",
                        "detail": "Regime-aware HRP portfolio construction and monitored live execution.",
                    },
                ],
                "governance_note": "All model outputs are constrained by risk budgets, drawdown controls, and explainability checks.",
            }
        }

    def get_execute_page(self) -> dict[str, object]:
        return {
            "execute": {
                "status": "IN_PROGRESS",
            },
            "placeholder": {
                "title": "This Page Is In Progress",
                "description": "Execution integrations are being hardened for production routing.",
            },
        }

    def get_contact_meta(self) -> dict[str, object]:
        return {
            "contact": {
                "form": {
                    "submit": "/api/contact",
                    "success_message": "Your request has been queued. A team member will reach out within SLA.",
                },
                "response_window_hours": 24,
            }
        }

    def submit_contact(self, payload: ContactRequest) -> dict[str, object]:
        return {
            "accepted": True,
            "name": payload.name,
            "email": payload.email,
            "message": "Submission received. We will respond within 24 hours.",
        }
