from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import HTTPException
from sklearn.exceptions import InconsistentVersionWarning
from xgboost.core import XGBoostError

from app.schemas import ExtractedFeatures

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "ensemble_bundle.joblib"


class ModelService:
    def __init__(self) -> None:
        self.bundle: dict[str, Any] | None = None
        self.load_error: str | None = None
        self.feature_names: list[str] = []

    @property
    def loaded(self) -> bool:
        return self.bundle is not None

    def load(self) -> None:
        if not MODEL_PATH.exists():
            self.load_error = f"Model bundle not found at {MODEL_PATH}"
            self.bundle = None
            return

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InconsistentVersionWarning)
                warnings.filterwarnings(
                    "ignore",
                    message=".*serialized model.*",
                    category=UserWarning,
                    module="xgboost.core",
                )
                self.bundle = joblib.load(MODEL_PATH)
            self.feature_names = list(self.bundle["feature_names"])
            self.load_error = None
        except (FileNotFoundError, KeyError, ModuleNotFoundError, XGBoostError, Exception) as exc:
            self.bundle = None
            self.feature_names = []
            self.load_error = str(exc)

    def _feature_frame(self, features: ExtractedFeatures) -> pd.DataFrame:
        if not self.bundle or not self.feature_names:
            raise HTTPException(status_code=503, detail="ML model bundle is not loaded")

        feature_dict = features.model_dump()
        frame = pd.DataFrame([feature_dict])
        missing = set(self.feature_names) - set(frame.columns)
        if missing:
            raise ValueError(f"Missing features: {sorted(missing)}")
        return frame[self.feature_names]

    def predict_proba(self, features: ExtractedFeatures) -> dict[str, Any]:
        if not self.bundle:
            raise HTTPException(status_code=503, detail=f"ML model unavailable: {self.load_error}")

        frame = self._feature_frame(features)
        models = self.bundle["models"]
        weights = self.bundle["weights"]

        rf_prob = float(models["rf"].predict_proba(frame)[0][1])
        lr_prob = float(models["lr"].predict_proba(frame)[0][1])
        xgb_prob = float(models["xgb"].predict_proba(frame)[0][1])

        final_score = (
            weights["rf"] * rf_prob
            + weights["lr"] * lr_prob
            + weights["xgb"] * xgb_prob
        )

        return {
            "ensemble_score": final_score,
            "model_scores": {
                "rf": rf_prob,
                "lr": lr_prob,
                "xgb": xgb_prob,
            },
        }


model_service = ModelService()
