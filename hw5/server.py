#!/usr/bin/env python3
import http.server
import socketserver
import json
import logging
import os
import time
import urllib.request
from datetime import datetime

import mysql.connector
from mysql.connector import pooling
from google.cloud import storage
import google.cloud.logging

log_client = google.cloud.logging.Client(project="utopian-planet-485618-b3")
log_client.setup_logging()
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "bu-cs528-architkk")
FORBIDDEN_SERVICE_URL = os.environ.get("FORBIDDEN_SERVICE_URL", "")
DB_HOST = os.environ.get("DB_HOST", "")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "hw5password123")
DB_NAME = os.environ.get("DB_NAME", "hw5")
PORT = 8080

FORBIDDEN_COUNTRIES = {
    "north korea", "iran", "cuba", "myanmar",
    "iraq", "libya", "sudan", "zimbabwe", "syria"
}

# Global reusable clients
storage_client = storage.Client(project="utopian-planet-485618-b3")
bucket = storage_client.bucket(BUCKET_NAME)

db_pool = pooling.MySQLConnectionPool(
    pool_name="hw5pool",
    pool_size=10,
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME
)

def get_db_connection():
    return db_pool.get_connection()

def extract_headers(handler):
    t0 = time.perf_counter()
    data = {
        "country":   handler.headers.get("X-country", "").strip().lower(),
        "client_ip": handler.client_address[0],
        "gender":    handler.headers.get("X-gender", "").strip(),
        "age":       handler.headers.get("X-age", "").strip(),
        "income":    handler.headers.get("X-income", "").strip(),
        "is_banned": handler.headers.get("X-is-banned", "false").strip().lower() == "true",
        "filename":  handler.path.lstrip("/"),
    }
    elapsed = time.perf_counter() - t0
    logger.info(f"[TIMING] extract_headers: {elapsed:.6f}s")
    return data

def read_from_gcs(filename):
    t0 = time.perf_counter()
    blob = bucket.blob(filename)
    exists = blob.exists()
    content = blob.download_as_bytes() if exists else None
    elapsed = time.perf_counter() - t0
    logger.info(f"[TIMING] read_from_gcs: {elapsed:.6f}s")
    return content

def send_response_to_client(handler, code, content=None, content_type="text/html"):
    t0 = time.perf_counter()
    handler.send_response(code)
    if content:
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    if content:
        handler.wfile.write(content)
    elapsed = time.perf_counter() - t0
    logger.info(f"[TIMING] send_response: {elapsed:.6f}s")

def insert_request(data):
    t0 = time.perf_counter()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        age = int(data["age"]) if data["age"].isdigit() else None
        cursor.execute("""
            INSERT INTO requests
                (country, client_ip, gender, age, income, is_banned, time_of_day, requested_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["country"], data["client_ip"], data["gender"],
            age, data["income"], data["is_banned"],
            datetime.now(), data["filename"]
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB insert_request error: {e}")
    elapsed = time.perf_counter() - t0
    logger.info(f"[TIMING] insert_request (DB): {elapsed:.6f}s")

def insert_error(filename, error_code):
    t0 = time.perf_counter()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO errors (time_of_day, requested_file, error_code)
            VALUES (%s, %s, %s)
        """, (datetime.now(), filename, error_code))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB insert_error error: {e}")
    elapsed = time.perf_counter() - t0
    logger.info(f"[TIMING] insert_error (DB): {elapsed:.6f}s")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class GCSHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        data = extract_headers(self)
        filename = data["filename"]

        if not filename:
            send_response_to_client(self, 400, b"400 Bad Request: no file specified")
            insert_error("", 400)
            return

        if data["country"] in FORBIDDEN_COUNTRIES:
            logger.critical(f"403 Forbidden: country={data['country']} file={filename}")
            if FORBIDDEN_SERVICE_URL:
                try:
                    payload = json.dumps({
                        "country": data["country"],
                        "filename": filename,
                        "ip": data["client_ip"]
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
            send_response_to_client(self, 403, b"403 Forbidden: export-controlled content")
            insert_error(filename, 403)
            return

        try:
            content = read_from_gcs(filename)
            if content is None:
                send_response_to_client(self, 404, f"File not found: {filename}".encode())
                insert_error(filename, 404)
                return
            send_response_to_client(self, 200, content)
            insert_request(data)
        except Exception as e:
            logger.error(f"500 Internal Error: {e}")
            send_response_to_client(self, 500, b"500 Internal Server Error")
            insert_error(filename, 500)

    def do_PUT(self):     self._not_implemented()
    def do_POST(self):    self._not_implemented()
    def do_DELETE(self):  self._not_implemented()
    def do_HEAD(self):    self._not_implemented()
    def do_OPTIONS(self): self._not_implemented()
    def do_PATCH(self):   self._not_implemented()
    def do_CONNECT(self): self._not_implemented()
    def do_TRACE(self):   self._not_implemented()

    def _not_implemented(self):
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
