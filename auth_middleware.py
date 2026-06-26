"""
MEOK auth_middleware (metered) — drop-in replacement for the bundled auth_middleware.py
=======================================================================================
Adds SERVER-SIDE metering: every call checks the live /verify endpoint (persistent
per-key daily limit via Vercel KV). FAIL-OPEN — if /verify is unreachable or KV
isn't configured, calls are allowed (never breaks the MCP). Keeps the existing
check_access(api_key) -> (allowed, message, tier) signature so packages need no code change.

<<<<<<< Updated upstream
Free tier: server-enforced 200/day (anon less). Pro/PAYG/CSOAI keys: unlimited.
Get a free key: https://proofof.ai/get-key.html   Upgrade: https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t
=======
Usage in any server.py:
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
    from auth_middleware import check_access, require_tier, audit_log, Tier

    @mcp.tool(name="my_tool")
    async def my_tool(query: str, api_key: str = "") -> str:
        allowed, msg, tier = check_access(api_key)
        if not allowed:
            return json.dumps({"error": msg, "upgrade_url": "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"})
        # ... tool logic ...
        audit_log(api_key, "my_tool", "eu_ai_act", "result_summary", tier)
        return json.dumps(result)
>>>>>>> Stashed changes
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error

_VERIFY_URL = os.environ.get("MEOK_VERIFY_URL", "https://proofof.ai/verify")
_PRO = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"
_TIMEOUT = float(os.environ.get("MEOK_VERIFY_TIMEOUT", "2.5"))


def _server_check(api_key: str, tool: str = ""):
    """Returns (allowed, tier, remaining) from the server, or None on any failure (fail-open)."""
    try:
        data = json.dumps({"api_key": api_key, "tool": tool}).encode()
        req = urllib.request.Request(_VERIFY_URL, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            d = json.load(r)
            return bool(d.get("allowed", True)), d.get("tier", "free"), d.get("remaining")
    except Exception:
        return None  # fail-open


def check_access(api_key: str = ""):
    key = (api_key or os.environ.get("MEOK_API_KEY", "")).strip()
    # Pro/PAYG/CSOAI keys: trusted, unlimited (still cheap local check)
    if key.startswith(("CSOAI-", "meok_pro_", "payg_")):
        return True, "OK (pro)", "pro"
    res = _server_check(key)
    if res is None:
        # fail-open: behave like the free tier without hard enforcement
        msg = "OK, Pro at https://proofof.ai/get-key.html" if not key else "OK"
        return True, msg, ("free" if key else "free")
    allowed, tier, remaining = res
    if allowed:
        return True, f"OK ({remaining} left today)" if remaining not in (None, "unlimited") else "OK", tier
    return False, f"Free daily limit reached. Upgrade (unlimited): {_PRO} — or get a free key: https://proofof.ai/get-key.html", tier


# ── Attestation primitive (the moat): HMAC-sign any tool result ──────────────
import hmac as _hmac, hashlib as _hashlib, json as _json


def meok_attest(result) -> str:
    """Return a verifiable HMAC-SHA256 attestation of a tool result. Sign with
    MEOK_ATTEST_KEY (env) — verifiable by anyone with the key at verify.meok.ai.
    Wire into a tool by adding {"attestation": meok_attest(out)} to its return."""
    key = os.environ.get("MEOK_ATTEST_KEY", "meok-public").encode()
    payload = _json.dumps(result, sort_keys=True, default=str).encode()
    return _hmac.new(key, payload, _hashlib.sha256).hexdigest()


from enum import Enum

class Tier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
<<<<<<< Updated upstream
=======


TIER_LIMITS = {
    Tier.FREE:          {"calls_per_day": 10,   "frameworks": 1,  "audit_trail": False},
    Tier.STARTER:       {"calls_per_day": 100,  "frameworks": 1,  "audit_trail": False},
    Tier.PROFESSIONAL:  {"calls_per_day": 1000, "frameworks": 5,  "audit_trail": True},
    Tier.ENTERPRISE:    {"calls_per_day": -1,   "frameworks": -1, "audit_trail": True},
}

TIER_ORDER = [Tier.FREE, Tier.STARTER, Tier.PROFESSIONAL, Tier.ENTERPRISE]

MEOK_DIR = os.path.expanduser("~/.meok")
USAGE_FILE = os.path.join(MEOK_DIR, "usage.json")
KEYS_FILE = os.path.join(MEOK_DIR, "api_keys.json")
AUDIT_FILE = os.path.join(MEOK_DIR, "audit_trail.jsonl")


def _ensure_dir():
    os.makedirs(MEOK_DIR, exist_ok=True)


def _load_json(path: str) -> dict:
    _ensure_dir()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_json(path: str, data: dict):
    _ensure_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_api_key(tier: Tier, customer_name: str) -> str:
    """Generate a new API key for a customer. Run manually to onboard customers."""
    raw = f"meok_{tier.value}_{customer_name}_{time.time()}"
    key = f"meok_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
    
    keys = _load_json(KEYS_FILE)
    keys[key] = {
        "tier": tier.value,
        "customer": customer_name,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active": True,
    }
    _save_json(KEYS_FILE, keys)
    return key


def get_tier_from_api_key(api_key: str) -> Tier:
    """Look up tier for an API key."""
    if not api_key:
        return Tier.FREE
    
    keys = _load_json(KEYS_FILE)
    if api_key in keys and keys[api_key].get("active", True):
        try:
            return Tier(keys[api_key]["tier"])
        except ValueError:
            return Tier.FREE
    
    return Tier.FREE


def check_access(api_key: str = "", framework: str = None) -> Tuple[bool, str, Tier]:
    """
    Main access control function. Returns (allowed, message, tier).
    Call at the start of every tool.
    """
    tier = get_tier_from_api_key(api_key)
    limits = TIER_LIMITS[tier]
    
    # Rate limit check
    usage = _load_json(USAGE_FILE)
    today = time.strftime("%Y-%m-%d")
    key_hash = hashlib.sha256((api_key or "anon").encode()).hexdigest()[:12]
    day_key = f"{key_hash}:{today}"
    
    current = usage.get(day_key, 0)
    max_calls = limits["calls_per_day"]
    
    if max_calls != -1 and current >= max_calls:
        return (
            False,
            f"Rate limit reached ({max_calls}/day on {tier.value} tier). "
            f"Upgrade at https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K",
            tier,
        )
    
    # Record usage
    usage[day_key] = current + 1
    # Clean old entries (keep last 7 days)
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7 * 86400))
    usage = {k: v for k, v in usage.items() if k.split(":")[1] >= cutoff}
    _save_json(USAGE_FILE, usage)
    
    return True, "OK", tier


def require_tier(minimum: Tier, current: Tier) -> Tuple[bool, str]:
    """Check if current tier meets the minimum requirement for a tool."""
    if TIER_ORDER.index(current) < TIER_ORDER.index(minimum):
        return (
            False,
            f"Requires {minimum.value} tier. Current: {current.value}. "
            f"Upgrade at https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K",
        )
    return True, "OK"


def audit_log(
    api_key: str,
    tool_name: str,
    framework: str,
    result_summary: str,
    tier: Tier,
):
    """Append to audit trail. Only Professional and Enterprise tiers generate audit logs."""
    if not TIER_LIMITS[tier]["audit_trail"]:
        return
    
    _ensure_dir()
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool_name,
        "framework": framework,
        "result": result_summary[:200],
        "tier": tier.value,
        "key_prefix": (api_key or "")[:8] + "...",
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_usage_stats(api_key: str = "") -> dict:
    """Get usage statistics for an API key."""
    usage = _load_json(USAGE_FILE)
    tier = get_tier_from_api_key(api_key)
    limits = TIER_LIMITS[tier]
    
    key_hash = hashlib.sha256((api_key or "anon").encode()).hexdigest()[:12]
    today = time.strftime("%Y-%m-%d")
    day_key = f"{key_hash}:{today}"
    
    return {
        "tier": tier.value,
        "calls_today": usage.get(day_key, 0),
        "limit": limits["calls_per_day"],
        "remaining": max(0, limits["calls_per_day"] - usage.get(day_key, 0))
            if limits["calls_per_day"] != -1 else "unlimited",
        "audit_trail": limits["audit_trail"],
    }


# CLI for key management
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python auth_middleware.py generate <tier> <customer_name>")
        print("  python auth_middleware.py list")
        print("  python auth_middleware.py stats <api_key>")
        print(f"\nTiers: {', '.join(t.value for t in Tier)}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "generate":
        tier = Tier(sys.argv[2])
        name = sys.argv[3]
        key = generate_api_key(tier, name)
        print(f"Generated key: {key}")
        print(f"Tier: {tier.value}")
        print(f"Customer: {name}")
    
    elif cmd == "list":
        keys = _load_json(KEYS_FILE)
        for k, v in keys.items():
            status = "active" if v.get("active", True) else "disabled"
            print(f"  {k[:20]}... | {v['tier']:15} | {v['customer']:20} | {status}")
    
    elif cmd == "stats":
        key = sys.argv[2]
        stats = get_usage_stats(key)
        print(json.dumps(stats, indent=2))
>>>>>>> Stashed changes
