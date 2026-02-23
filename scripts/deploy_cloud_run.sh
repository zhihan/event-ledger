#!/usr/bin/env bash
set -euo pipefail

PROJECT="living-memories-488001"
REGION="northamerica-northeast1"
SERVICE="event-ledger-api"

echo "Deploying ${SERVICE} to Cloud Run (${PROJECT} / ${REGION})..."

gcloud run deploy "${SERVICE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --source . \
  --set-env-vars "EVENT_LEDGER_USER_ID=cambridge-lexington,GOOGLE_CLOUD_PROJECT=${PROJECT},LIVING_MEMORY_FIRESTORE_DATABASE=(default)"

SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --format "value(status.url)")

echo ""
echo "Deployed successfully: ${SERVICE_URL}"
