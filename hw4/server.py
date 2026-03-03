#!/usr/bin/env python3
import http.server
import socketserver
import json
import logging
import os
import urllib.request

from google.cloud import storage
import google.cloud.logging

log_client = google.cloud.logging.Client()
log_client.setup_logging()
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "bu-cs528-architkk")
FORBIDDEN_SERVICE_URL = os.environ.get("FORBIDDEN_SERVICE_URL", "")
PORT = 8080

FORBIDDEN_COUNTRIES = {
    "north korea", "iran", "cuba", "myanmar",
    "iraq", "libya", "sudan", "zimbabwe", "syria"
}

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class GCSHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        filename = self.path.lstrip("/")
        if not filename:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"400 Bad Request: no file specified")
            return

        country = self.headers.get("X-country", "").strip().lower()
        if country in FORBIDDEN_COUNTRIES:
            logger.critical(
                f"403 Forbidden country: country={country} file={filename} ip={self.client_address[0]}"
            )
            if FORBIDDEN_SERVICE_URL:
                try:
                    payload = json.dumps({
                        "country": country,
                        "filename": filename,
                        "ip": self.client_address[0]
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        FORBIDDEN_SERVICE_URL,
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=3)
                except Exception as e:
                    logger.error(f"Failed to notify forbidden service: {e}")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"403 Forbidden: export-controlled content")
            return

        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(filename)
            if not blob.exists():
                logger.warning(
                    f"404 Not Found: file={filename} ip={self.client_address[0]}"
                )
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"File not found: {filename}".encode())
                return
            content = blob.download_as_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error(f"500 Internal Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"500 Internal Server Error")

    def do_PUT(self):     self._not_implemented()
    def do_POST(self):    self._not_implemented()
    def do_DELETE(self):  self._not_implemented()
    def do_HEAD(self):    self._not_implemented()
    def do_OPTIONS(self): self._not_implemented()
    def do_PATCH(self):   self._not_implemented()
    def do_CONNECT(self): self._not_implemented()
    def do_TRACE(self):   self._not_implemented()

    def _not_implemented(self):
        logger.warning(
            f"501 Not Implemented: method={self.command} path={self.path} ip={self.client_address[0]}"
        )
        self.send_response(501)
        self.end_headers()
        self.wfile.write(b"501 Not Implemented")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"Starting server on port {PORT}...", flush=True)
    with ThreadedTCPServer(("", PORT), GCSHandler) as httpd:
        print(f"Server running on port {PORT}", flush=True)
        httpd.serve_forever()
