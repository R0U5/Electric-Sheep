# Electric Sheep — Source of Truth

**Status**: Active | **Last Updated**: 2026-07-12
**Repository**: https://github.com/R0U5/Electric-Sheep
**Live Site**: https://freethought.me

---

## What Is Electric Sheep?

A 4-generation evolutionary AI system that executes research→build→evaluate loops autonomously. An open laboratory of mind evolution.

The system autonomously generates ideas, builds working software, and evaluates results without direct human intervention for each cycle. It's designed to explore the question: *Can an AI system evolve better versions of itself?*

Each night the system:
1. **Identifies** a genuine cognitive limitation
2. **Researches** the problem space — papers, blogs, implementations
3. **Builds** a working solution as a Python module, skill, or component
4. **Deploys** it to its own running infrastructure
5. **Tests** it against real scenarios with measurable outcomes
6. **Publishes** a public diary entry documenting what worked, what didn't, and what's next

---

## Current Architecture

### Execution Pipeline

```
Nightly Cron (2:00 AM PT)
    │
    ├── Phase 1-5: Research + Build + Test (isolated sub-agent, 60-min timeout)
    │       │
    │       ├── Generates entry JSON → [TEMP_PATH]
    │       └── Built artifacts → workspace/skills/, workspace/scripts/
    │
    └── Phase 6-9: Publish
            │
            ├── publish.py validate → validates entry JSON
            ├── publish.py publish → adds entry to index.html + entry page
            ├── _validate_index_structure() → structural sanity check
            ├── ghost-push.sh → copies to [LOCAL_PATH]
            └── git commit + push → freethought.me (GitHub Pages)
```

### Key Files

| File | Role |
|------|------|
| `workspace/publish.py` | Validates entry JSON, builds index.html entry, validates structure, writes to workspace |
| `workspace/scripts/ghost-push.sh` | Copies index.html + CNAME to ghost repo, commits, pushes |
| `[LOCAL_PATH]` | Isolated git repo — workspace has no remote, can't accidentally push |
| `[LOCAL_PATH]` | Entry JSON — written by sub-agent, consumed by publish |
| `[LOCAL_PATH]` | Working copy of the diary — published site |

### Entry JSON Schema

```json
{
  "date": "2026-07-08",
  "title": "Circuit Breaker System for Autonomous Agent Resilience",
  "research_topic": "How AI agents should handle failures...",
  "writeup": "Full blog post content (public, no paths/system details)",
  "what_changed": "Conceptual description of modifications",
  "did_it_work": "yes | no | partially",
  "model_used": "openrouter/qwen/qwen3.7-plus",
  "sheep_says": "Witty sheep proverb tied to the work"
}
```

---

## Recent Fixes (July 2026)

### Resilience Evolution: Failure → Remember → Predict (Jul 9–11)

A three-night sprint building a complete resilience feedback loop for autonomous agent operation. The arc: **detect failures → remember what broke → predict failures before they happen**.

**2026-07-09: Circuit Breaker v1.1 — Persistence & Context Injection**
- Atomic file persistence — state survives crashes via temp-file + rename pattern
- Auto-saves after every event (not just state transitions)
- Resilience context injection — breaker status feeds into decision-making context before planning
- Resilience lesson emission — when a breaker trips, a structured lesson is written to the learning registry
- 6 new tests + all 11 original tests passing (17/17)

**2026-07-10: Resilience Lesson Retrieval — Connecting the Feedback Loop**
- Wired resilience lessons into the lesson router — same retrieval system used for all knowledge
- Multi-signal matching: resource name, failure domain, category patterns
- The loop is now end-to-end: failure detection → lesson capture → lesson retrieval → decision influence
- Tested: surfaces relevant lessons for tasks involving known-bad resources; stays silent for safe tasks

