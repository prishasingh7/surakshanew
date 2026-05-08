from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.feature_extractor import extract_features
from app.model_service import model_service
from app.rule_engine import compute_rule_score
from app.schemas import HealthResponse, PredictionRequest, PredictionResponse

app = FastAPI(
    title="SURAKSHA Backend API",
    description="Backend service for behavioral and contextual authentication.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="suraksha-backend",
        model_loaded=model_service.loaded,
    )


@app.on_event("startup")
def load_model_bundle() -> None:
    model_service.load()


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    features = extract_features(
        payload.mouse,
        payload.keyboard,
        payload.device,
        honeypot_filled=payload.honeypotFilled,
        time_to_first_input=payload.timeToFirstInput,
        time_to_submit=payload.timeToSubmit,
        paste_count=payload.pasteCount,
    )
    ml_result = model_service.predict_proba(features)
    rule_score, reasons = compute_rule_score(features)
    risk_score = _calculate_final_score(ml_result["ensemble_score"], rule_score)

    if risk_score > 0.7:
        message = "Low Risk - Access Granted"
    elif risk_score >= 0.4:
        message = "Medium Risk - Suspicious Behavior"
    else:
        message = "High Risk - Bot Detected"

    return PredictionResponse(
        is_human=risk_score > 0.7,
        risk_score=round(risk_score, 3),
        message=message,
        model_scores={name: round(score, 3) for name, score in ml_result["model_scores"].items()},
        rule_score=round(rule_score, 3),
        reasons=reasons[:6],
    )


def _calculate_final_score(ensemble_score: float, rule_score: float) -> float:
    final_score = 0.6 * ensemble_score + 0.4 * rule_score
    return max(0.0, min(1.0, final_score))
