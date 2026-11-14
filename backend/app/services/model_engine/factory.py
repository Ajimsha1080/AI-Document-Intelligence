import logging
from app.core.config import settings
from app.services.model_engine.base import BaseModelProvider
from app.services.model_engine.mock_adapter import MockModelAdapter

logger = logging.getLogger("model_factory")

def get_model_provider() -> BaseModelProvider:
    """
    Factory function returning the configured ModelProvider backend.
    Enforces UAE data sovereignty guards.
    Never silently masquerades fallback mock as real local engine.
    """
    backend = settings.MODEL_PROVIDER_BACKEND.lower()
    
    if settings.STRICT_LOCAL_ONLY and backend not in ["local", "mock"]:
        raise ValueError(
            "UAE Data Sovereignty Violation: STRICT_LOCAL_ONLY is active. "
            f"Model backend '{backend}' cannot be loaded because external egress is strictly forbidden."
        )

    if backend == "mock":
        return MockModelAdapter(is_fallback=False)
    elif backend == "local":
        # Check if real local OCR engine / weights are available
        try:
            from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
            if LocalOCRAdapter.is_available():
                return LocalOCRAdapter()
        except ImportError:
            pass
            
        logger.warning(
            "HONESTY/COMPLIANCE ALERT: MODEL_PROVIDER_BACKEND is configured as 'local', "
            "but real local OCR engine/weights are not yet loaded. "
            "Reporting 'mock-fallback' and logging explicit warning. Never silently falling back."
        )
        return MockModelAdapter(is_fallback=True)
    else:
        raise NotImplementedError(f"Model backend '{backend}' is not supported or compliant.")
