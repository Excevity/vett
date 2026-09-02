#!/usr/bin/env python3
"""Twice-a-day posting guard for CI.

GitHub's scheduler is best-effort — crons get delayed or skipped. So the
workflow fires SEVERAL cron attempts per slot, and this guard makes sure we post
exactly ONCE per slot: the first attempt that lands posts and marks the slot;
later attempts in the same slot see the mark and skip.

Two slots per day: 'am' (before 18:00 UTC) and 'pm' (18:00 UTC and later).
State lives in state/posted.json, persisted across runs via the Actions cache.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "state", "posted.json")

def _slot():
    return "am" if time.gmtime().tm_hour < 18 else "pm"

def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())

def _load():
    try:
        d = json.load(open(STATE))
        if d.get("date") != _today():
            return {"date": _today(), "slots": []}
        return d
    except Exception:
        return {"date": _today(), "slots": []}

def decide():
    d = _load()
    slot = _slot()
    return ("no" if slot in d.get("slots", []) else "yes"), slot

def mark(slot=None):
    slot = slot or _slot()
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    d = _load()
    if slot not in d.get("slots", []):
        d.setdefault("slots", []).append(slot)
    d["date"] = _today()
    json.dump(d, open(STATE, "w"))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "decide"
    if cmd == "decide":
        should, slot = decide()
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"post={should}\nslot={slot}\n")
        print(f"slot={slot} post={should}")
    elif cmd == "mark":
        mark(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"marked slot {_slot()} for {_today()}")
