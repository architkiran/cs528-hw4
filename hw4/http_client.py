#!/usr/bin/env python3
import urllib.request
import sys
import random
import time

if len(sys.argv) < 2:
    print("Usage: python3 http_client.py <server_ip> [num_requests]")
    sys.exit(1)

SERVER_IP = sys.argv[1]
NUM_REQUESTS = int(sys.argv[2]) if len(sys.argv) > 2 else 100
BASE_URL = f"http://{SERVER_IP}:8080"

success = 0
errors = 0

for i in range(NUM_REQUESTS):
    file_index = random.randint(0, 19999)
    filename = f"{file_index}.html"
    url = f"{BASE_URL}/{filename}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            resp.read()
            print(f"[{status}] {filename}")
            if status == 200:
                success += 1
            else:
                errors += 1
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {filename}")
        errors += 1
    except Exception as e:
        print(f"[ERROR] {filename}: {e}")
        errors += 1

print(f"\nDone: {success} success, {errors} errors out of {NUM_REQUESTS} requests")
