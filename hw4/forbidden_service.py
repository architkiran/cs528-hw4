#!/usr/bin/env python3
import http.server
import json

PORT = 8081

class ForbiddenHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            print(
                f"[FORBIDDEN REQUEST] Country={data.get('country', 'unknown').upper()} | "
                f"File={data.get('filename', 'unknown')} | "
                f"IP={data.get('ip', 'unknown')}",
                flush=True
            )
        except Exception as e:
            print(f"[ERROR] Could not parse forbidden request: {e}", flush=True)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"Forbidden country service listening on port 8081...", flush=True)
    server = http.server.HTTPServer(("", 8081), ForbiddenHandler)
    server.serve_forever()
