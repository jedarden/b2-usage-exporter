import csv
import io
import logging
import re

import boto3
from botocore.config import Config as BotoConfig

from .config import S3Endpoint

log = logging.getLogger(__name__)

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}/$")


def client(endpoint: S3Endpoint):
    return boto3.client(
        "s3",
        endpoint_url=endpoint.endpoint_url,
        aws_access_key_id=endpoint.access_key_id,
        aws_secret_access_key=endpoint.secret_access_key,
        region_name=endpoint.region,
        config=BotoConfig(s3={"addressing_style": endpoint.addressing_style}),
    )


def list_date_prefixes(s3, bucket: str):
    prefixes = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Delimiter="/"):
        for entry in page.get("CommonPrefixes", []):
            prefix = entry["Prefix"]
            if _DATE_PREFIX_RE.match(prefix):
                prefixes.append(prefix.rstrip("/"))
    return sorted(prefixes)


def _usage_csv_keys(s3, bucket: str, date_prefix: str):
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{date_prefix}/"):
        for obj in page.get("Contents", []):
            name = obj["Key"].rsplit("/", 1)[-1]
            if name.startswith("usage.") and name.endswith(".csv") and not name.startswith("usage.audit-"):
                keys.append(obj["Key"])
    return keys


def _parse_csv_rows(date: str, body: bytes):
    text = body.decode("utf-8")
    rows = []
    for record in csv.DictReader(io.StringIO(text)):
        bucket_name = (record.get("bucket_name") or "").strip()
        if not bucket_name:
            continue  # account-level transaction-summary row, not a bucket
        rows.append(
            {
                "date": date,
                "bucket_id": record.get("bucket_id", ""),
                "bucket_name": bucket_name,
                "stored_gb": float(record.get("stored_gb") or 0.0),
                "storage_byte_hours": int(record.get("storage_byte_hours") or 0),
                "uploaded_gb": float(record.get("uploaded_gb") or 0.0),
                "downloaded_gb": float(record.get("downloaded_gb") or 0.0),
                "deleted_gb": float(record.get("deleted_gb") or 0.0),
            }
        )
    return rows


def fetch_all_rows(endpoint: S3Endpoint):
    s3 = client(endpoint)
    date_prefixes = list_date_prefixes(s3, endpoint.bucket)
    log.info("found %d date folder(s) under s3://%s", len(date_prefixes), endpoint.bucket)

    rows = []
    for date_prefix in date_prefixes:
        for key in _usage_csv_keys(s3, endpoint.bucket, date_prefix):
            obj = s3.get_object(Bucket=endpoint.bucket, Key=key)
            rows.extend(_parse_csv_rows(date_prefix, obj["Body"].read()))
    log.info("parsed %d bucket-day row(s) total", len(rows))
    return rows
