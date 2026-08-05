# b2-usage-exporter Plan

## Overview

A small, generic tool that polls a Backblaze B2 account's Usage Reports
(daily per-bucket storage/bandwidth CSVs, written by Backblaze to an
account-specific `b2-reports-$ACCOUNTID` bucket once enabled) and writes a
single combined Parquet file — one row per bucket per day — to any
S3-compatible destination bucket. Written to feed a storage-consumption
dashboard that reads the Parquet file client-side (e.g. via duckdb-wasm or
hyparquet), but this tool has no dependency on any particular dashboard or
deployment — every account, bucket, and credential is supplied via
environment variables at deploy time.

This repo is **public**. Nothing account-specific, cluster-specific, or
otherwise private may be hardcoded anywhere in source, tests, or docs —
only placeholder/example values. Real values live entirely in whatever
private deployment config (e.g. a Kubernetes Secret/ConfigMap) wires up the
container at runtime.

## Architecture

```
                  poll loop (every POLL_INTERVAL_SECONDS)
                            |
                            v
   SOURCE_S3_*  --list-->  date-prefixed folders in the B2 Usage Reports bucket
        |                   |
        |                  filter: usage.*.csv, skip usage.audit-*.csv
        |                   |
        |                  download + parse each CSV's bucket-level rows
        |                   v
        |         combined in-memory table:
        |         date, bucket_id, bucket_name, stored_gb,
        |         storage_byte_hours, uploaded_gb, downloaded_gb, deleted_gb
        |                   |
        |                  write to a single Parquet file
        v                   v
   DEST_S3_*   <--upload-- usage.parquet
                            + meta.json (version, generated_at)
```

- No persistent state, no database, no PVC. Each cycle re-lists and
  re-downloads everything under the source bucket and rewrites the Parquet
  file from scratch — the dataset (one account's daily usage rows) is small
  enough that this is simpler and more self-healing than incremental state.
- Runs as a long-lived process with an internal sleep loop, not a one-shot
  script or a Kubernetes `Job`/`CronJob` — the deployment wrapping this
  container is expected to be a `Deployment` that just keeps the process
  running.
- Small HTTP server for `/health` (liveness/readiness), since it's expected
  to run under Kubernetes.

## Components

- `src/config.py` — loads and validates all configuration from environment
  variables; fails fast with a clear error if anything required is missing.
- `src/reports.py` — talks to the *source* S3-compatible endpoint: lists
  date-prefixed folders, downloads and parses the Usage Report CSVs into
  row dicts.
- `src/exporter.py` — builds the Parquet file from collected rows, uploads
  it to the *destination* S3-compatible endpoint, and writes a `meta.json`
  provenance sidecar (this build's version + a UTC generation timestamp)
  alongside it every cycle — see `docs/notes/configuration.md`.
- `src/main.py` — entrypoint: wires config → reports → exporter into the
  poll loop, plus the health server.

## Data Models

Output Parquet schema, one row per (date, bucket):

| Column | Type | Notes |
|---|---|---|
| `date` | string (`YYYY-MM-DD`) | the report day |
| `bucket_id` | string | |
| `bucket_name` | string | |
| `stored_gb` | float | end-of-day storage |
| `storage_byte_hours` | int64 | the actual billable figure |
| `uploaded_gb` | float | |
| `downloaded_gb` | float | |
| `deleted_gb` | float | |

Source CSV rows with an empty `bucket_name` (account-level transaction
summary rows) are dropped — only per-bucket rows are kept.

## Implementation Phases

- [x] Phase 1: Repo scaffolded
- [x] Phase 2: Config loading + source report listing/parsing
- [x] Phase 3: Parquet build + destination upload
- [x] Phase 4: Poll loop + health server, containerized
- [x] Phase 5: CI wired (declarative-config), deployed — verified live 2026-08-05
- [x] Phase 6: `meta.json` provenance sidecar (version + generated_at), for dashboards to display

## Open Questions

- Whether to cap how far back the source listing scans (`LOOKBACK_DAYS` or
  similar) — currently unbounded (scans every date folder that exists).
  Fine at today's scale; revisit if the source bucket accumulates years of
  history and re-scanning every cycle becomes wasteful.
- Retry/backoff behavior on a transient S3 error mid-cycle — currently: log
  and retry next cycle rather than crash-looping the pod.
