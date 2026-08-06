import io
import json
import logging
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from .config import S3Endpoint
from .reports import client as s3_client

log = logging.getLogger(__name__)

_SCHEMA = pa.schema(
    [
        ("date", pa.string()),
        ("bucket_id", pa.string()),
        ("bucket_name", pa.string()),
        ("stored_gb", pa.float64()),
        ("storage_byte_hours", pa.int64()),
        ("uploaded_gb", pa.float64()),
        ("downloaded_gb", pa.float64()),
        ("deleted_gb", pa.float64()),
    ]
)


def rows_to_parquet_bytes(rows) -> bytes:
    table = pa.Table.from_pylist(rows, schema=_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def upload(endpoint: S3Endpoint, key: str, data: bytes):
    s3 = s3_client(endpoint)
    s3.put_object(Bucket=endpoint.bucket, Key=key, Body=data, ContentType="application/octet-stream")
    log.info("uploaded %d bytes to s3://%s/%s", len(data), endpoint.bucket, key)


def meta_bytes(version: str, data_size: int) -> bytes:
    # Explicit "Z" suffix, not a naive isoformat() -- a timestamp with no UTC
    # offset gets misread as local time by browsers, making recent
    # generation times appear to be in the future.
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return json.dumps(
        {"version": version, "generated_at": generated_at, "size": data_size}
    ).encode("utf-8")


def upload_meta(endpoint: S3Endpoint, key: str, version: str, data_size: int):
    s3 = s3_client(endpoint)
    data = meta_bytes(version, data_size)
    s3.put_object(Bucket=endpoint.bucket, Key=key, Body=data, ContentType="application/json")
    log.info("uploaded meta to s3://%s/%s", endpoint.bucket, key)
