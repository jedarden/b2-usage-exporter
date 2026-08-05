import io
import logging

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
