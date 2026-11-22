import logging
from app.core.config import settings
from app.services.model_engine.base import BaseModelProvider

logger = logging.getLogger("model_factory")

def get_model_provider() -> BaseModelProvider:
    """
    Factory function returning the configured ModelProvider backend.
    Enforces UAE data sovereignty guards.
    Mock adapters are strictly forbidden in production configurations and reside exclusively under /tests.
    """
    backend = settings.MODEL_PROVIDER_BACKEND.lower()
    is_prod = settings.ENVIRONMENT.lower() == "production"

    # 1. Enforce UAE data sovereignty
    if settings.STRICT_LOCAL_ONLY and backend not in ["local", "mock"]:
        raise ValueError(
            "UAE Data Sovereignty Violation: STRICT_LOCAL_ONLY is active. "
            f"Model backend '{backend}' cannot be loaded because external egress is strictly forbidden."
        )

    # 2. Strict Production Guard: Impossible to enable mock in production
    if is_prod:
        if backend == "mock":
            raise ValueError(
                "Production Configuration Violation: 'mock' model backend is strictly forbidden in production. "
                "A real sovereign local model provider must be configured."
            )
        from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
        if not LocalOCRAdapter.is_available():
            raise RuntimeError(
                "FATAL PRODUCTION ERROR: MODEL_PROVIDER_BACKEND is 'local', but real local OCR engine "
                "(Tesseract with 'ara' and 'eng') is missing. Production refuses to start without real engine."
            )
        return LocalOCRAdapter()

    # 3. Non-production / test execution paths
    if backend == "mock":
        if settings.ENVIRONMENT.lower() != "test":
            raise ValueError("Mock model adapter is only permitted when ENVIRONMENT=test")
        from tests.mock_adapter import MockModelAdapter
        return MockModelAdapter(is_fallback=False)

    elif backend == "local":
        from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
        if LocalOCRAdapter.is_available():
            return LocalOCRAdapter()

        # Only in ENVIRONMENT=test can we fall back to mock adapter
        if settings.ENVIRONMENT.lower() == "test":
            from tests.mock_adapter import MockModelAdapter
            return MockModelAdapter(is_fallback=True)

        logger.warning(
            "Tesseract is not available on this host. LocalOCRAdapter will extract empty fields with confidence 0.0."
        )
        return LocalOCRAdapter()

    else:
        raise NotImplementedError(f"Model backend '{backend}' is not supported or compliant.")
