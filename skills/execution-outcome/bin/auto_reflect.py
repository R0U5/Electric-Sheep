#!/usr/bin/env python3
"""Auto-reflection engine: bridges execution outcomes to case-based planning and self-improving.

This is the missing link in the cognitive architecture. After every significant
execution, this tool:
1. Captures the outcome automatically (or prompts the agent to score it)
2. Generates a verbal reflection on what happened and why
3. Stores reflection + outcome in both execution-outcome data and self-improving archives
4. Updates case-based planner adaptation records when applicable
5. Flags patterns that need deeper review

Usage (called by the agent after executing a plan):
    python3 auto_reflect.py --plan-id "plan-xyz" --steps "read,exec,write" --outcome "partial"
    python3 auto_reflect.py --task "What I was trying to do" --strategy "How I did it" --outcome "success" --tools "read exec write" --time 45

The agent evaluates outcome honestly:
    SUCCESS = completed goal, verified result correct
    PARTIAL = made progress but didn't fully achieve goal, or result needs verification
    FAILURE = did not achieve goal, result was wrong, or execution blocked

Resolves bin/data paths relative to skill directory.
"""

import argparse
import json
import os
import sys
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = SCRIPTS_DIR.parent
DATA_DIR = SKILL_DIR / "data"
SELF_IMPROVING_DIR = Path(os.path.expanduser("~/.openclaw/workspace")) / "skills" / "self-improving"
ADAPTATION_DIR = Path(os.path.expanduser("~/.openclaw/workspace")) / "adaptation-tracking"

OUTCOMES_FILE = DATA_DIR / "outcomes.json"
PROFILES_FILE = DATA_DIR / "strategy_profiles.json"
REFLECTIONS_AUTO_FILE = DATA_DIR / "auto_reflections.json"
REFLECTIONS_SKILL_FILE = SELF_IMPROVING_DIR / "reflections.md"
ADAPTATIONS_FILE = Path(os.path.expanduser("~/.openclaw/workspace")) / "skills" / "case-based-planner" / "adaptations.json"
ADAPTATION_LOG = ADAPTATION_DIR / "effectiveness_log.json"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SELF_IMPROVING_DIR.mkdir(parents=True, exist_ok=True)
    ADAPTATION_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path, default=None):
    if default is None:
        default = [] if str(path).endswith(('.json',)) and 'reflections' not in str(path).lower() else []
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content) if not str(path).endswith('.md') else default
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def outcome_quality_reflection(outcome, strategy, task, notes="", tools=None):
    """Generate a reflection on the outcome — based on Reflexion framework principles.

    Reflexion (Shinn et al.) showed that agents which verbally reflect on outcomes
    and store those reflections see 20%+ accuracy gains. Key: reflection must be
    specific, honest, and stored for future retrieval.
    """
    reflections = []

    if outcome == "success":
        reflections.append(f"SUCCESS: {strategy} worked for {task}.")
        reflections.append(f"This approach should be preferred for similar tasks in this category.")
        if notes:
            reflections.append(f"Additional note: {notes}")
    elif outcome == "partial":
        reflections.append(f"PARTIAL: {strategy} got partway through {task} but didn't fully succeed.")
        reflections.append(f"Next time on similar tasks: identify the missing piece upfront rather than discovering it mid-execution.")
        if notes:
            reflections.append(f"What went wrong: {notes}")
    else:  # failure
        reflections.append(f"FAILURE: {strategy} did not work for {task}.")
        reflections.append(f"Critical: do NOT retry the same approach without modification.")
        reflections.append(f"Root cause analysis needed before attempting again.")
        if notes:
            reflections.append(f"Failure context: {notes}")

    return " ".join(reflections)


def pattern_check(outcomes_list, current_task, current_strategy):
    """Check if there's a pattern of repeated failures or partials on similar tasks."""
    if len(outcomes_list) < 3:
        return None

    recent = [o for o in outcomes_list[-10:] if current_task.lower() in o.get("task_description", "").lower()
              or current_strategy.lower() in o.get("strategy_used", "").lower()]

    if len(recent) >= 2:
        failures = sum(1 for r in recent if r.get("outcome") in ("failure", "partial"))
        if failures >= len(recent) * 0.5:
            return {
                "flag": "repeated_difficulty",
                "count": len(recent),
                "failure_rate": round(failures / len(recent), 2),
                "recommendation": "This task pattern has struggled before. Consider a different approach or ask for input before proceeding.",
            }
    return None


def record_outcome(task, strategy, outcome, category="other", tools=None,
                   notes="", time_s=None, plan_id=None, conf_before=None, conf_after=None):
    """Record the outcome and generate reflection."""
    ensure_dirs()

    outcomes = load_json(OUTCOMES_FILE, [])
    reflections = load_json(REFLECTIONS_AUTO_FILE, [])

    # 1. Record outcome
    outcome_record = {
        "id": f"outcome-{uuid.uuid4().hex[:12]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_category": category,
        "task_description": task,
        "strategy_used": strategy,
        "tools_involved": tools or [],
        "outcome": outcome,
        "confidence_before": conf_before,
        "confidence_after": conf_after,
        "execution_time_s": time_s,
        "notes": notes or "",
        "plan_id": plan_id,
        "auto_captured": True,
    }
    outcomes.append(outcome_record)
    save_json(OUTCOMES_FILE, outcomes)

    # 2. Generate reflection (Reflexion-style)
    reflection_text = outcome_quality_reflection(outcome, strategy, task, notes, tools)
    reflection_record = {
        "id": f"reflect-{uuid.uuid4().hex[:12]}",
        "timestamp": outcome_record["timestamp"],
        "outcome_id": outcome_record["id"],
        "task": task,
        "strategy": strategy,
        "outcome": outcome,
        "reflection": reflection_text,
        "auto_generated": True,
    }
    reflections.append(reflection_record)
    save_json(REFLECTIONS_AUTO_FILE, reflections)

    # Keep auto-reflections to last 100 entries
    if len(reflections) > 100:
        reflections = reflections[-100:]
        save_json(REFLECTIONS_AUTO_FILE, reflections)

    # 3. Check for concerning patterns
    pattern = pattern_check(outcomes, task, strategy)

    # 4. Update strategy profiles
    _update_profiles(outcomes)

    # 4b. Update planning directives via reflection pipeline
    _update_planning_directives(outcomes)

    # 5. Output for the agent
    result = {
        "status": "captured",
        "outcome_id": outcome_record["id"],
        "reflection_id": reflection_record["id"],
        "reflection": reflection_text,
        "total_outcomes_recorded": len(outcomes),
        "total_reflections_recorded": len(reflections),
    }
    if pattern:
        result["pattern_alert"] = pattern

    print(json.dumps(result, indent=2))
    return result


