from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    model_loaded: bool


class MouseEvent(BaseModel):
    x: float
    y: float
    t: float = Field(ge=0)


class KeyboardEvent(BaseModel):
    key: str
    down: float = Field(ge=0)
    up: float = Field(ge=0)


class DeviceInfo(BaseModel):
    userAgent: str = ""
    screen: Tuple[int, int]
    timezone: str = ""
    webdriver: Optional[bool] = None
    pluginsCount: Optional[int] = None
    languagesCount: Optional[int] = None
    hardwareConcurrency: Optional[int] = None
    deviceMemory: Optional[float] = None
    maxTouchPoints: Optional[int] = None
    refreshRate: Optional[float] = None
    webglVendor: str = ""
    webglRenderer: str = ""
    platform: str = ""


class PredictionRequest(BaseModel):
    mouse: List[MouseEvent] = Field(default_factory=list)
    keyboard: List[KeyboardEvent] = Field(default_factory=list)
    device: DeviceInfo
    honeypotFilled: bool = False
    timeToFirstInput: Optional[float] = Field(default=None, ge=0)
    timeToSubmit: Optional[float] = Field(default=None, ge=0)
    pasteCount: int = Field(default=0, ge=0)


class ExtractedFeatures(BaseModel):
    mouse_event_count: int
    mouse_duration: float
    avg_speed: float
    speed_std: float
    max_speed: float
    avg_acceleration: float
    acceleration_std: float
    path_length: float
    straightness_ratio: float
    direction_changes: int
    idle_time_ratio: float
    movement_entropy: float
    key_event_count: int
    typing_duration: float
    dwell_mean: float
    dwell_std: float
    flight_mean: float
    flight_std: float
    typing_speed: float
    typing_variance: float
    backspace_ratio: float
    pause_ratio: float
    total_session_time: float
    event_density: float
    mouse_keyboard_ratio: float
    headless_flag: int
    webdriver_flag: int
    suspicious_user_agent: int
    invalid_screen_flag: int
    timezone_missing: int
    mouse_timing_entropy: float
    typing_timing_entropy: float
    rhythm_consistency: float
    hesitation_frequency: float
    micro_corrections: int
    impossible_speed_flag: int
    screen_anomaly_flag: int
    plugin_anomaly_flag: int
    languages_missing_flag: int
    hardware_anomaly_flag: int
    memory_anomaly_flag: int
    refresh_rate_anomaly_flag: int
    touch_platform_mismatch_flag: int
    webgl_software_flag: int
    honeypot_triggered: int
    time_to_first_input: float
    time_to_submit: float
    paste_count: int


class PredictionResponse(BaseModel):
    is_human: bool
    risk_score: float
    message: str
    model_scores: Dict[str, float]
    rule_score: float
    reasons: List[str]
