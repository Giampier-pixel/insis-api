"""
Cloud Run Celery worker entry point.
Starts the HTTP health server immediately (daemon thread),
then runs the Celery worker in the main thread.
Container exits if Celery crashes, triggering Cloud Run restart.
"""
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def _start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[worker] Health server on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=_start_health_server, daemon=True).start()

    from celery.__main__ import main as celery_main

    sys.argv = [
        "celery",
        "-A", "config.celery",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
    ]
    celery_main()
