#!/usr/bin/env python3
"""Payment reconciliation."""
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


def parse_ts(v):
    if isinstance(v, (int, float)) or str(v).strip().replace(".", "", 1).isdigit():
        n = float(v)
        if n > 1e11:  #i am using milliseconds
            n /= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc)
    s = str(v).strip()
    if s[-1:] in ("Z", "z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_amount(v):
    return Decimal(str(v).replace(",", "").strip())


latest = {}   
skipped = {"unreadable": 0, "no_txn_id": 0, "bad_ts": 0}

with open("payments.jsonl", encoding="utf-8-sig") as f:
    for line_no, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            skipped["unreadable"] += 1
            continue
        if not isinstance(event, dict):
            skipped["unreadable"] += 1
            continue
        txn = event.get("txn_id")
        if txn is None or str(txn).strip() == "":
            skipped["no_txn_id"] += 1
            continue
        txn = str(txn).strip()
        try:
            ts = parse_ts(event["ts"])
        except Exception:
            skipped["bad_ts"] += 1
            continue
        key = (ts, line_no)
        if txn not in latest or key > latest[txn][0]:
            latest[txn] = (key, event)

total = Decimal(0)
count = 0
for _, event in latest.values():
    if str(event.get("status", "")).strip().lower() == "success":
        total += parse_amount(event["amount"])
        count += 1

print(f"Skipped: {skipped}", file=sys.stderr)

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{int(total.quantize(Decimal('1'), rounding=ROUND_HALF_UP))}")