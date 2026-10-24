import os
from pathlib import Path
from typing import Optional, Set
import warnings
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

DEFAULT_DEV_JWT_SECRET = "super-secret-fashion-marketplace-key-2024"
WEAK_KEYWORDS: Set[str] = {
    "secret",
    "changeme",
    "password",
    "admin",
    "12345678",
    "placeholder",
    "default",
    "development",
}


def _resolve_and_validate_jwt_secret(
    jwt_secret: Optional[str],
    secret_key: Optional[str],
    environment: str,
) -> str:
    """Resolve and validate JWT secret across environments."""
    js = jwt_secret.strip() if jwt_secret is not None and jwt_secret.strip() else None
    sk = secret_key.strip() if secret_key is not None and secret_key.strip() else None

    if js and sk and js != sk:
        raise ValueError(
            "Ambiguous configuration: both JWT_SECRET and SECRET_KEY are set with conflicting values."
        )

    resolved = js or sk
    is_production = environment in ("production", "prod")

    if is_production:
        if not resolved:
            raise RuntimeError(
                "CRITICAL: Production environment cannot start without a secure JWT_SECRET."
            )
        if resolved == DEFAULT_DEV_JWT_SECRET:
            raise RuntimeError(
                "CRITICAL: Production environment cannot start using the insecure default JWT_SECRET."
            )
        if len(resolved) < 32:
            raise RuntimeError(
                "CRITICAL: JWT_SECRET does not meet production security standards. "
                "It must be at least 32 characters long."
            )
        resolved_lower = resolved.lower()
        for weak in WEAK_KEYWORDS:
            if weak in resolved_lower:
                raise RuntimeError(
                    "CRITICAL: JWT_SECRET does not meet production security standards. "
                    "It must not contain known weak placeholders."
                )
        if len(set(resolved)) < 8:
            raise RuntimeError(
                "CRITICAL: JWT_SECRET does not meet production security standards. "
                "It possesses insufficient character entropy."
            )
        return resolved

    # Development / Test fallback
    if not resolved:
        warnings.warn(
            "Using development fallback JWT secret. Set JWT_SECRET in production.",
            UserWarning,
            stacklevel=2,
        )
        return DEFAULT_DEV_JWT_SECRET

    return resolved


class Settings:
    def __init__(
        self,
        environment: Optional[str] = None,
        jwt_secret: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        raw_env = (
            environment
            if environment is not None
            else os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))
        )
        self.ENVIRONMENT: str = raw_env.strip().lower()

        raw_jwt_secret = jwt_secret if jwt_secret is not None else os.getenv("JWT_SECRET")
        raw_secret_key = secret_key if secret_key is not None else os.getenv("SECRET_KEY")

        self.JWT_SECRET: str = _resolve_and_validate_jwt_secret(
            raw_jwt_secret,
            raw_secret_key,
            self.ENVIRONMENT,
        )

        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.CHROMADB_HOST: str = os.getenv("CHROMADB_HOST", "localhost")
        self.CHROMADB_PORT: int = int(os.getenv("CHROMADB_PORT", "8000"))
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "mock-gemini-key")
        self.PAYMENT_RECIPIENT_ACCOUNT: str = os.getenv("PAYMENT_RECIPIENT_ACCOUNT", "")
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")


settings = Settings()