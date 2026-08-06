# Configuration

Everything is supplied via environment variables. No defaults reference any
real account, bucket, or endpoint — this repo is public.

## Source (the B2 Usage Reports bucket — read-only)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SOURCE_S3_ENDPOINT` | yes | | e.g. `https://s3.us-west-002.backblazeb2.com` |
| `SOURCE_S3_ACCESS_KEY_ID` | yes | | scope to `listFiles`+`readFiles` on the reports bucket only |
| `SOURCE_S3_SECRET_ACCESS_KEY` | yes | | |
| `SOURCE_S3_BUCKET` | yes | | the account's `b2-reports-$ACCOUNTID` bucket. Note: this bucket does not appear in B2's native `b2_list_buckets` API even with a full-access key — you have to already know its name (Backblaze's own Usage Reports docs give the naming convention) |
| `SOURCE_S3_ADDRESSING_STYLE` | no | `virtual` | `virtual` or `path` |
| `SOURCE_S3_REGION` | no | `us-east-1` | boto3 requires some value even when the backend ignores it |

## Destination (any S3-compatible bucket — write)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DEST_S3_ENDPOINT` | yes | | |
| `DEST_S3_ACCESS_KEY_ID` | yes | | needs write access to `DEST_S3_KEY` |
| `DEST_S3_SECRET_ACCESS_KEY` | yes | | |
| `DEST_S3_BUCKET` | yes | | |
| `DEST_S3_KEY` | no | `usage.parquet` | full object key within the bucket — include any prefix here, e.g. `b2-usage/data/usage.parquet` |
| `DEST_S3_META_KEY` | no | same directory as `DEST_S3_KEY`, filename `meta.json` | where the provenance sidecar (see below) is written |
| `DEST_S3_ADDRESSING_STYLE` | no | `virtual` | some S3-compatible servers (e.g. Garage) require `path` — no per-bucket virtual-host DNS |
| `DEST_S3_REGION` | no | `us-east-1` | |

## Behavior

| Variable | Required | Default | Notes |
|---|---|---|---|
| `POLL_INTERVAL_SECONDS` | no | `3600` | source data changes at most once/day upstream; hourly is already generous |
| `HEALTH_PORT` | no | `8080` | serves `GET /health` → `200 OK` once the first successful cycle has completed |
| `LOG_LEVEL` | no | `INFO` | standard Python logging levels |
| `VERSION_FILE` | no | `VERSION` | path to a file containing this build's semver, embedded in `meta.json` (see below) — the Dockerfile copies the repo's `VERSION` file to this path by default |

## Provenance sidecar (`meta.json`)

Every cycle, alongside the Parquet file, the exporter writes a small JSON
object to `DEST_S3_META_KEY`:

```json
{"version": "0.3.0", "generated_at": "2026-08-05T21:40:00Z", "size": 6544}
```

`generated_at` is always UTC with an explicit `Z` suffix — never a naive
timestamp, which browsers misread as local time and can make a just-generated
file appear to be from the future. `size` is the exact byte length of the
uploaded Parquet file — pass it as `byteLength` to hyparquet's
`asyncBufferFromUrl` so it can skip its own `HEAD`-request byte-length
probe entirely and go straight to ranged `GET`s. This isn't just an
optimization: a `HEAD` request against some S3-compatible backends (Garage
included, observed in production) can behave inconsistently in ways a
ranged `GET` doesn't, so skipping it is also a reliability fix, not only a
latency one. A consuming dashboard should fetch this
alongside the data file and display both, so viewers can tell which build
produced what they're looking at and how fresh it is.
