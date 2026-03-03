import os
import json
import datetime
from google.cloud import pubsub_v1, storage
from google.oauth2 import service_account

KEY_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", os.path.expanduser("~/hw3-key.json"))
PROJECT_ID = "utopian-planet-485618-b3"
SUBSCRIPTION_ID = "forbidden-requests-sub"
BUCKET_NAME = "bu-cs528-architkk"
LOG_BLOB = "forbidden-logs/forbidden.log"

credentials = service_account.Credentials.from_service_account_file(KEY_FILE)
storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

def callback(message):
    data = json.loads(message.data.decode("utf-8"))
    country = data.get("country", "unknown")
    filename = data.get("filename", "unknown")
    ip = data.get("ip", "unknown")
    timestamp = datetime.datetime.utcnow().isoformat()

    log_line = f"[{timestamp}] FORBIDDEN REQUEST: country={country}, file={filename}, ip={ip}\n"
    print(log_line, flush=True)

    # Append to forbidden-logs/forbidden.log in GCS
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(LOG_BLOB)
    existing = ""
    try:
        existing = blob.download_as_text()
    except Exception:
        pass
    blob.upload_from_string(existing + log_line, content_type="text/plain")
    message.ack()

print("Service 2 is running. Listening for forbidden country requests...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

try:
    streaming_pull_future.result()
except KeyboardInterrupt:
    streaming_pull_future.cancel()
    print("Subscriber stopped.")
