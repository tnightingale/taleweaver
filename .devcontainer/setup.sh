#!/bin/bash
set -e

echo "==> Installing system dependencies (ffmpeg)..."
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg

echo "==> Setting up Python virtual environment..."
cd /workspaces/taleweaver/backend
python -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "==> Creating backend .env from example (if not present)..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "   -> Created backend/.env — add your API keys to it (or set Codespaces secrets)."
fi

echo "==> Installing frontend dependencies..."
cd /workspaces/taleweaver/frontend
npm install --silent

echo ""
echo "==> Setup complete! To start the app:"
echo "    Terminal 1 (backend):  cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "    Terminal 2 (frontend): cd frontend && npm run dev"
