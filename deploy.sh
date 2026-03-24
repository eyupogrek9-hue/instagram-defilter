#!/usr/bin/env bash
# deploy.sh — first-time deploy of instagram-defilter to Railway (backend) + Vercel (frontend)
#
# Prerequisites (one-time setup):
#   npm install -g @railway/cli vercel
#   railway login
#   vercel login
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... bash deploy.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "Usage: ANTHROPIC_API_KEY=your_key bash deploy.sh"
  exit 1
fi

echo "==> Deploying backend to Railway..."
cd "$REPO_ROOT/backend"

# Link to a new Railway project (creates it if not linked yet)
railway init --name "instagram-defilter" 2>/dev/null || true

# Set the Anthropic API key
railway variables set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"

# Deploy (Railway reads railway.toml for build/start config)
railway up --detach

# Get the backend URL
RAILWAY_URL=$(railway domain 2>/dev/null || echo "")
if [[ -z "$RAILWAY_URL" ]]; then
  echo "  Could not auto-detect Railway URL. Check your Railway dashboard."
  echo "  Set it manually: VITE_API_URL=https://your-app.up.railway.app"
  RAILWAY_URL="https://YOUR_RAILWAY_URL.up.railway.app"
fi
echo "  Backend URL: https://$RAILWAY_URL"

echo ""
echo "==> Deploying frontend to Vercel..."
cd "$REPO_ROOT/frontend"

# Install deps first (needed for build)
npm install --silent

# Deploy with env var pointing to Railway backend
VITE_API_URL="https://$RAILWAY_URL" vercel --prod \
  --build-env VITE_API_URL="https://$RAILWAY_URL" \
  --env VITE_API_URL="https://$RAILWAY_URL" \
  --yes

echo ""
echo "==> Done!"
echo "  Backend: https://$RAILWAY_URL"
echo "  Frontend: check Vercel output above for the URL"
