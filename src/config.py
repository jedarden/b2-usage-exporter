import os
from dataclasses import dataclass


class ConfigError(Exception):
    pass


def _require(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"missing required env var: {name}")
    return value


def _optional(name, default):
    value = os.environ.get(name, "").strip()
    return value if value else default


@dataclass(frozen=True)
class S3Endpoint:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket: str
    addressing_style: str
    region: str


def _default_meta_key(dest_key):
    directory = dest_key.rsplit("/", 1)[0] if "/" in dest_key else ""
    return f"{directory}/meta.json" if directory else "meta.json"


@dataclass(frozen=True)
class Config:
    source: S3Endpoint
    dest: S3Endpoint
    dest_key: str
    dest_meta_key: str
    version: str
    poll_interval_seconds: int
    health_port: int
    log_level: str


def _read_version(version_file):
    try:
        with open(version_file) as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def load() -> Config:
    source = S3Endpoint(
        endpoint_url=_require("SOURCE_S3_ENDPOINT"),
        access_key_id=_require("SOURCE_S3_ACCESS_KEY_ID"),
        secret_access_key=_require("SOURCE_S3_SECRET_ACCESS_KEY"),
        bucket=_require("SOURCE_S3_BUCKET"),
        addressing_style=_optional("SOURCE_S3_ADDRESSING_STYLE", "virtual"),
        region=_optional("SOURCE_S3_REGION", "us-east-1"),
    )
    dest = S3Endpoint(
        endpoint_url=_require("DEST_S3_ENDPOINT"),
        access_key_id=_require("DEST_S3_ACCESS_KEY_ID"),
        secret_access_key=_require("DEST_S3_SECRET_ACCESS_KEY"),
        bucket=_require("DEST_S3_BUCKET"),
        addressing_style=_optional("DEST_S3_ADDRESSING_STYLE", "virtual"),
        region=_optional("DEST_S3_REGION", "us-east-1"),
    )
    dest_key = _optional("DEST_S3_KEY", "usage.parquet")
    return Config(
        source=source,
        dest=dest,
        dest_key=dest_key,
        dest_meta_key=_optional("DEST_S3_META_KEY", _default_meta_key(dest_key)),
        version=_read_version(_optional("VERSION_FILE", "VERSION")),
        poll_interval_seconds=int(_optional("POLL_INTERVAL_SECONDS", "3600")),
        health_port=int(_optional("HEALTH_PORT", "8080")),
        log_level=_optional("LOG_LEVEL", "INFO"),
    )
