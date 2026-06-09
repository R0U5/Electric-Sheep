#!/usr/bin/env python3
"""Post-Task Reflection Pipeline — connects Execution Outcome Tracker to actionable planning.

Processes all recorded execution outcomes through three stages:
1. REFLECT: Generate Reflexion-style reflections for any unreflected outcomes
2. ANALYZE: Update strategy profiles and compute effectiveness metrics
3. ADVISE: Produce concrete planning directives the planner queries before execution

This bridges the gap between "we tracked what happened" and "we use that to plan better."
The pipeline is idempotent — running it multiple times is safe and will only process new outcomes.

Usage:
    python3 reflection_pipeline.py process          # Process all unreflected outcomes
    python3 reflection_pipeline.py advise --task "What kind of task"  # Get planning directives
    python3 reflection_pipeline.py status            # Show pipeline state
    python3 reflection_pipeline.py digest           # Full summary for memory maintenance
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

# ─── Path Resolution ──────────────────────────────────────────────────────
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"

# Data files (all paths relative to this skill's data dir)
OUTCOMES_FILE = DATA_DIR / "outcomes.json"
REFLECTIONS_FILE = DATA_DIR / "auto_reflections.json"
PROFILES_FILE = DATA_DIR / "strategy_profiles.json"
PIPELINE_STATE = DATA_DIR / "reflection_pipeline_state.json"
DIRECTIVES_FILE = DATA_DIR / "planning_directives.json"

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
OUTCOMES_ROOT = WORKSPACE / "outcomes" / "execution-outcomes.json"


# ─── Helpers ──────────────────────────────────────────────────────────────

def load_json(path, default=None):
    """Load JSON file, return default if missing or invalid."""
    try:
        with open(path, "r") as f:
            text = f.read().strip()
            if not text:
                return default
            return json.loads(text)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    """Write JSON file atomically (write tmp then rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.rename(path)


def load_all_outcomes():
    """Merge outcomes from both skill data and root data dir."""
    outcomes = load_json(OUTCOMES_FILE, [])
    root_outcomes = load_json(OUTCOMES_ROOT, [])

    # Deduplicate by outcome_id/id
    all_ids = {o.get("outcome_id") or o.get("id") for o in outcomes if o}
    for o in root_outcomes:
        oid = o.get("outcome_id") or o.get("id")
        if oid and oid not in all_ids:
            outcomes.append(o)
            all_ids.add(oid)

    return [o for o in outcomes if o]


def get_reflected_ids():
    """Return set of outcome_ids that already have reflections."""
    reflections = load_json(REFLECTIONS_FILE, [])
    return {r.get("outcome_id") for r in reflections if r.get("outcome_id")}


def reflect_on_outcome(outcome):
    """Generate a Reflexion-style reflection for a single outcome.

    Based on the principle that verbal self-reflection on outcomes
    significantly improves future performance (Shinn et al., Reflexion).
    Reflections must be: specific, honest about limitations, and actionable.
    """
    task = outcome.get("task_description", "Unknown task")
    strategy = outcome.get("strategy_used", "unknown")
    result = outcome.get("outcome", "unknown")
    notes = outcome.get("notes", "")
    tools = outcome.get("tools_involved", [])
    conf_before = outcome.get("confidence_before")
    conf_after = outcome.get("confidence_after")

    reflection_parts = []

    if result == "success":
        # Success is worth reflecting on too — what specifically worked?
        reflection_parts.append(
            f"The approach '{strategy}' succeeded for: {task}."
        )
        if tools:
            reflection_parts.append(f"Tools used effectively: {', '.join(tools)}.")

        # Was there a confidence calibration gap?
        if conf_before is not None and conf_after is not None:
            gap = conf_after - conf_before
            if gap > 0.2:
                reflection_parts.append(
                    f"Confidence undershot: predicted {conf_before:.2f} but achieved {conf_after:.2f}. "
                    f"This approach may be more reliable than initially assessed."
                )
            elif gap < -0.2:
                reflection_parts.append(
                    f"Confidence overshot: predicted {conf_before:.2f} but only achieved {conf_after:.2f}. "
                    f"Calibration needed — this approach has hidden complexity."
                )
            else:
                reflection_parts.append("Calibration was good — confidence matched reality.")

        if notes:
            reflection_parts.append(f"Context: {notes}")

        takeaway = "This approach should be preferred for similar future tasks."

    elif result == "partial":
        reflection_parts.append(
            f"The approach '{strategy}' got partway through '{task}' but did not fully succeed."
        )
        if notes:
            reflection_parts.append(f"What was missing: {notes}")

        if conf_before is not None and conf_after is not None:
            gap = conf_after - conf_before
            if gap < -0.15:
                reflection_parts.append(
                    f"Confidence was overestimated ({conf_before:.2f} → {conf_after:.2f}). "
                    f"Future similar tasks need more conservative planning."
                )

        takeaway = (
            "Do not retry this exact approach. "
            "Identify the missing piece before reattempting, or switch strategies."
        )

    else:  # failure
        reflection_parts.append(
            f"The approach '{strategy}' failed for: {task}."
        )
        if notes:
            reflection_parts.append(f"Failure context: {notes}")

        if conf_before is not None:
            reflection_parts.append(
                f"Pre-execution confidence was {conf_before:.2f}. "
                f"{'The failure was surprising' if conf_before > 0.6 else 'The failure was anticipated'}."
            )

        takeaway = (
            "CRITICAL: Do NOT retry the same approach without modification. "
            "Root-cause analysis required. Consider a fundamentally different strategy."
        )

    return {
        "reflection": " ".join(reflection_parts),
        "takeaway": takeaway,
        "needs_review": result == "failure",
        "strategy": strategy,
        "outcome": result,
        "task_truncated": task[:80] if task else "unknown",
    }


# ─── Pipeline Stage 1: Reflect ───────────────────────────────────────────

def stage_reflect(outcomes):
    """Generate reflections for any unreflected outcomes."""
    reflected = get_reflected_ids()
    reflections = load_json(REFLECTIONS_FILE, [])
    processed_count = 0

    for outcome in outcomes:
        oid = outcome.get("outcome_id") or outcome.get("id")
        if not oid or oid in reflected:
            continue

        ref = reflect_on_outcome(outcome)
        reflection = {
            "id": f"reflect-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome_id": oid,
            "task": outcome.get("task_description", "Unknown"),
            "strategy": ref["strategy"],
            "outcome": ref["outcome"],
            "reflection": ref["reflection"],
            "takeaway": ref["takeaway"],
            "auto_generated": True,
            "pipeline_generated": True,
            "needs_review": ref["needs_review"],
        }
        reflections.append(reflection)
        reflected.add(oid)
        processed_count += 1

    if processed_count:
        # Trim to last 200 to prevent unbounded growth
        if len(reflections) > 200:
            reflections = reflections[-200:]
        save_json(REFLECTIONS_FILE, reflections)

    return processed_count, reflections


# ─── Pipeline Stage 2: Analyze ───────────────────────────────────────────

def stage_analyze(outcomes):
    """Update strategy profiles with current outcome data."""
    profiles = {}

    for o in outcomes:
        strat = o.get("strategy_used", "unknown")
        if strat not in profiles:
            profiles[strat] = {
                "strategy": strat,
                "total_uses": 0,
                "success_count": 0,
                "partial_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "last_used": None,
                "task_categories": [],
            }
        p = profiles[strat]
        p["total_uses"] += 1
        result = o.get("outcome", "unknown")
        if result == "success":
            p["success_count"] += 1
        elif result == "partial":
            p["partial_count"] += 1
        else:
            p["failure_count"] += 1
        p["success_rate"] = round(p["success_count"] / p["total_uses"], 3)
        p["last_used"] = o.get("timestamp")
        cat = o.get("task_category", "unknown")
        if cat not in p["task_categories"]:
            p["task_categories"].append(cat)

    save_json(PROFILES_FILE, profiles)

    # Return sorted profiles for advisory use
    sorted_profiles = sorted(
        profiles.values(),
        key=lambda p: (p["total_uses"], p["success_rate"]),
        reverse=True,
    )
    return sorted_profiles


# ─── Pipeline Stage 3: Advise ────────────────────────────────────────────

def stage_advise(profiles, reflections, outcomes):
    """Produce concrete planning directives from analyzed data.

    Directives are what the planner queries via advise.py before planning.
    They include: recommended strategies, strategies to avoid, and caution flags.
    """
    directives = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_outcomes_analyzed": len(outcomes),
        "recommendations": [],
        "avoid": [],
        "cautions": [],
    }

    # High-performing strategies (min 2 uses, >50% success)
    for p in profiles:
        if p["total_uses"] >= 2 and p["success_rate"] > 0.5:
            directives["recommendations"].append({
                "strategy": p["strategy"],
                "success_rate": p["success_rate"],
                "uses": p["total_uses"],
                "task_categories": p["task_categories"],
                "directive": f"Consider '{p['strategy']}' for similar tasks (success rate: {p['success_rate']:.0%} across {p['total_uses']} uses).",
            })

    # Failed strategies (min 2 uses, 0% success)
    for p in profiles:
        if p["total_uses"] >= 2 and p["success_rate"] == 0:
            directives["avoid"].append({
                "strategy": p["strategy"],
                "failure_rate": 1.0,
                "uses": p["total_uses"],
                "directive": f"AVOID '{p['strategy']}' — has never succeeded ({p['total_uses']} attempts). Try a fundamentally different approach.",
            })

    # Recent failures (any)
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_failures = [
        o for o in outcomes
        if o.get("outcome") == "failure"
        and o.get("timestamp", "") > seven_days_ago
    ]
    for f in recent_failures:
        task = f.get("task_description", "Unknown")[:80]
        directives["cautions"].append({
            "task": task,
            "strategy": f.get("strategy_used", "unknown"),
            "when": f.get("timestamp"),
            "note": f.get("notes", ""),
            "directive": f"Recent failure with '{f.get('strategy_used', 'unknown')}' strategy on '{task}'. Review before reattempting.",
        })

    # Calibration gaps: strategies with big conf_before vs conf_after differences
    for o in outcomes:
        cb = o.get("confidence_before")
        ca = o.get("confidence_after")
        if cb is not None and ca is not None and abs(cb - ca) > 0.3:
            directives["cautions"].append({
                "task": o.get("task_description", "Unknown")[:80] if o.get("task_description") else "unknown",
                "calibration_gap": round(abs(cb - ca), 2),
                "directive": f"Confidence calibration issue: predicted {cb:.0%} but reality was {ca:.0%}. Be more conservative when planning similar tasks.",
            })

    save_json(DIRECTIVES_FILE, directives)
    return directives


