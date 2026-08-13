import ipaddress
import re
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="API Studio AI Backend")
    environment: str = Field(...)
    database_url: str = Field(..., min_length=10)
    secret_key: str = Field(..., min_length=32)
    refresh_secret_key: str = Field(..., min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)
    cors_origins: str = Field(...)
    trusted_hosts: str = Field(...)
    allow_localhost_targets: bool | None = Field(default=None, description="Allow requests targeting localhost/loopback/private IPs when enabled. Defaults to true in development and false in production if unset.")
    max_request_size: int = Field(...)
    max_upload_size: int = Field(...)
    max_response_size: int = Field(...)
    request_timeout_seconds: int = Field(...)
    max_redirects: int = Field(default=5)
    log_level: str = Field(default="INFO")
    ai_provider: str = Field(default="local")
    ai_model: str = Field(default="local-sim")
    ai_chat_model: str = Field(default="openai/gpt-oss-120b")
    ai_large_context_model: str = Field(default="moonshotai/kimi-k2-instruct")
    ai_fast_model: str = Field(default="llama-3.3-70b-versatile")
    ai_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    ai_max_tokens: int = Field(default=1024, gt=0)
    ai_timeout_seconds: int = Field(default=30, gt=0)
    ai_retries: int = Field(default=2, ge=0)
    groq_api_key: str | None = Field(default=None)
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")

    @classmethod
    def _parse_csv(cls, value: str, label: str) -> list[str]:
        if not isinstance(value, str):
            raise ValueError(f"{label} must be a comma-separated string of values.")
        items = [item.strip() for item in value.split(",") if item.strip()]
        if not items:
            raise ValueError(f"{label} cannot be empty.")
        if "*" in items:
            raise ValueError("Wildcard origins or hosts are not allowed.")
        return items

    @classmethod
    def _validate_origin(cls, origin: str) -> str:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Invalid origin '{origin}'. Expected 'http://' or 'https://'.")
        if not parsed.netloc:
            raise ValueError(f"Invalid origin '{origin}'. Missing host/port.")
        if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
            raise ValueError(f"Invalid origin '{origin}'. Origins must not include a path, query, or fragment.")
        return origin

    @classmethod
    def _validate_trusted_host(cls, host: str) -> str:
        if host.startswith("["):
            if "]" not in host:
                raise ValueError(f"Invalid trusted host '{host}'. IPv6 hosts must be bracketed.")
            address, _, port_part = host[1:].partition("]")
            if not address:
                raise ValueError(f"Invalid trusted host '{host}'. IPv6 address is required.")
            try:
                ipaddress.IPv6Address(address)
            except ValueError as exc:
                raise ValueError(f"Invalid trusted host '{host}': {exc}") from exc
            if port_part:
                if not port_part.startswith(":") or not port_part[1:].isdigit():
                    raise ValueError(f"Invalid trusted host '{host}'. Port must be numeric.")
        else:
            if ":" in host:
                host_name, port = host.rsplit(":", 1)
                if not port.isdigit() or not (1 <= int(port) <= 65535):
                    raise ValueError(f"Invalid trusted host '{host}'. Port must be numeric between 1 and 65535.")
            else:
                host_name = host
            if not host_name:
                raise ValueError(f"Invalid trusted host '{host}'. Host name cannot be empty.")
            if host_name[0].isdigit():
                try:
                    ipaddress.IPv4Address(host_name)
                except ValueError as exc:
                    raise ValueError(f"Invalid trusted host '{host}': {exc}") from exc
            else:
                if not re.fullmatch(r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*", host_name):
                    raise ValueError(f"Invalid trusted host '{host}'.")
        return host

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        items = cls._parse_csv(value, "CORS_ORIGINS")
        return ",".join(cls._validate_origin(item) for item in items)

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def validate_trusted_hosts(cls, value: str) -> str:
        items = cls._parse_csv(value, "TRUSTED_HOSTS")
        return ",".join(cls._validate_trusted_host(item) for item in items)

    @field_validator("max_request_size", "max_upload_size", "max_response_size", "request_timeout_seconds", "max_redirects")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Configuration values must be positive.")
        return value

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    def allow_localhost_targets_enabled(self) -> bool:
        """Return whether localhost/loopback/private targets are permitted.

        If `ALLOW_LOCALHOST_TARGETS` is explicitly set in the environment it will be respected.
        Otherwise defaults to True in development and False in production.
        """
        if self.allow_localhost_targets is not None:
            return bool(self.allow_localhost_targets)
        return (self.environment or "").lower() == "development"

    @field_validator("groq_api_key", "groq_base_url", mode="before")
    @classmethod
    def trim_optional_config(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value or None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
