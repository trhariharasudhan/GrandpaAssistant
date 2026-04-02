import os
import sys
import threading
import time


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402
from utils.config import get_setting  # noqa: E402


def _now():
    return time.time()


def _poll_states(duration_seconds=3.0, interval=0.02):
    seen = []
    end_at = _now() + duration_seconds
    while _now() < end_at:
        state = web_api._voice_status_payload().get("state_label", "")
        if state and state not in seen:
            seen.append(state)
        time.sleep(interval)
    return seen


def _run_with_fake_listen(sequence, test_name):
    results = {"test": test_name, "ok": False, "states": [], "diagnostics": {}}
    queue = list(sequence)
    queue_lock = threading.Lock()

    original_listen = web_api.listen
    original_speak = web_api.voice_speak_module.speak
    original_capture = web_api._capture_command_reply

    def fake_listen(for_wake_word=False, for_follow_up=False):
        with queue_lock:
            if not queue:
                time.sleep(0.04)
                return None
            expected_mode, value, delay = queue.pop(0)

        if expected_mode == "wake" and not for_wake_word:
            with queue_lock:
                queue.insert(0, (expected_mode, value, delay))
            time.sleep(0.04)
            return None
        if expected_mode == "follow" and (for_wake_word or not for_follow_up):
            with queue_lock:
                queue.insert(0, (expected_mode, value, delay))
            time.sleep(0.04)
            return None

        if delay > 0:
            time.sleep(delay)
        return value

    def fake_capture(command):
        # Keep speaking state visible briefly for polling.
        time.sleep(0.12)
        return [f"Handled: {command}"]

    try:
        web_api.listen = fake_listen
        web_api.voice_speak_module.speak = lambda *args, **kwargs: None
        web_api._capture_command_reply = fake_capture

        web_api.stop_voice_api_mode()
        web_api.start_voice_api_mode()
        results["states"] = _poll_states(duration_seconds=2.4)
        payload = web_api._voice_status_payload()
        results["diagnostics"] = payload.get("diagnostics", {})
        return results
    finally:
        web_api.stop_voice_api_mode()
        time.sleep(0.15)
        web_api.listen = original_listen
        web_api.voice_speak_module.speak = original_speak
        web_api._capture_command_reply = original_capture


def run_state_flow_test():
    # wake word => awake => follow-up => command => speaking/follow_up
    sequence = [
        ("wake", "hey grandpa", 0.35),
        ("follow", "voice status", 0.20),
    ]
    result = _run_with_fake_listen(sequence, "state_flow")
    states = result["states"]
    diagnostics = result["diagnostics"]
    has_states = all(s in states for s in ["sleeping", "awake", "follow_up", "speaking"])
    has_counts = diagnostics.get("wake_detection_count", 0) >= 1 and diagnostics.get("command_count", 0) >= 1
    result["ok"] = bool(has_states and has_counts)
    return result


def run_interrupt_phrase_test(phrase):
    sequence = [
        ("wake", "hey grandpa", 0.0),
        ("follow", phrase, 0.15),
    ]
    result = _run_with_fake_listen(sequence, f"interrupt_{phrase}")
    diagnostics = result["diagnostics"]
    result["ok"] = (
        diagnostics.get("interrupt_count", 0) >= 1
        and diagnostics.get("last_interrupt_at")
        and "interrupted" in result["states"]
    )
    return result


def run_command_parser_checks():
    commands = [
        "set wake threshold to 0.72",
        "set wake retry window to 8 seconds",
        "set follow up timeout to 12 seconds",
        "set follow up listen timeout to 3 seconds",
        "set follow up phrase limit to 5 seconds",
        "set interrupt follow up window to 6 seconds",
        "set post wake pause to 0.4 seconds",
        "disable wake fallback",
        "enable wake fallback",
        "disable voice desktop popup",
        "enable voice desktop popup",
        "disable voice desktop chime",
        "enable voice desktop chime",
    ]
    outputs = []
    for command in commands:
        messages = web_api._capture_command_reply(command)
        outputs.append((command, messages))

    checks = {
        "wake_match_threshold": float(get_setting("voice.wake_match_threshold", 0)),
        "wake_retry_window_seconds": float(get_setting("voice.wake_retry_window_seconds", 0)),
        "follow_up_timeout_seconds": float(get_setting("voice.follow_up_timeout_seconds", 0)),
        "follow_up_listen_timeout": float(get_setting("voice.follow_up_listen_timeout", 0)),
        "follow_up_phrase_time_limit": float(get_setting("voice.follow_up_phrase_time_limit", 0)),
        "interrupt_follow_up_seconds": float(get_setting("voice.interrupt_follow_up_seconds", 0)),
        "post_wake_pause_seconds": float(get_setting("voice.post_wake_pause_seconds", 0)),
        "wake_direct_fallback_enabled": bool(get_setting("voice.wake_direct_fallback_enabled", False)),
        "desktop_popup_enabled": bool(get_setting("voice.desktop_popup_enabled", False)),
        "desktop_chime_enabled": bool(get_setting("voice.desktop_chime_enabled", False)),
    }
    ok = (
        abs(checks["wake_match_threshold"] - 0.72) < 0.0001
        and abs(checks["wake_retry_window_seconds"] - 8.0) < 0.0001
        and abs(checks["follow_up_timeout_seconds"] - 12.0) < 0.0001
        and abs(checks["follow_up_listen_timeout"] - 3.0) < 0.0001
        and abs(checks["follow_up_phrase_time_limit"] - 5.0) < 0.0001
        and abs(checks["interrupt_follow_up_seconds"] - 6.0) < 0.0001
        and abs(checks["post_wake_pause_seconds"] - 0.4) < 0.0001
        and checks["wake_direct_fallback_enabled"]
        and checks["desktop_popup_enabled"]
        and checks["desktop_chime_enabled"]
    )
    return {"ok": ok, "outputs": outputs, "checks": checks}


def _print_result_line(name, ok):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")


def main():
    overall_ok = True

    state_result = run_state_flow_test()
    _print_result_line("Wake/follow-up/state flow", state_result["ok"])
    print(f"  States seen: {', '.join(state_result['states'])}")
    print(f"  Diagnostics: {state_result['diagnostics']}")
    overall_ok = overall_ok and state_result["ok"]

    interrupt_phrases = ["stop", "wait", "cancel", "listen"]
    interrupt_results = []
    for phrase in interrupt_phrases:
        result = run_interrupt_phrase_test(phrase)
        interrupt_results.append(result)
        _print_result_line(f"Interrupt phrase '{phrase}'", result["ok"])
        print(f"  States seen: {', '.join(result['states'])}")
        print(f"  Interrupt count: {result['diagnostics'].get('interrupt_count', 0)}")
        overall_ok = overall_ok and result["ok"]

    parser_result = run_command_parser_checks()
    _print_result_line("Voice tuning parser + popup/chime toggles", parser_result["ok"])
    print(f"  Checks: {parser_result['checks']}")
    for command, messages in parser_result["outputs"]:
        preview = messages[0] if messages else "(no message)"
        print(f"  {command} => {preview}")
    overall_ok = overall_ok and parser_result["ok"]

    print("\nSummary:")
    print(f"overall_ok={overall_ok}")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
