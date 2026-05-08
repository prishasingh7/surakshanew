from __future__ import annotations

import math
from collections import Counter
from statistics import mean, pstdev

from app.schemas import DeviceInfo, ExtractedFeatures, KeyboardEvent, MouseEvent


def _standard_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values)


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    value_mean = mean(values)
    return mean([(value - value_mean) ** 2 for value in values])


def _normalized_entropy(values: list[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    return entropy / max_entropy if max_entropy else 0.0


def _mouse_metrics(mouse_events: list[MouseEvent]) -> dict[str, float | int]:
    events = sorted(mouse_events, key=lambda event: event.t)
    mouse_event_count = len(events)
    if mouse_event_count < 2:
        return {
            "mouse_event_count": mouse_event_count,
            "mouse_duration": 0.0,
            "avg_speed": 0.0,
            "speed_std": 0.0,
            "max_speed": 0.0,
            "avg_acceleration": 0.0,
            "acceleration_std": 0.0,
            "path_length": 0.0,
            "straightness_ratio": 0.0,
            "direction_changes": 0,
            "idle_time_ratio": 0.0,
            "movement_entropy": 0.0,
            "mouse_timing_entropy": 0.0,
            "hesitation_frequency": 0.0,
            "micro_corrections": 0,
            "impossible_speed_flag": 0,
        }

    speeds: list[float] = []
    accelerations: list[float] = []
    angles: list[float] = []
    dt_values: list[float] = []
    path_length = 0.0
    idle_time = 0.0
    impossible_speed_flag = 0

    for previous, current in zip(events, events[1:]):
        dx = current.x - previous.x
        dy = current.y - previous.y
        dt = current.t - previous.t
        if dt <= 0:
            continue

        distance = math.hypot(dx, dy)
        speed = distance / dt
        speeds.append(speed)
        dt_values.append(dt)
        path_length += distance
        if speed > 8.0:
            impossible_speed_flag = 1

        if dt > 500:
            idle_time += dt
        if distance > 0:
            angles.append(math.atan2(dy, dx))

    for previous_speed, current_speed, dt in zip(speeds, speeds[1:], dt_values[1:]):
        accelerations.append((current_speed - previous_speed) / dt if dt > 0 else 0.0)

    direction_changes = 0
    micro_corrections = 0
    for previous_angle, current_angle in zip(angles, angles[1:]):
        diff = abs(current_angle - previous_angle)
        normalized_diff = min(diff, 2 * math.pi - diff)
        if normalized_diff > math.pi / 6:
            direction_changes += 1
        if math.pi / 18 < normalized_diff < math.pi / 5:
            micro_corrections += 1

    mouse_duration = max(0.0, events[-1].t - events[0].t)
    straight_distance = math.hypot(events[-1].x - events[0].x, events[-1].y - events[0].y)
    straightness_ratio = straight_distance / path_length if path_length > 0 else 0.0

    angle_buckets = [
        int(((angle + math.pi) / (2 * math.pi)) * 8) % 8
        for angle in angles
    ]
    movement_entropy = _normalized_entropy(angle_buckets)
    dt_buckets = [min(9, int(dt // 100)) for dt in dt_values]
    mouse_timing_entropy = _normalized_entropy(dt_buckets)
    hesitation_frequency = (
        sum(1 for dt in dt_values if dt > 250) / len(dt_values)
        if dt_values
        else 0.0
    )

    return {
        "mouse_event_count": mouse_event_count,
        "mouse_duration": mouse_duration,
        "avg_speed": mean(speeds) if speeds else 0.0,
        "speed_std": _standard_deviation(speeds),
        "max_speed": max(speeds) if speeds else 0.0,
        "avg_acceleration": mean(accelerations) if accelerations else 0.0,
        "acceleration_std": _standard_deviation(accelerations),
        "path_length": path_length,
        "straightness_ratio": straightness_ratio,
        "direction_changes": direction_changes,
        "idle_time_ratio": idle_time / mouse_duration if mouse_duration > 0 else 0.0,
        "movement_entropy": movement_entropy,
        "mouse_timing_entropy": mouse_timing_entropy,
        "hesitation_frequency": hesitation_frequency,
        "micro_corrections": micro_corrections,
        "impossible_speed_flag": impossible_speed_flag,
    }


def _keyboard_metrics(keyboard_events: list[KeyboardEvent]) -> dict[str, float | int]:
    events = sorted(keyboard_events, key=lambda event: event.down)
    key_event_count = len(events)
    if key_event_count == 0:
        return {
            "key_event_count": 0,
            "typing_duration": 0.0,
            "dwell_mean": 0.0,
            "dwell_std": 0.0,
            "flight_mean": 0.0,
            "flight_std": 0.0,
            "typing_speed": 0.0,
            "typing_variance": 0.0,
            "backspace_ratio": 0.0,
            "pause_ratio": 0.0,
            "typing_timing_entropy": 0.0,
            "rhythm_consistency": 0.0,
        }

    dwell_times = [max(0.0, event.up - event.down) for event in events]
    flight_times = [
        max(0.0, current.down - previous.up)
        for previous, current in zip(events, events[1:])
    ]

    typing_duration = max(0.0, events[-1].up - events[0].down)
    typing_speed = key_event_count / typing_duration if typing_duration > 0 else 0.0
    backspace_count = sum(1 for event in events if event.key.lower() == "backspace")
    pause_count = sum(1 for value in flight_times if value > 600)
    timing_values = dwell_times + flight_times
    timing_buckets = [min(11, int(value // 75)) for value in timing_values]
    rhythm_consistency = 0.0
    if timing_values:
        timing_mean = mean(timing_values)
        if timing_mean > 0:
            rhythm_consistency = 1.0 / (1.0 + (_standard_deviation(timing_values) / timing_mean))

    return {
        "key_event_count": key_event_count,
        "typing_duration": typing_duration,
        "dwell_mean": mean(dwell_times),
        "dwell_std": _standard_deviation(dwell_times),
        "flight_mean": mean(flight_times) if flight_times else 0.0,
        "flight_std": _standard_deviation(flight_times),
        "typing_speed": typing_speed,
        "typing_variance": _variance(dwell_times + flight_times),
        "backspace_ratio": backspace_count / key_event_count if key_event_count > 0 else 0.0,
        "pause_ratio": pause_count / len(flight_times) if flight_times else 0.0,
        "typing_timing_entropy": _normalized_entropy(timing_buckets),
        "rhythm_consistency": rhythm_consistency,
    }


def _device_metrics(device: DeviceInfo) -> dict[str, int]:
    user_agent = device.userAgent.lower()
    screen_width, screen_height = device.screen
    pixel_count = screen_width * screen_height
    aspect_ratio = screen_width / screen_height if screen_height else 0.0
    weird_aspect = aspect_ratio < 1.2 or aspect_ratio > 2.5
    weird_pixels = pixel_count < 200000 or pixel_count > 9000000
    plugins_count = device.pluginsCount if device.pluginsCount is not None else -1
    languages_count = device.languagesCount if device.languagesCount is not None else -1
    hardware_concurrency = (
        device.hardwareConcurrency if device.hardwareConcurrency is not None else -1
    )
    device_memory = device.deviceMemory if device.deviceMemory is not None else -1.0
    refresh_rate = device.refreshRate if device.refreshRate is not None else -1.0
    renderer = device.webglRenderer.lower()
    vendor = device.webglVendor.lower()
    platform = device.platform.lower()
    touch_points = device.maxTouchPoints if device.maxTouchPoints is not None else -1

    return {
        "headless_flag": int("headless" in user_agent),
        "webdriver_flag": int(
            bool(device.webdriver)
            or "webdriver" in user_agent
            or "selenium" in user_agent
            or "playwright" in user_agent
        ),
        "suspicious_user_agent": int(
            not device.userAgent.strip()
            or "headless" in user_agent
            or "phantomjs" in user_agent
            or "puppeteer" in user_agent
        ),
        "invalid_screen_flag": int(screen_width < 320 or screen_height < 240),
        "timezone_missing": int(not device.timezone.strip()),
        "screen_anomaly_flag": int(weird_aspect or weird_pixels),
        "plugin_anomaly_flag": int(plugins_count == 0),
        "languages_missing_flag": int(languages_count == 0),
        "hardware_anomaly_flag": int(
            hardware_concurrency in {0, 1} or hardware_concurrency > 64
        ),
        "memory_anomaly_flag": int(
            (device_memory > 0 and device_memory < 0.5) or device_memory > 128
        ),
        "refresh_rate_anomaly_flag": int(
            (refresh_rate > 0 and refresh_rate < 20)
            or refresh_rate > 360
        ),
        "touch_platform_mismatch_flag": int(
            (("iphone" in user_agent or "android" in user_agent) and touch_points == 0)
            or (
                touch_points >= 0
                and ("windows" in platform or "mac" in platform)
                and touch_points > 10
            )
        ),
        "webgl_software_flag": int(
            "swiftshader" in renderer
            or "software" in renderer
            or "llvmpipe" in renderer
            or "google inc." in vendor and "swiftshader" in renderer
        ),
    }


def extract_features(
    mouse_events: list[MouseEvent],
    keyboard_events: list[KeyboardEvent],
    device: DeviceInfo,
    honeypot_filled: bool = False,
    time_to_first_input: float | None = None,
    time_to_submit: float | None = None,
    paste_count: int = 0,
) -> ExtractedFeatures:
    mouse_metrics = _mouse_metrics(mouse_events)
    keyboard_metrics = _keyboard_metrics(keyboard_events)
    device_metrics = _device_metrics(device)

    total_session_time = max(mouse_metrics["mouse_duration"], keyboard_metrics["typing_duration"])
    if mouse_events and keyboard_events:
        first_time = min(min(event.t for event in mouse_events), min(event.down for event in keyboard_events))
        last_time = max(max(event.t for event in mouse_events), max(event.up for event in keyboard_events))
        total_session_time = max(0.0, last_time - first_time)
    elif mouse_events:
        total_session_time = mouse_metrics["mouse_duration"]
    elif keyboard_events:
        total_session_time = keyboard_metrics["typing_duration"]

    total_event_count = mouse_metrics["mouse_event_count"] + keyboard_metrics["key_event_count"]
    event_density = total_event_count / total_session_time if total_session_time > 0 else 0.0
    mouse_keyboard_ratio = (
        mouse_metrics["mouse_event_count"] / keyboard_metrics["key_event_count"]
        if keyboard_metrics["key_event_count"] > 0
        else float(mouse_metrics["mouse_event_count"])
    )

    return ExtractedFeatures(
        **mouse_metrics,
        **keyboard_metrics,
        total_session_time=total_session_time,
        event_density=event_density,
        mouse_keyboard_ratio=mouse_keyboard_ratio,
        **device_metrics,
        honeypot_triggered=int(honeypot_filled),
        time_to_first_input=time_to_first_input or 0.0,
        time_to_submit=time_to_submit or 0.0,
        paste_count=paste_count,
    )
