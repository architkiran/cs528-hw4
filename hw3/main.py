import functions_framework
import json
from google.cloud import storage

BUCKET_NAME = "bu-cs528-architkk"

FORBIDDEN_COUNTRIES = {
    "north korea", "iran", "cuba", "myanmar", "iraq",
    "libya", "sudan", "zimbabwe", "syria"
}

storage_client = storage.Client()

def publish_forbidden(country, filename, request_ip):
    from google.cloud import pubsub_v1
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        "utopian-planet-485618-b3", "forbidden-requests"
    )
    message = json.dumps({
        "country": country,
        "filename": filename,
        "ip": request_ip
    }).encode("utf-8")
    publisher.publish(topic_path, message)

@functions_framework.http
def serve_file(request):
    if request.method not in ("GET",):
        entry = {
            "severity": "WARNING",
            "message": f"501 Not Implemented: method={request.method} path={request.path}",
            "method": request.method,
            "path": request.path
        }
        print(json.dumps(entry))
        return ("Not Implemented", 501)

    country = request.headers.get("X-country", "").strip().lower()
    if country in FORBIDDEN_COUNTRIES:
        filename = request.path.lstrip("/")
        entry = {
            "severity": "ERROR",
            "message": f"400 Forbidden country: country={country} file={filename}",
            "country": country,
            "filename": filename
        }
        print(json.dumps(entry))
        try:
            publish_forbidden(country, filename, request.remote_addr)
        except Exception as e:
            print(json.dumps({"severity": "ERROR", "message": f"Pub/Sub publish failed: {e}"}))
        return ("Permission Denied: export-controlled content", 400)

    filename = request.path.lstrip("/")
    if not filename:
        return ("No file specified", 400)

    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        if not blob.exists():
            entry = {
                "severity": "WARNING",
                "message": f"404 Not Found: file={filename}",
                "filename": filename
            }
            print(json.dumps(entry))
            return (f"File not found: {filename}", 404)

        content = blob.download_as_text()
        return (content, 200, {"Content-Type": "text/html"})

    except Exception as e:
        entry = {
            "severity": "ERROR",
            "message": f"500 Internal Error: {str(e)}"
        }
        print(json.dumps(entry))
        return (f"Internal Server Error: {str(e)}", 500)