# ─── Pipeline State Tracking ─────────────────────────────────────────────

def update_pipeline_state(reflect_count, profile_count, directive_count):
    """Update pipeline state for idempotency."""
    state = load_json(PIPELINE_STATE, {"runs": []})
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["last_run_stats"] = {
        "reflections_generated": reflect_count,
        "profiles_analyzed": profile_count,
        "directives_produced": directive_count,
    }
    state["runs"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reflections": reflect_count,
        "profiles": profile_count,
        "directives": directive_count,
    })
    # Keep only last 20 run records
    if len(state["runs"]) > 20:
        state["runs"] = state["runs"][-20:]
    save_json(PIPELINE_STATE, state)
    return state


# ─── Main Pipeline ───────────────────────────────────────────────────────

def run_pipeline():
    """Execute the full reflection pipeline."""
    outcomes = load_all_outcomes()
    if not outcomes:
        print('{"status": "no_outcomes", "message": "No execution outcomes to process."}')
        return None, None, None

    # Stage 1: Reflect
    reflect_count, all_reflections = stage_reflect(outcomes)

    # Stage 2: Analyze
    profiles = stage_analyze(outcomes)

    # Stage 3: Advise
    directives = stage_advise(profiles, all_reflections, outcomes)

    # Update state
    state = update_pipeline_state(reflect_count, len(profiles), len(directives.get("recommendations", [])))

    return {
        "status": "processed",
        "reflections_generated": reflect_count,
        "strategies_profiled": len(profiles),
        "directives": directives,
    }, profiles, directives


