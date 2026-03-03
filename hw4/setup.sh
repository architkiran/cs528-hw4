#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
ZONE="us-central1-a"
BUCKET_NAME="bu-cs528-architkk"

echo "========================================"
echo "HW4 Setup — Project: $PROJECT_ID"
echo "========================================"

# ---- Step 1: Enable APIs ----
echo "[1/8] Enabling required APIs..."
gcloud services enable compute.googleapis.com \
    storage.googleapis.com \
    logging.googleapis.com \
    --project=$PROJECT_ID

# ---- Step 2: Create service account for VM1 ----
echo "[2/8] Creating service account for VM1..."
gcloud iam service-accounts create hw4-webserver-sa \
    --display-name="HW4 Web Server SA" \
    --project=$PROJECT_ID 2>/dev/null || echo "Service account already exists, continuing..."

SA_EMAIL="hw4-webserver-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter" --quiet

echo "Service account: $SA_EMAIL"

# ---- Step 3: Reserve static IP for VM1 ----
echo "[3/8] Reserving static IP for web server..."
gcloud compute addresses create hw4-webserver-ip \
    --region=$REGION \
    --project=$PROJECT_ID 2>/dev/null || echo "Static IP already exists, continuing..."

STATIC_IP=$(gcloud compute addresses describe hw4-webserver-ip \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(address)")
echo "Static IP reserved: $STATIC_IP"

# ---- Step 4: Create VM3 (forbidden service) FIRST so we get its IP ----
echo "[4/8] Creating VM3 (forbidden country service)..."
gcloud compute instances create hw4-forbidden-vm \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --metadata-from-file startup-script=startup_forbidden.sh \
    --tags=forbidden-service \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --project=$PROJECT_ID 2>/dev/null || echo "VM3 already exists, continuing..."

echo "Waiting 30 seconds for VM3 to get an IP..."
sleep 30

FORBIDDEN_IP=$(gcloud compute instances describe hw4-forbidden-vm \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "VM3 IP: $FORBIDDEN_IP"

# ---- Step 5: Create VM1 (web server) ----
echo "[5/8] Creating VM1 (web server)..."
gcloud compute instances create hw4-webserver-vm \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --address=$STATIC_IP \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --metadata=bucket-name=${BUCKET_NAME} \
    --metadata=forbidden-service-url=http://${FORBIDDEN_IP}:8081/forbidden \
    --metadata-from-file startup-script=startup.sh \
    --tags=http-server \
    --project=$PROJECT_ID 2>/dev/null || echo "VM1 already exists, continuing..."

# ---- Step 6: Create VM2 (client) ----
echo "[6/8] Creating VM2 (client)..."
gcloud compute instances create hw4-client-vm \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --metadata-from-file startup-script=startup_client.sh \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --project=$PROJECT_ID 2>/dev/null || echo "VM2 already exists, continuing..."

# ---- Step 7: Create firewall rules ----
echo "[7/8] Creating firewall rules..."
gcloud compute firewall-rules create hw4-allow-http \
    --allow=tcp:8080 \
    --target-tags=http-server \
    --description="Allow web server port 8080" \
    --project=$PROJECT_ID 2>/dev/null || echo "Firewall rule already exists, continuing..."

gcloud compute firewall-rules create hw4-allow-forbidden \
    --allow=tcp:8081 \
    --target-tags=forbidden-service \
    --description="Allow forbidden service port 8081" \
    --project=$PROJECT_ID 2>/dev/null || echo "Firewall rule already exists, continuing..."

gcloud compute firewall-rules create hw4-allow-internal \
    --allow=tcp:8081 \
    --source-tags=http-server \
    --target-tags=forbidden-service \
    --description="Allow VM1 to reach VM3 internally" \
    --project=$PROJECT_ID 2>/dev/null || echo "Internal firewall rule already exists, continuing..."

# ---- Step 8: Copy client script to VM2 ----
echo "[8/8] Copying http_client.py to VM2..."
sleep 60
gcloud compute scp http_client.py hw4-client-vm:/home/$(gcloud config get-value account | cut -d@ -f1)/http_client.py \
    --zone=$ZONE \
    --project=$PROJECT_ID 2>/dev/null || echo "SCP failed — copy manually with: gcloud compute scp http_client.py hw4-client-vm:~/ --zone=$ZONE"

echo ""
echo "========================================"
echo "Setup complete!"
echo "Web server static IP: $STATIC_IP"
echo "VM3 (forbidden) IP:   $FORBIDDEN_IP"
echo ""
echo "Wait ~2 minutes for VMs to finish installing, then test:"
echo "  curl http://${STATIC_IP}:8080/0.html"
echo "========================================"
