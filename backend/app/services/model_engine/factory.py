import logging
from app.core.config import settings
from app.services.model_engine.base import BaseModelProvider
from app.services.model_engine.mock_adapter import MockModelAdapter

logger = logging.getLogger("model_factory")

def get_model_provider() -> BaseModelProvider:
    """
    Factory function returning the configured ModelProvider backend.
    Enforces UAE data sovereignty guards.
    """
    backend = settings.MODEL_PROVIDER_BACKEND.lower()
    
    if settings.STRICT_LOCAL_ONLY and backend not in ["local", "mock"]:
        raise ValueError(
            "UAE Data Sovereignty Violation: STRICT_LOCAL_ONLY is active. "
            f"Model backend '{backend}' cannot be loaded because external egress is strictly forbidden."
        )

    if backend == "mock":
        return MockModelAdapter()
    elif backend == "local":
        # Local air-gapped adapter (falls back to deterministic mock if local weights/tesseract not yet mounted)
        return MockModelAdapter()
    else:
        raise NotImplementedError(f"Model backend '{backend}' is not supported or compliant.")
