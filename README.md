# SURAKSHA

SURAKSHA is a behavioral bot-detection and passive authentication demo. The frontend collects browser, mouse, keyboard, and device telemetry, sends it to a FastAPI backend, and renders a human/suspicious/bot risk decision from a hybrid ML + rule engine.

## Live Setup

- Frontend: `https://getsuraksha.in`
- Hosting: Vercel
- DNS: GoDaddy
- Backend: FastAPI, currently exposed through a public backend URL during demo/development

## Project Structure

```txt
frontend/
  index.html
  script.js
  style.css
  services/api.js
  utils/buildPayload.js

backend/
  app/
  data/
  models/
  samples/
  scripts/
```

## Frontend

The frontend is a Vite app. It collects:

- mouse movement
- keyboard dwell/flight timing
- paste count
- time to first input
- time to submit
- browser/device signals such as webdriver, plugins, languages, hardware concurrency, device memory, touch points, refresh rate, platform, and WebGL renderer

Run locally:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Required environment variable:

```txt
VITE_API_URL=https://your-backend-url
```

For Vercel, set `VITE_API_URL` for Production and Preview environments.

## Backend

The backend is a FastAPI service with:

- `GET /health`
- `POST /predict`
- feature extraction
- rule-based scoring
- Random Forest, Logistic Regression, and XGBoost ensemble model loading
- hybrid score calculation

Run locally:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Contract

Request:

```json
{
  "mouse": [{ "x": 120, "y": 300, "t": 0 }],
  "keyboard": [{ "key": "a", "down": 100, "up": 180 }],
  "device": {
    "userAgent": "Mozilla/5.0 ...",
    "screen": [1920, 1080],
    "timezone": "Asia/Kolkata"
  }
}
```

Response:

```json
{
  "is_human": true,
  "risk_score": 0.951,
  "message": "Low Risk - Access Granted",
  "model_scores": {
    "rf": 0.823,
    "lr": 1.0,
    "xgb": 0.974
  },
  "rule_score": 1.0,
  "reasons": [
    "No headless browser indicator detected",
    "User agent looks normal",
    "Natural mouse variance observed"
  ]
}
```

## Notes

- Large backend datasets and the trained model bundle are stored with Git LFS.
- This is a demo/prototype, not production-grade authentication security.
- The current model needs larger real-world datasets before it should be treated as reliable in adversarial environments.