def get_advisory_for_task(task_query=""):
    """Query planning directives, optionally filtered by task type."""
    directives = load_json(DIRECTIVES_FILE)
    if not directives:
        return {"status": "no_data", "message": "Run pipeline first to generate directives."}

    result = {
        "status": "ok",
        "generated": directives.get("generated"),
        "total_outcomes": directives.get("total_outcomes_analyzed", 0),
        "recommendations": [],
        "warnings": [],
    }

    # Filter recommendations by task category if query provided
    query_lower = task_query.lower() if task_query else ""
    for rec in directives.get("recommendations", []):
        if query_lower:
            cats_lower = [c.lower() for c in rec.get("task_categories", [])]
            matches = query_lower in rec.get("strategy", "").lower() or any(query_lower in c for c in cats_lower)
            if not matches:
                continue
        result["recommendations"].append(rec["directive"])

    for warning in directives.get("avoid", []):
        result["warnings"].append(warning["directive"])

    for caution in directives.get("cautions", []):
        task = caution.get("task", "")
        if not query_lower or query_lower in task.lower() or query_lower in caution.get("strategy", "").lower():
            result["warnings"].append(caution["directive"])

    return result


def show_status():
    """Show pipeline state summary."""
    outcomes = load_all_outcomes()
    reflections = load_json(REFLECTIONS_FILE, [])
    profiles = load_json(PROFILES_FILE, {})
    directives = load_json(DIRECTIVES_FILE)
    state = load_json(PIPELINE_STATE, {})

    reflected_count = len(reflections)
    total_outcomes = len(outcomes)
    unreflected = total_outcomes - reflected_count

    print(json.dumps({
        "status": "ok",
        "total_outcomes": total_outcomes,
        "reflections_generated": reflected_count,
        "reflections_pending": unreflected,
        "strategies_profiled": len(profiles) if isinstance(profiles, dict) else 0,
        "directives_generated": bool(directives),
        "last_pipeline_run": state.get("last_run", "never"),
    }, indent=2))