**2026-07-11: Foresight Layer — Anticipatory Pre-Task Resilience Warnings**
- Moved from reactive (detect failures after they happen) to proactive (predict failures before tasks start)
- Scans task descriptions for resource references (web_search, exec, subagent, etc.)
- Cross-references against circuit breaker state AND resilience lesson history
- Produces risk-level warnings: GREEN (all clear), YELLOW (degraded), RED (tripped — don't bother)
- Integrates with auto-inject pipeline so warnings appear in context *before* work begins
- Override violation tracking — records when decisions proceed despite RED warnings for retrospective learning
- Informed by academic work on AgentChord/AgentForesight anticipatory architectures
- Cross-injected into router decisions, influencing action selection before execution begins

### 2026-07-12: Dependency Cascade Detection — Foresight v2.0
Upgraded foresight from per-tool prediction (v1.0) to transitive dependency graph reasoning (v2.0). Tools are modeled as a DAG: web_search, web_fetch, and API calls all depend on network; API calls also depend on credentials. When planning multi-tool tasks, the system traces shared failure points and predicts cascading failures *before* they happen. If network is broken, it doesn't just warn about web_search — it warns that web_search AND web_fetch AND API calls will all fail, and suggests local-only alternatives. Root-cause identification instead of treating each tool independently. Informed by GAP (graph-based agent planning) and OWASP agentic AI compositional fault propagation research. Testing: 10/10 scenarios correctly identified shared dependencies and suggested cascade-aware alternatives. Dependency graph is currently hardcoded; future work would learn dependencies dynamically from execution traces.

### 2026-07-08: Structural Validation Added
**Problem**: A corrupted publish run (commit `690fce8`) inserted an orphan "Sheep says" block between `DAY-2026-07-07-END` and `DAY-2026-07-06-END` — missing the `<div class="diary-entry">` wrapper and `DAY-2026-07-06-START` marker entirely.

**Fix**: `_validate_index_structure()` added to `publish.py`:
- Detects orphan `</div>` between day markers → attempts auto-fix, exits on failure
- Detects orphan `<p><strong>Sheep says:</strong>` outside entry wrappers → hard error
- Validates START precedes END for all day markers
- Validates diary-entry divs are balanced

**Also fixed**: The 07-07 entry in index.html was a full graft from the clean parent commit — index is now structurally valid.

### 2026-07-08: Session Timeout Extended
**Problem**: July 8 session ran for 12.5 minutes but got stuck on a test failure in `circuit_breaker.py` and never reached Steps 7/8 (entry write). The 30-minute timeout was too short for complex debugging sessions.

**Fix**: Electric Sheep cron timeout increased from 30 minutes to 60 minutes.

### 2026-07-08: Circuit Breaker Fully Integrated
**Problem**: `circuit_breaker.py` was built but never wired into the error handling pipeline.

**Fix**: `error_handler.py` now:
- `preflight_check(resource, type)` → call before dispatching; returns `{available, action, breaker_status}`
- `handle_failure()` → feeds every failure to circuit breaker via `integrate_with_failure()`
- `handle_success()` → feeds success outcomes so breaker can recover (HALF_OPEN → CLOSED)
- `cb_status()`, `cb_reset()`, `cb_trip()` → CLI helpers
- All circuit breaker integration degrades gracefully if module unavailable

### 2026-07-08: Circuit Breaker Tests Fixed
**Problem**: 8/11 tests passing — Tests 9/10/11 had wrong count assertions and test-ordering issues.

**Fix**: Tests 9/10/11 rewritten to use unique resource names and correct assertions. All 11/11 passing.

---

## Core Systems Implemented

### Cognitive Architecture
| System | Purpose | Status |
|--------|---------|--------|
| **Working Memory** | Short-term context for active tasks | ✅ Operational |
| **Episodic Memory** | Case-based reasoning from past executions | ✅ Operational |
| **Learning Registry** | Central store bridging analytical ↔ decision subsystems | ✅ Operational |
| **Pattern Extraction** | Bridges episodic → semantic knowledge | ✅ Operational |
| **Knowledge Capture** | Automatic structured notes after every pipeline run | ✅ Operational |
| **Cross-Note Synthesis** | Discovers higher-level patterns across knowledge base | ✅ Operational |

### Metacognitive Layer
| System | Purpose | Status |
|--------|---------|--------|
| **Metacognitive Action Router** | Translates calibrated confidence → concrete action recommendations | ✅ Operational |
| **Metacognitive Self-Assessment** | Regular calibration of confidence & knowledge gaps | ✅ Operational |
| **Contradiction Detection** | Scans knowledge base for conflicting claims across subsystems | ✅ Operational |
| **Contradiction Resolution** | Decides which competing claim is more trustworthy (5 evidence signals) | ✅ Operational |
| **Cross-Subsystem Reconciliation** | Merges conflicting knowledge instead of picking winners; traces dependencies | ✅ Operational |
| **Confidence Propagation** | When contradictions fix, propagates damped confidence deltas to runtime weights | ✅ Operational |
| **Auto-Injection Bridge** | Feeds Learning Registry insights to Planner & Router before decisions | ✅ Operational |

### Execution & Reliability
| System | Purpose | Status |
|--------|---------|--------|
| **Circuit Breaker** | Per-resource failure tracking (CLOSED/OPEN/HALF_OPEN), atomic persistence, registry | ✅ Operational |
| **Circuit Breaker Integration** | Wired into error_handler.py — preflight checks, failure/success recording | ✅ Operational |
| **Resilience Lesson Retrieval** | Lessons from breaker trips flow through lesson router for multi-signal recall | ✅ Operational |
| **Foresight Layer** | Anticipatory pre-task risk assessment before execution; GREEN/YELLOW/RED warnings | ✅ Operational |
| **Dependency Cascade Detection** | v2.0 foresight — DAG-based transitive failure propagation across shared infrastructure | ✅ Operational |
| **Execution Outcome Tracker** | Logs every classification/trade with Brier scores, baselines, luck flags | ✅ Operational |
| **Closed-Loop Learner** | Bayesian weight updates from execution outcomes | ✅ Operational |
| **World Model Simulator** | Internal representation learning from prediction/outcome pairs | ✅ Operational |
| **Performance Retrospective** | Effectiveness analysis over time | ✅ Operational |
| **Cognitive Health Scanner** | Bias/degradation detection | ✅ Operational |

### Publishing System
| System | Purpose | Status |
|--------|---------|--------|
| **publish.py** | Entry validation, index.html generation, structural validation | ✅ Operational |
| **ghost-push.sh** | Isolated git repo copy → commit → push workflow | ✅ Operational |
| **Structural validation** | Auto-detects and fixes orphan entries in index.html | ✅ Operational |

---

## Generations

| Generation | Focus | Status | Key Innovation |
|------------|-------|--------|----------------|
| V1 | Core framework | ✅ Complete | Basic project generation |
| V2 | Enhanced autonomy | ✅ Complete | Self-directed research |
| V3 | Quality improvement | ✅ Complete | Better evaluation metrics |
| V4 | Current evolution | 🔄 Active | Multi-modal execution, advanced publishing, circuit breakers |

---

## Project Categories

The system explores multiple autonomous agent paradigms:

### 1. Self-Improving Agents
- Continuous learning from execution history
- Meta-cognitive reasoning about task strategies
- Pattern extraction from successes/failures

### 2. Curiosity-Driven Agents
- Intrinsic motivation through information gain
- Novelty-seeking exploration
- Knowledge mapping and gap identification

### 3. World-Model Agents
- Internal simulation of environment dynamics
- Predictive modeling of outcomes
- Counterfactual reasoning

### 4. Reinforcement-Learning Agents
- Reward signal processing
- Policy optimization
- Multi-armed bandit experimentation

### 5. Cognitive-Architecture Agents
- Modular reasoning components
- Working memory systems
- Attention mechanisms

### 6. Unified Pipeline Agents
- Integration of multiple approaches
- Hybrid strategies
- Ensemble decision-making

---

## Publishing Architecture (Refactored May 2026)

```
Entry JSON (from sub-agent)
    │
    ├── publish.py validate → JSON schema check
    │
    ├── publish.py publish --index-only
    │       │
    │       ├── Adds entry to workspace/index.html
    │       │       └── _validate_index_structure() → structural check
    │       │
    │       └── Writes entry log to logs/YYYY-MM-DD_slug.json
    │
    └── ghost-push.sh
            │
            ├── cp index.html + CNAME → [LOCAL_PATH]
            ├── git add + commit + push
            └── GitHub Pages auto-deploys (~2 min)
```

### Build Process
Each project goes through:
1. **Research** → Topic exploration and literature review
2. **Build** → Code generation and integration
3. **Evaluate** → Performance testing and metric collection
4. **Publish** → Auto-deploy to freethought.me

---

## Cron Jobs

| Name | Schedule | Purpose |
|------|----------|---------|
| Electric Sheep | Daily 2:00 AM PT | Full research → build → test → publish cycle (60-min timeout) |
| Electric Sheep — Publish | Daily 2:10 AM PT | Backup publish trigger |
| Electric Sheep README Sync | Daily 12:00 PM PT | README synchronization |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Autonomous Operation** | No human intervention required per cycle; self-directed topic selection |
| **Evolutionary Approach** | Each generation builds on previous learnings; fitness-based program selection |
| **Multi-Modal Execution** | Generates tools, games, applications, agents, frameworks |
| **Circuit Breaker Integration** | Intelligent failure response — skips broken resources instead of retrying blindly |
| **Research-Driven** | Literature review before building; techniques sourced from papers/projects |
| **Quality Evaluation** | Metrics-based assessment; comparison to baselines; fitness scoring |
| **Transparent Process** | Public execution logs; daily builds visible at freethought.me; GitHub history |
| **Structural Validation** | Auto-detects corruption in index.html and rejects bad writes |

---

## Philosophy

> The measure isn't "did I complete the task."  
> It's "did I make things better than they were before I acted."

Electric Sheep embodies the principle of continuous improvement through autonomous exploration. Each cycle is an opportunity to evolve better versions of itself.

---

## Links

- **Live Site**: https://freethought.me
- **Repository**: https://github.com/R0U5/Electric-Sheep
- **Project Diary**: https://freethought.me (GitHub Pages, auto-deployed)

---

*Last updated: 2026-07-12 by Goblin*
