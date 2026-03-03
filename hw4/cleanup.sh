#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
ZONE="us-central1-a"
REGION="us-central1"

echo "========================================"
echo "HW4 Cleanup — Project: $PROJECT_ID"
echo "========================================"

echo "Deleting VMs..."
gcloud compute instances delete hw4-webserver-vm --zone=$ZONE --quiet --project=$PROJECT_ID 2>/dev/null || true
gcloud compute instances delete hw4-client-vm --zone=$ZONE --quiet --project=$PROJECT_ID 2>/dev/null || true
gcloud compute instances delete hw4-forbidden-vm --zone=$ZONE --quiet --project=$PROJECT_ID 2>/dev/null || true

echo "Releasing static IP..."
gcloud compute addresses delete hw4-webserver-ip --region=$REGION --quiet --project=$PROJECT_ID 2>/dev/null || true

echo "Deleting firewall rules..."
gcloud compute firewall-rules delete hw4-allow-http --quiet --project=$PROJECT_ID 2>/dev/null || true
gcloud compute firewall-rules delete hw4-allow-forbidden --quiet --project=$PROJECT_ID 2>/dev/null || true
gcloud compute firewall-rules delete hw4-allow-internal --quiet --project=$PROJECT_ID 2>/dev/null || true

echo "Removing IAM bindings..."
SA_EMAIL="hw4-webserver-sa@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" --quiet 2>/dev/null || true
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter" --quiet 2>/dev/null || true

echo "Deleting service account..."
gcloud iam service-accounts delete $SA_EMAIL --quiet --project=$PROJECT_ID 2>/dev/null || true

echo ""
echo "========================================"
echo "Cleanup complete!"
echo "========================================"
