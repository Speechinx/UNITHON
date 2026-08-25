#!/usr/bin/env bash
# Build and deploy the backend to Google Cloud Run.
#
# Prereqs (one-time):
#   1. gcloud CLI installed and logged in: gcloud auth login
#   2. A GCP project with billing enabled (Always Free tier still applies
#      without extra cost as long as usage stays under the free quota):
#        gcloud config set project YOUR_PROJECT_ID
#   3. Enable the required APIs:
#        gcloud services enable run.googleapis.com cloudbuild.googleapis.com
#   4. Put your real Gemini key in backend/.env as GEMINI_API_KEY=... (this
#      file is already gitignored and is only read locally by this script,
#      never baked into the image or committed).
#
# Usage:
#   cd backend
#   ./deploy-cloudrun.sh

set -euo pipefail

# --- edit these two ---
PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
REGION="asia-northeast3"   # Seoul; pick whatever region is closest to you
# ----------------------

SERVICE_NAME="pr-coach-backend"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [ -z "${PROJECT_ID}" ]; then
  echo "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "backend/.env not found — copy .env.example to .env and fill in GEMINI_API_KEY first." >&2
  exit 1
fi

GEMINI_API_KEY="$(grep -E '^GEMINI_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"')"

if [ -z "${GEMINI_API_KEY}" ]; then
  echo "GEMINI_API_KEY is empty in backend/.env." >&2
  exit 1
fi

echo "== Building image via Cloud Build (no local Docker needed) =="
gcloud builds submit --tag "${IMAGE}" .

echo "== Deploying to Cloud Run =="
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 8Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 3 \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"

echo "== Done =="
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format="value(status.url)"
