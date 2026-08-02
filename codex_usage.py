#!/usr/bin/env python3
"""Live Codex subscription usage tracker for SwiftBar/xbar."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

AUTH_FILE = os.path.expanduser(os.environ.get("CODEX_USAGE_AUTH_FILE", "~/.codex/auth.json"))
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


class UsageError(RuntimeError):
    pass


def load_auth(path=AUTH_FILE):
    """Get a ChatGPT subscription token without printing or persisting it."""
    token = os.environ.get("CODEX_USAGE_TOKEN", "").strip()
    account_id = os.environ.get("CODEX_USAGE_ACCOUNT_ID", "").strip()
    if token:
        return token, account_id
    try:
        with open(path) as file:
            tokens = json.load(file)["tokens"]
        return tokens["access_token"], tokens.get("account_id", "")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise UsageError("Codex is not signed in. Run `codex login`, or set CODEX_USAGE_TOKEN.") from exc


def fetch_usage(opener=urllib.request.urlopen):
    token, account_id = load_auth()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "codex-usage-pace-tracker"}
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    try:
        with opener(urllib.request.Request(USAGE_URL, headers=headers), timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise UsageError("Codex login expired. Open Codex or run `codex login` and try again.") from exc
        raise UsageError(f"Codex usage request failed (HTTP {exc.code}).") from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise UsageError("Could not reach Codex usage. Check your connection and try again.") from exc


def local_time(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone().replace(tzinfo=None) if isinstance(epoch, (int, float)) else None


def pace(pct, resets_at, seconds, now):
    if not resets_at or not seconds:
        return None
    period = timedelta(seconds=seconds)
    elapsed = (now - (resets_at - period)) / period
    if not 0 < elapsed <= 1:
        return None
    eod = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    eod_target = min((min(eod, resets_at) - (resets_at - period)) / period * 100, 100)
    delta = round(pct - elapsed * 100, 1)
    if delta == 0:
        delta = 0.0
    return {
        "target_now": round(elapsed * 100, 1),
        "target_eod": round(eod_target, 1),
        "delta": delta,
        "projection": round(pct / elapsed),
    }


def duration_label(seconds):
    minutes = round((seconds or 0) / 60)
    if minutes and minutes % 10080 == 0:
        return f"{minutes // 10080}-week"
    if minutes and minutes % 1440 == 0:
        return f"{minutes // 1440}-day"
    if minutes and minutes % 60 == 0:
        return f"{minutes // 60}-hour"
    return f"{minutes}-minute" if minutes else "usage"


def normalize_window(raw, label, now):
    if not isinstance(raw, dict) or not isinstance(raw.get("used_percent"), (int, float)):
        return None
    seconds = raw.get("limit_window_seconds")
    reset = local_time(raw.get("reset_at"))
    return {
        "label": label or duration_label(seconds),
        "pct": raw["used_percent"],
        "resets_at": reset,
        "duration_seconds": seconds,
        "pace": pace(raw["used_percent"], reset, seconds, now),
    }


def analyze(payload=None, now=None):
    now = now or datetime.now()
    payload = fetch_usage() if payload is None else payload
    windows = []
    rate_limit = payload.get("rate_limit") or {}
    for key in ("primary_window", "secondary_window"):
        window = normalize_window(rate_limit.get(key), None, now)
        if window:
            windows.append(window)
    for item in payload.get("additional_rate_limits") or []:
        window = normalize_window((item.get("rate_limit") or {}).get("primary_window"), item.get("limit_name"), now)
        if window:
            windows.append(window)
    if not windows:
        raise UsageError("Codex did not return any subscription usage limits for this account.")
    return {"plan_type": payload.get("plan_type"), "sampled_at": now, "windows": windows}


def fmt_dt(value):
    return value.strftime("%a %b %-d %H:%M") if value else "?"


def arrow(delta):
    if delta is None:
        return "◐", None
    if delta > 3:
        return "▲", "red"
    if delta < -3:
        return "▼", "#28a745"
    return "●", None


def console_report(result):
    plan = f" ({result['plan_type']})" if result["plan_type"] else ""
    lines = [f"Codex subscription usage{plan}", f"  sampled {fmt_dt(result['sampled_at'])} via live Codex usage"]
    for window in result["windows"]:
        lines.extend(["", f"  {window['label']:<22}: {window['pct']:g}%  (resets {fmt_dt(window['resets_at'])})"])
        if window["pace"]:
            item = window["pace"]
            status = "ON PACE" if abs(item["delta"]) <= 3 else ("OVER pace" if item["delta"] > 0 else "under pace")
            sign = "+" if item["delta"] >= 0 else ""
            lines.extend([
                f"    pace target : {item['target_now']}% now, {item['target_eod']}% by end of today",
                f"    status      : {status}  ({sign}{item['delta']} pts vs linear budget)",
                f"    projection  : ~{item['projection']}% at reset",
            ])
    return "\n".join(lines)


def swiftbar_report(result):
    first = result["windows"][0]
    icon, color = arrow(first["pace"]["delta"] if first["pace"] else None)
    lines = [f"{icon} {first['pct']:g}%" + (f" | color={color}" if color else ""), "---"]
    plan = f" ({result['plan_type']})" if result["plan_type"] else ""
    lines.append(f"Codex subscription{plan} | size=13")
    for window in result["windows"]:
        lines.append(f"{window['label']}: {window['pct']:g}% used — resets {fmt_dt(window['resets_at'])} | size=13")
        if window["pace"]:
            item = window["pace"]
            sign = "+" if item["delta"] >= 0 else ""
            lines.extend([
                f"-- pace target now: {item['target_now']}% ({sign}{item['delta']} pts) | size=13",
                f"-- budget by end of today: {item['target_eod']}% | size=13",
                f"-- projected at reset: ~{item['projection']}% | size=13",
            ])
    lines.extend(["---", f"Sampled: {fmt_dt(result['sampled_at'])} via live Codex usage | size=12 color=gray"])
    return "\n".join(lines)


def main(argv):
    swiftbar = "--swiftbar" in argv
    try:
        result = analyze()
        if "--json" in argv:
            output = {**result, "sampled_at": result["sampled_at"].isoformat()}
            output["windows"] = [{**window, "resets_at": window["resets_at"].isoformat() if window["resets_at"] else None} for window in result["windows"]]
            print(json.dumps(output, indent=2))
        else:
            print(swiftbar_report(result) if swiftbar else console_report(result))
    except UsageError as exc:
        if swiftbar:
            print("⚠︎ Codex | color=orange\n---\n" + str(exc) + " | color=red")
        else:
            print(f"Codex usage: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
