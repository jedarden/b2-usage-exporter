# b2-usage-exporter

A small, generic tool that polls a Backblaze B2 account's [Usage Reports](https://www.backblaze.com/docs/cloud-storage-use-partner-api-reports) (daily per-bucket storage/bandwidth CSVs) and writes a combined Parquet file to any S3-compatible destination bucket. Runs as a long-lived loop (not a one-shot script or cron job) — polls on an interval and re-uploads whenever new report data appears.

Nothing account-specific or infrastructure-specific is hardcoded — every endpoint, bucket, key prefix, and credential is supplied at deploy time via environment variables. See [`docs/notes/configuration.md`](docs/notes/configuration.md) for the full list.

## Structure

- `src/` — the exporter itself
- `docs/notes/` — features, constraints, design decisions
- `docs/research/` — external reference material and prior art
- `docs/plan/plan.md` — complete application plan

## Usage

```bash
docker run --rm \
  -e SOURCE_S3_ENDPOINT=https://s3.us-west-002.backblazeb2.com \
  -e SOURCE_S3_ACCESS_KEY_ID=... \
  -e SOURCE_S3_SECRET_ACCESS_KEY=... \
  -e SOURCE_S3_BUCKET=b2-reports-XXXXXXXXXXXX \
  -e DEST_S3_ENDPOINT=https://your-s3-compatible-endpoint \
  -e DEST_S3_ACCESS_KEY_ID=... \
  -e DEST_S3_SECRET_ACCESS_KEY=... \
  -e DEST_S3_BUCKET=your-bucket \
  -e DEST_S3_KEY=some/prefix/usage.parquet \
  ronaldraygun/b2-usage-exporter:0.1.0
```

See [`docs/notes/configuration.md`](docs/notes/configuration.md) for every
variable, its default, and what it controls.