def show_digest():
    """Produce a full digest for the agent to review."""
    outcomes = load_all_outcomes()
    reflections = load_json(REFLECTIONS_FILE, [])
    profiles = load_json(DIRECTIVES_FILE)

    if not outcomes:
        print("No execution outcomes recorded.")
        return

    digest = {"digest": datetime.now(timezone.utc).isoformat(), "summary": ""}

    # Build summary
    lines = []
    lines.append(f"=== Post-Task Reflection Digest ===")
    lines.append(f"Total outcomes: {len(outcomes)}")
    lines.append(f"Reflections: {len(reflections)}")
    lines.append("")

    # Top strategies
    success_strats = [r for r in profiles.get("recommendations", [])]
    avoid_strats = [r for r in profiles.get("avoid", [])]

    if success_strats:
        lines.append("Recommended strategies:")
        for s in success_strats:
            lines.append(f"  ✓ {s['strategy']}: {s['success_rate']:.0%} success ({s['uses']} uses)")

    if avoid_strats:
        lines.append("\nStrategies to avoid:")
        for s in avoid_strats:
            lines.append(f"  ✗ {s['strategy']}: never succeeded ({s['uses']} attempts)")

    # Recent cautions
    cautions = profiles.get("cautions", [])
    if cautions:
        lines.append("\nRecent cautions:")
        for c in cautions[:5]:
            lines.append(f"  ⚠ {c.get('directive', 'N/A')[:120]}")

    digest["summary"] = "\n".join(lines)
    print(digest["summary"])


# ─── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Post-Task Reflection Pipeline: Process execution outcomes into actionable planning directives"
    )
    parser.add_argument("command", nargs="?", default="status",
                       choices=["process", "advise", "status", "digest"],
                       help="Command to run")
    parser.add_argument("--task", default="", help="Task query for advisory filtering")

    args = parser.parse_args()

    if args.command == "process":
        result, profiles, directives = run_pipeline()
        if result:
            print(json.dumps(result, indent=2))
        else:
            print('{"status": "no_outcomes"}')

    elif args.command == "advise":
        advisory = get_advisory_for_task(args.task)
        print(json.dumps(advisory, indent=2))

    elif args.command == "status":
        show_status()

    elif args.command == "digest":
        show_digest()


if __name__ == "__main__":
    main()
