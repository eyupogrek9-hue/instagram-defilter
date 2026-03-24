#!/usr/bin/env bash
# deploy.sh — first-time deploy of instagram-defilter to Railway (backend) + Vercel (frontend)
#
# Prerequisites (one-time setup):
#   npm install -g @railway/cli vercel
#   railway login
#   vercel login
#
# Usage:
#   bash deploy.sh
#   (reads ANTHROPIC_API_KEY from ~/.deploy-secrets automatically)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$HOME/.deploy-secrets"

# Load secrets file if it exists
if [[ -f "$SECRETS_FILE" ]]; then
  set -a; source "$SECRETS_FILE"; set +a
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "Add it to $SECRETS_FILE: ANTHROPIC_API_KEY=your_key"
  exit 1
fi

echo "==> Deploying backend to Railway..."
cd "$REPO_ROOT/backend"

# Create and link project
railway init --name "instagram-defilter" 2>/dev/null || true

# Deploy (creates a new service automatically)
railway up --detach

# Link the newly created service so we can set variables
SERVICE_ID=$(railway status --json 2>/dev/null | grep -o '"serviceId":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
if [[ -n "$SERVICE_ID" ]]; then
  railway service link "$SERVICE_ID" 2>/dev/null || true
fi

# Set the Anthropic API key
railway variables set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"

# Generate a public domain
RAILWAY_URL=$(railway domain 2>/dev/null | grep -o 'https://[^ ]*' | head -1 || echo "")
if [[ -z "$RAILWAY_URL" ]]; then
  echo "  Could not auto-detect Railway URL. Check your Railway dashboard."
  RAILWAY_URL="https://YOUR_RAILWAY_URL.up.railway.app"
fi
echo "  Backend URL: $RAILWAY_URL"

echo ""
echo "==> Deploying frontend to Vercel..."
cd "$REPO_ROOT/frontend"

npm install --silent

vercel --prod \
  --build-env VITE_API_URL="$RAILWAY_URL" \
  --env VITE_API_URL="$RAILWAY_URL" \
  --yes

echo ""
echo "==> Done!"
echo "  Backend:  $RAILWAY_URL"
echo "  Frontend: check Vercel output above for the URL"
