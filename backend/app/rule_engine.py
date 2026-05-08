from __future__ import annotations

from app.schemas import ExtractedFeatures


def compute_rule_score(features: ExtractedFeatures) -> tuple[float, list[str]]:
    score = 1.0
    reasons: list[str] = []

    if features.headless_flag:
        score -= 0.35
        reasons.append("Headless browser indicator detected")
    else:
        reasons.append("No headless browser indicator detected")

    if features.webdriver_flag:
        score -= 0.3
        reasons.append("Webdriver or automation marker detected")

    if features.honeypot_triggered:
        score -= 0.45
        reasons.append("Hidden honeypot field was filled")

    if features.suspicious_user_agent:
        score -= 0.15
        reasons.append("Suspicious user agent pattern detected")
    else:
        reasons.append("User agent looks normal")

    if features.invalid_screen_flag:
        score -= 0.15
        reasons.append("Invalid screen dimensions detected")

    if features.screen_anomaly_flag:
        score -= 0.12
        reasons.append("Screen resolution or aspect ratio looks unusual")

    if features.refresh_rate_anomaly_flag:
        score -= 0.08
        reasons.append("Refresh rate looks unrealistic")

    if features.plugin_anomaly_flag:
        score -= 0.1
        reasons.append("Browser reports zero plugins")

    if features.languages_missing_flag:
        score -= 0.08
        reasons.append("Browser languages are missing")

    if features.hardware_anomaly_flag:
        score -= 0.08
        reasons.append("Hardware concurrency looks suspicious")

    if features.memory_anomaly_flag:
        score -= 0.05
        reasons.append("Device memory value looks suspicious")

    if features.touch_platform_mismatch_flag:
        score -= 0.08
        reasons.append("Touch capability does not match platform hints")

    if features.webgl_software_flag:
        score -= 0.12
        reasons.append("WebGL renderer suggests software or virtualized rendering")

    if features.avg_speed == 0 and features.mouse_event_count > 0:
        score -= 0.2
        reasons.append("Mouse movement has zero effective speed")

    if features.speed_std < 0.01 and features.mouse_event_count >= 10:
        score -= 0.12
        reasons.append("Mouse speed variance is unusually low")
    else:
        reasons.append("Natural mouse variance observed")

    if features.impossible_speed_flag:
        score -= 0.25
        reasons.append("Inhuman mouse speed detected")

    if features.direction_changes < 2 and features.mouse_event_count >= 20:
        score -= 0.1
        reasons.append("Movement path has very few direction changes")

    if features.straightness_ratio > 0.97 and features.path_length > 120:
        score -= 0.1
        reasons.append("Movement path is unusually straight")

    if features.micro_corrections <= 1 and features.mouse_event_count >= 40:
        score -= 0.06
        reasons.append("Movement lacks human-like micro-corrections")

    if features.mouse_timing_entropy < 0.18 and features.mouse_event_count >= 25:
        score -= 0.08
        reasons.append("Mouse timing rhythm is too regular")

    if features.typing_variance < 50 and features.key_event_count >= 6:
        score -= 0.15
        reasons.append("Typing timing is overly consistent")

    if features.rhythm_consistency > 0.92 and features.key_event_count >= 6:
        score -= 0.08
        reasons.append("Typing rhythm is suspiciously consistent")

    if features.typing_timing_entropy < 0.18 and features.key_event_count >= 6:
        score -= 0.08
        reasons.append("Typing timing entropy is unusually low")

    if features.paste_count > 0:
        reasons.append("Paste activity detected in session")

    if 0 < features.time_to_first_input < 120:
        score -= 0.08
        reasons.append("Input started unusually quickly")

    if 0 < features.time_to_submit < 900:
        score -= 0.1
        reasons.append("Submission completed unusually quickly")

    if features.backspace_ratio > 0.18:
        reasons.append("Human-like correction behavior observed")

    if features.pause_ratio > 0.12 or features.idle_time_ratio > 0.08 or features.hesitation_frequency > 0.12:
        reasons.append("Natural pauses present in the session")

    if features.mouse_event_count == 0 and features.key_event_count > 0:
        reasons.append("Keyboard-only session preserved as valid human edge case")
    if features.key_event_count == 0 and features.mouse_event_count > 0:
        reasons.append("Mouse-only session preserved as valid human edge case")

    return max(0.0, min(1.0, score)), reasons