def _update_profiles(outcomes):
    """Update strategy profiles from outcome data."""
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
                "success_rate": 0,
                "last_used": None,
            }
        p = profiles[strat]
        p["total_uses"] += 1
        out = o.get("outcome", "unknown")
        if out == "success":
            p["success_count"] += 1
        elif out == "partial":
            p["partial_count"] += 1
        else:
            p["failure_count"] += 1
        p["success_rate"] = round(p["success_count"] / p["total_uses"], 3) if p["total_uses"] > 0 else 0
        p["last_used"] = o.get("timestamp")

    save_json(PROFILES_FILE, profiles)
    return profiles


def _update_planning_directives(outcomes):
    """After recording an outcome, update planning directives so the next plan
    benefits from this result. Lightweight inline version of reflection_pipeline's
    stage_analyze + stage_advise. Full batch processing via reflection_pipeline.py process."""
    # Build profiles (same logic as stage_analyze)
    profiles = _update_profiles(outcomes)

    # Quick directives
    recommendations = []
    avoid = []
    for strat, p in profiles.items():
        if p["total_uses"] >= 2 and p["success_rate"] > 0.5:
            recommendations.append({
                "strategy": strat,
                "success_rate": p["success_rate"],
                "uses": p["total_uses"],
                "directive": f"Consider '{strat}' for similar tasks (success rate: {p['success_rate']:.0%}).",
            })
        elif p["total_uses"] >= 2 and p["success_rate"] == 0:
            avoid.append({
                "strategy": strat,
                "uses": p["total_uses"],
                "directive": f"AVOID '{strat}' — never succeeded in {p['total_uses']} attempts.",
            })

    DIRECTIVES = DATA_DIR / "planning_directives.json"
    directives = load_json(DIRECTIVES, {
        "generated": "",
        "total_outcomes_analyzed": 0,
        "recommendations": [],
        "avoid": [],
        "cautions": [],
    })

    directives["recommendations"] = recommendations
    directives["avoid"] = avoid
    directives["generated"] = datetime.now(timezone.utc).isoformat()
    directives["total_outcomes_analyzed"] = len(outcomes)

    latest = outcomes[-1] if outcomes else None
    if latest and latest.get("outcome") == "failure":
        caution = {
            "task": latest.get("task_description", "Unknown")[:80],
            "strategy": latest.get("strategy_used", "unknown"),
            "when": latest.get("timestamp"),
            "note": latest.get("notes", ""),
            "directive": f"Recent failure with '{latest.get('strategy_used', 'unknown')}' on '{latest.get('task_description', 'Unknown')[:80]}'. Review before reattempting.",
        }
        directives.setdefault("cautions", []).append(caution)
        if len(directives["cautions"]) > 10:
            directives["cautions"] = directives["cautions"][-10:]

    save_json(DIRECTIVES, directives)
    return directives


def get_recent_reflections(limit=10):
    """Return most recent reflections for the agent to review."""
    reflections = load_json(REFLECTIONS_AUTO_FILE, [])
    return reflections[-limit:]


def main():
    parser = argparse.ArgumentParser(description="Auto-capture execution outcomes with Reflexion-style reflection")
    parser.add_argument("--task", default=None, help="What you were trying to do")
    parser.add_argument("--strategy", default=None, help="How you attempted it")
    parser.add_argument("--outcome", default=None, choices=["success", "partial", "failure"], help="Honest result")
    parser.add_argument("--category", default="other", help="Task category (auto-detect: research/code/config/debugging/creative/memory/planning)")
    parser.add_argument("--tools", nargs="*", default=[], help="Tools used")
    parser.add_argument("--notes", default="", help="What went well or what went wrong")
    parser.add_argument("--time", type=int, default=None, help="Execution time in seconds")
    parser.add_argument("--plan-id", default=None, help="Associated plan ID")
    parser.add_argument("--conf-before", type=float, default=None, help="Confidence before (0-1)")
    parser.add_argument("--conf-after", type=float, default=None, help="Confidence after (0-1)")
    parser.add_argument("--recent", action="store_true", help="Show recent reflections instead of recording")

    args = parser.parse_args()

    if args.recent:
        refs = get_recent_reflections()
        print(json.dumps(refs, indent=2))
        return

    if not args.task or not args.strategy or not args.outcome:
        print('Error: --task, --strategy, and --outcome are required unless --recent is used', file=sys.stderr)
        sys.exit(1)

    record_outcome(
        task=args.task,
        strategy=args.strategy,
        outcome=args.outcome,
        category=args.category,
        tools=args.tools,
        notes=args.notes,
        time_s=args.time,
        plan_id=args.plan_id,
        conf_before=args.conf_before,
        conf_after=args.conf_after,
    )


if __name__ == "__main__":
    main()
