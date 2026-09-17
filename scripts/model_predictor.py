#!/usr/bin/env python3
"""
Smart Model Switcher — predicts the best model for a given task.

Classifies a task description on four axes (cognitive demand, output shape,
context size, failure tolerance), maps to the routing decision matrix from
the hybrid-model-router skill, and outputs the recommended model + fallbacks.

Usage:
    python3 scripts/model_predictor.py "task description"
    python3 scripts/model_predictor.py --json "task description"
    echo "task description" | python3 scripts/model_predictor.py

Output (JSON to stdout with --json, human-readable otherwise):
    {
      "classification": {
        "cognitive": "synthesis",
        "output": "structured",
        "context": "<131K",
        "failure_tolerance": "low"
      },
      "tier": 2,
      "model": "ollama-local/gpt-oss:120b-cloud",
      "fallbacks": ["openrouter/deepseek/deepseek-v4-flash-0731", "openrouter/z-ai/glm-5.2"],
      "reasoning": "Task involves synthesis/cross-referencing → Tier 2 free cloud"
    }

Integration:
    - Called before creating a cron job or dispatching a subagent
    - Output model/fallbacks used directly in payload.model / payload.fallbacks
    - Verifies the recommended model is in the allowlist (openclaw.json)
    - Optionally checks endpoint health via model_health_monitor.py

Design:
    - Rule-based classification (keyword matching → taxonomy)
    - No LLM tokens consumed (pure local computation)
    - Reads the live model registry from openclaw.json
    - Aligns with hybrid-model-router/SKILL.md routing decision matrix
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ─── Model Registry (mirrors hybrid-model-router/SKILL.md §1) ────────────────

ACTIVE_MODELS = [
    {
        "id": "ollama-local/qwen3:8b",
        "alias": "qwen3-8b-local",
        "tier": 1,
        "cost": 0,
        "context": 32768,
        "min_servable_tokens": 32768,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "14GiB RAM box; OLLAMA_MAX_LOADED_MODELS=1",
    },
    {
        "id": "ollama-local/gpt-oss:120b-cloud",
        "alias": "gpt-oss:120b-cloud",
        "tier": 2,
        "cost": 0,
        "context": 131072,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "Ollama Cloud free tier; fast, clean JSON",
    },
    {
        "id": "google/gemini-3.6-flash",
        "alias": "gemini-3.6-flash",
        "tier": 2,
        "cost": 0,
        "context": 1048576,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "Google AI Studio free; 1M ctx; verified 2026-09-10",
    },
    {
        "id": "google/gemini-flash-latest",
        "alias": "gemini-flash-latest",
        "tier": 2,
        "cost": 0,
        "context": 1048576,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "Google AI Studio free; always-latest; 1M ctx",
    },
    {
        "id": "google/gemini-3.1-flash-lite",
        "alias": "gemini-flash-lite",
        "tier": 2,
        "cost": 0,
        "context": 1048576,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": False,
        "notes": "Google AI Studio free; lightweight, no reasoning overhead",
    },
    {
        "id": "openrouter/deepseek/deepseek-v4-flash-0731",
        "alias": "deepseek-v4-flash",
        "tier": 3,
        "cost": 0.07,
        "context": 256000,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "Primary paid; fast, reliable",
    },
    {
        "id": "openrouter/z-ai/glm-5.2",
        "alias": "glm-5.2",
        "tier": 3,
        "cost": 0.15,
        "context": 1000000,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "Last-resort fallback; highest quality; most expensive",
    },
    {
        "id": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        "alias": "nemotron-ultra:free",
        "tier": 2,
        "cost": 0,
        "context": 1000000,
        "min_servable_tokens": 131072,
        "json_reliable": False,
        "tools": True,
        "reasoning": True,
        "notes": "Frequently 502/503; fallback only",
    },
    {
        "id": "openrouter/cohere/north-mini-code:free",
        "alias": "north-mini-code",
        "tier": 2,
        "cost": 0,
        "context": 256000,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "OpenRouter free; agentic coding; TOOLS=YES verified 2s 2026-09-10",
    },
    {
        "id": "openrouter/nex-agi/nex-n2.5-pro:free",
        "alias": "nex-n2.5-pro",
        "tier": 2,
        "cost": 0,
        "context": 262144,
        "min_servable_tokens": 131072,
        "json_reliable": True,
        "tools": True,
        "reasoning": True,
        "notes": "OpenRouter free; agentic; JSON tools; 235K max out",
    },
]

# ─── Retired models (never recommend) ────────────────────────────────────────

RETIRED_MODELS = {
    "minimax/minimax-m3:free",
    "minimax/minimax-m2.7:free",
    "openrouter/z-ai/glm-5.2:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "openai/gpt-oss:120b",
}

# ─── Routing Decision Matrix (mirrors hybrid-model-router/SKILL.md §2) ────────

ROUTING_MATRIX = [
    # (cognitive, output, context, failure_tol, primary_alias, [fallback_aliases])
    ("mechanical", "plain", "<32K", "medium", "qwen3-8b-local", ["nemotron-ultra:free", "glm-5.2"]),
    ("mechanical", "json", "<32K", "medium", "qwen3-8b-local", ["nemotron-ultra:free", "glm-5.2"]),
    ("analytical", "plain", "<32K", "medium", "qwen3-8b-local", ["gpt-oss:120b-cloud", "glm-5.2"]),
    ("analytical", "json", "<32K", "low", "gpt-oss:120b-cloud", ["deepseek-v4-flash", "glm-5.2"]),
    ("synthesis", "plain", "<131K", "low", "gpt-oss:120b-cloud", ["deepseek-v4-flash", "glm-5.2"]),
    ("synthesis", "structured", "<131K", "low", "gpt-oss:120b-cloud", ["deepseek-v4-flash", "glm-5.2"]),
    ("synthesis", "plain", "<131K", "medium", "gpt-oss:120b-cloud", ["deepseek-v4-flash", "glm-5.2"]),
    ("decision", "json", "<131K", "low", "deepseek-v4-flash", ["gpt-oss:120b-cloud", "glm-5.2"]),
    ("decision", "structured", "<131K", "low", "deepseek-v4-flash", ["glm-5.2"]),
    ("decision", "plain", "<131K", "low", "deepseek-v4-flash", ["gpt-oss:120b-cloud", "glm-5.2"]),
]

# ─── Task Classification (keyword-based) ─────────────────────────────────────

# Cognitive demand keywords
DECISION_KEYWORDS = {
    "trade", "trading", "buy", "sell", "market", "merge", "deploy", "publish",
    "approve", "reject", "commit", "push", "ship", "release", "rollout",
    "execute", "authorize", "confirm", "decide", "choose", "select",
    "polymarket", "kalshi", "portfolio", "investment", "financial",
}
SYNTHESIS_KEYWORDS = {
    "synthesize", "review", "report", "assess", "analyze", "reflect",
    "summarize", "consolidate", "knowledge", "episodic", "memory",
    "metacognitive", "self-assessment", "standup", "briefing", "retrospective",
    "weekly", "monthly", "daily", "electric sheep", "dream", "publish",
}
ANALYTICAL_KEYWORDS = {
    "check", "scan", "sync", "health", "status", "monitor", "verify",
    "validate", "audit", "inspect", "diagnose", "troubleshoot", "debug",
    "heartbeat", "ping", "test", "gate", "lint",
}
MECHANICAL_KEYWORDS = {
    "backup", "copy", "count", "list", "format", "rename", "move",
    "archive", "cleanup", "prune", "trim", "vacuum", "schedule",
    "follow-back", "github sync", "sheet", "spreadsheet",
}

# Output shape keywords
JSON_KEYWORDS = {"json", "parse", "serialize", "structured", "yaml", "toml", "config"}
CODE_KEYWORDS = {"code", "function", "class", "method", "refactor", "bugfix", "fix", "implement", "patch", "diff", "test"}
LARGE_CONTEXT_KEYWORDS = {"large", "long", "full", "entire", "all", "complete", "comprehensive", "everything", "wholesale"}

# Failure tolerance keywords
LOW_TOLERANCE_KEYWORDS = {"critical", "must", "required", "essential", "important", "urgent", "merge", "deploy", "trade"}
HIGH_TOLERANCE_KEYWORDS = {"best-effort", "optional", "informational", "nice-to-have", "idle", "background"}


def classify_cognitive(text):
    """Classify cognitive demand from task description."""
    text_lower = text.lower()
    words = set(re.findall(r"[a-z]+", text_lower))

    decision_hits = len(words & DECISION_KEYWORDS)
    synthesis_hits = len(words & SYNTHESIS_KEYWORDS)
    analytical_hits = len(words & ANALYTICAL_KEYWORDS)
    mechanical_hits = len(words & MECHANICAL_KEYWORDS)

    # Also check for phrase matches (multi-word keywords)
    for kw in DECISION_KEYWORDS:
        if " " in kw and kw in text_lower:
            decision_hits += 1
    for kw in SYNTHESIS_KEYWORDS:
        if " " in kw and kw in text_lower:
            synthesis_hits += 1
    for kw in MECHANICAL_KEYWORDS:
        if " " in kw and kw in text_lower:
            mechanical_hits += 1

    max_hits = max(decision_hits, synthesis_hits, analytical_hits, mechanical_hits)
    if max_hits == 0:
        return "analytical"  # default fallback
    if max_hits == decision_hits:
        return "decision"
    if max_hits == synthesis_hits:
        return "synthesis"
    if max_hits == analytical_hits:
        return "analytical"
    return "mechanical"


def classify_output(text):
    """Classify output shape from task description."""
    text_lower = text.lower()
    words = set(re.findall(r"[a-z]+", text_lower))
    if words & CODE_KEYWORDS:
        return "code"
    if words & JSON_KEYWORDS or "structured" in text_lower or "json" in text_lower:
        return "json"
    return "plain"


def classify_context(text, estimated_tokens=None):
    """Classify context size."""
    if estimated_tokens:
        if estimated_tokens > 131072:
            return ">131K"
        if estimated_tokens > 32768:
            return "32K-131K"
        return "<32K"
    # Heuristic: if the task mentions "large", "full", "entire" etc.
    text_lower = text.lower()
    for kw in LARGE_CONTEXT_KEYWORDS:
        if kw in text_lower:
            return "32K-131K"
    return "<131K"  # default


def classify_failure_tolerance(text):
    """Classify failure tolerance."""
    text_lower = text.lower()
    words = set(re.findall(r"[a-z]+", text_lower))
    if words & LOW_TOLERANCE_KEYWORDS:
        return "low"
    if words & HIGH_TOLERANCE_KEYWORDS:
        return "high"
    # Default: medium for analytical, low for decision/synthesis
    return "medium"


def resolve_model(alias_or_id):
    """Resolve an alias or id to the full model entry."""
    for m in ACTIVE_MODELS:
        if m["alias"] == alias_or_id or m["id"] == alias_or_id:
            return m
    return None


def route(classification, estimated_tokens=None):
    """Map classification to model + fallbacks using the routing matrix, screening by ceiling."""
    cognitive = classification["cognitive"]
    output = classification["output"]
    context = classification["context"]
    tolerance = classification["failure_tolerance"]

    all_screened = []  # Accumulate all screened models across attempts
    seen_screened = set()  # Track model_ids to deduplicate

    def _screen_model(alias, reason_prefix):
        """Check if model can serve estimated_tokens. Return (model_entry, screened_out_entry)."""
        model = resolve_model(alias)
        if not model:
            return None, {"alias": alias, "reason": f"{reason_prefix}: not found in registry"}
        min_servable = model.get("min_servable_tokens", model.get("context", 131072))
        if estimated_tokens is not None and estimated_tokens > min_servable:
            return None, {
                "alias": alias,
                "model_id": model["id"],
                "reason": f"{reason_prefix}: needs {estimated_tokens} tokens, ceiling is {min_servable}"
            }
        return model, None

    def _screen_fallbacks(fallback_aliases):
        """Screen fallback list, return (valid_fallbacks, screened_out_list)."""
        valid = []
        screened = []
        for alias in fallback_aliases:
            model, screened_entry = _screen_model(alias, "fallback")
            if model:
                valid.append(model)
            else:
                screened.append(screened_entry)
        return valid, screened

    def _try_entry(primary_alias, fallback_aliases):
        """Try a routing entry, return (primary_model, fallback_models, screened_out) or (None, None, screened_out)."""
        primary_model, primary_screened = _screen_model(primary_alias, "primary")
        fallback_models, fallback_screened = _screen_fallbacks(fallback_aliases)
        screened = []
        if primary_screened:
            screened.append(primary_screened)
        screened.extend(fallback_screened)
        if primary_model:
            return primary_model, fallback_models, screened
        return None, None, screened

    # Try exact match first, then progressively relax
    for entry in ROUTING_MATRIX:
        r_cog, r_out, r_ctx, r_tol, primary_alias, fallback_aliases = entry
        if (r_cog == cognitive and
                r_out in (output, "plain", "structured") and
                (r_ctx == context or r_ctx == "<131K") and
                (r_tol == tolerance or r_tol == "low")):
            primary_model, fallback_models, screened = _try_entry(primary_alias, fallback_aliases)
            for s in screened:
                if s["model_id"] not in seen_screened:
                    all_screened.append(s)
                    seen_screened.add(s["model_id"])
            if primary_model:
                return primary_model, fallback_models, all_screened

    # Fallback: match cognitive only
    for entry in ROUTING_MATRIX:
        r_cog, _, _, _, primary_alias, fallback_aliases = entry
        if r_cog == cognitive:
            primary_model, fallback_models, screened = _try_entry(primary_alias, fallback_aliases)
            for s in screened:
                if s["model_id"] not in seen_screened:
                    all_screened.append(s)
                    seen_screened.add(s["model_id"])
            if primary_model:
                return primary_model, fallback_models, all_screened

    # Ultimate fallback - try the default chain with screening
    primary_model, fallback_models, screened = _try_entry("gpt-oss:120b-cloud", ["deepseek-v4-flash", "glm-5.2"])
    for s in screened:
        if s["model_id"] not in seen_screened:
            all_screened.append(s)
            seen_screened.add(s["model_id"])
    if primary_model:
        return primary_model, fallback_models, all_screened

    # Last resort: return first model that passes screening
    for m in ACTIVE_MODELS:
        min_servable = m.get("min_servable_tokens", m.get("context", 131072))
        if estimated_tokens is None or estimated_tokens <= min_servable:
            return m, [], all_screened
    return ACTIVE_MODELS[0], [], all_screened


def check_allowlist(model_id):
    """Check if model_id is in the openclaw.json allowlist."""
    openclaw_path = Path.home() / ".openclaw" / "openclaw.json"
    if not openclaw_path.exists():
        return None, "openclaw.json not found"
    try:
        cfg = json.loads(openclaw_path.read_text())
        allowlist = cfg.get("agents", {}).get("defaults", {}).get("models", {})
        if model_id in allowlist:
            return True, f"{model_id} is in the allowlist"
        return False, f"{model_id} is NOT in the allowlist — add it before assigning to a cron"
    except Exception as e:
        return None, f"Error reading allowlist: {e}"


def predict(task_description, estimated_tokens=None, check_health=False, small_prompt=False):
    """Main prediction function. Returns the routing recommendation."""
    # Determine token estimate for ceiling screening
    # Default: 40000 for agent sessions; small_prompt mode uses a low value to keep groq/cerebras eligible
    if small_prompt:
        screening_tokens = 4000  # Small prompt mode: assume ~4K tokens
    elif estimated_tokens is not None:
        screening_tokens = estimated_tokens
    else:
        screening_tokens = 40000  # Agent-session work standard

    # Classify (uses estimated_tokens for context classification heuristic)
    cognitive = classify_cognitive(task_description)
    output = classify_output(task_description)
    context = classify_context(task_description, estimated_tokens)
    tolerance = classify_failure_tolerance(task_description)

    classification = {
        "cognitive": cognitive,
        "output": output,
        "context": context,
        "failure_tolerance": tolerance,
    }

    # Route with ceiling screening
    primary_model, fallback_models, screened_out = route(classification, screening_tokens)

    # Check allowlist
    allowlisted, allowlist_msg = check_allowlist(primary_model["id"])

    # Build reasoning
    reasoning_parts = []
    cog_desc = {
        "mechanical": "runs a script / formats text (no judgment)",
        "analytical": "reads data / evaluates conditions (simple decisions)",
        "synthesis": "cross-references multiple sources / writes structured analysis",
        "decision": "makes consequential choices (errors are costly)",
    }
    reasoning_parts.append(f"Task is {cog_desc.get(cognitive, cognitive)}")
    reasoning_parts.append(f"Output shape: {output}")
    reasoning_parts.append(f"Context: {context}")
    reasoning_parts.append(f"Failure tolerance: {tolerance}")
    cost_str = 'free' if primary_model['cost'] == 0 else f"${primary_model['cost']}/M"
    reasoning_parts.append(f"→ Tier {primary_model['tier']} ({cost_str}: {primary_model['alias']})")
    if screened_out:
        screened_aliases = [s["alias"] for s in screened_out]
        reasoning_parts.append(f"Screened out (ceiling): {', '.join(screened_aliases)}")
    if not allowlisted:
        reasoning_parts.append(f"⚠️ {allowlist_msg}")

    result = {
        "classification": classification,
        "tier": primary_model["tier"],
        "model": primary_model["id"],
        "alias": primary_model["alias"],
        "fallbacks": [m["id"] for m in fallback_models],
        "fallback_aliases": [m["alias"] for m in fallback_models],
        "reasoning": " · ".join(reasoning_parts),
        "allowlisted": allowlisted,
        "allowlist_note": allowlist_msg,
        "prompt_tokens_estimate": screening_tokens,
        "screened_out": screened_out,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Smart Model Switcher — predicts the best model for a task."
    )
    parser.add_argument("task", nargs="*", help="Task description to classify")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--tokens", type=int, default=None, help="Estimated token count for context classification and ceiling screening")
    parser.add_argument("--small-prompt", action="store_true", help="Opt into small-prompt mode (keeps low-ceiling models like Groq/Cerebras eligible)")
    parser.add_argument("--check-health", action="store_true", help="Check endpoint health before recommending")
    args = parser.parse_args()

    # Get task description
    if args.task:
        task_text = " ".join(args.task)
    elif not sys.stdin.isatty():
        task_text = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not task_text:
        print("Error: no task description provided", file=sys.stderr)
        sys.exit(1)

    result = predict(task_text, estimated_tokens=args.tokens, check_health=args.check_health, small_prompt=args.small_prompt)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Classification: {result['classification']}")
        print(f"Tier: {result['tier']}")
        print(f"Model: {result['model']} (alias: {result['alias']})")
        print(f"Fallbacks: {', '.join(result['fallbacks'])}")
        print(f"Reasoning: {result['reasoning']}")
        if result["screened_out"]:
            screened_aliases = [s["alias"] for s in result["screened_out"]]
            print(f"Screened out (ceiling): {', '.join(screened_aliases)}")
        if not result["allowlisted"]:
            print(f"\n⚠️ ALLOWLIST WARNING: {result['allowlist_note']}")


if __name__ == "__main__":
    main()
