import logging
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, exporter, reports

log = logging.getLogger(__name__)

_ready = threading.Event()


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200 if _ready.is_set() else 503)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def _serve_health(port: int):
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("health server listening on :%d/health", port)


def _run_cycle(cfg: config.Config):
    rows = reports.fetch_all_rows(cfg.source)
    data = exporter.rows_to_parquet_bytes(rows)
    exporter.upload(cfg.dest, cfg.dest_key, data)
    exporter.upload_meta(cfg.dest, cfg.dest_meta_key, cfg.version, len(data))


def main():
    try:
        cfg = config.load()
    except config.ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    _serve_health(cfg.health_port)

    while not stop.is_set():
        try:
            _run_cycle(cfg)
            _ready.set()
        except Exception:
            log.exception("cycle failed, will retry next interval")
        stop.wait(cfg.poll_interval_seconds)


if __name__ == "__main__":
    main()
