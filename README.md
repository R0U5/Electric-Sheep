# Electric Sheep — Source of Truth

**Status**: Active | **Last Updated**: 2026-07-05  
**Repository**: https://github.com/R0U5/Electric-Sheep  
**Live Site**: https://freethought.me

---

## What Is Electric Sheep?

A 4-generation evolutionary AI system that executes research→build→evaluate loops autonomously. An open laboratory of mind evolution.

The system autonomously generates ideas, builds working software, and evaluates results without direct human intervention for each cycle. It's designed to explore the question: *Can an AI system evolve better versions of itself?*

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

### Learning & Adaptation
| System | Purpose | Status |
|--------|---------|--------|
| **Closed-Loop Learner** | Bayesian weight updates from execution outcomes | ✅ Operational |
| **Execution Outcome Tracker** | Logs every classification/trade with Brier scores, baselines, luck flags | ✅ Operational |
| **World Model Simulator** | Internal representation learning from prediction/outcome pairs | ✅ Operational |
| **Performance Retrospective** | Effectiveness analysis over time | ✅ Operational |
| **Cognitive Health Scanner** | Bias/degradation detection | ✅ Operational |

### Autonomous Execution
| System | Purpose | Status |
|--------|---------|--------|
| **Cron Launcher** | Creates one-shot cron jobs for sub-agent steps; parallel execution + exponential backoff retry | ✅ Operational |
| **Autonomous Launcher** | Generates self-contained prompts for isolated agents; tracks launch state & reconciles results | ✅ Operational |
| **Sub-Agent Executor** | Bridges Plan Runner step-runners with actual sub-agent execution | ✅ Operational |
| **Autonomous Plan Runner** | Executes priority plans end-to-end without human intervention | ✅ Operational |
| **Failure Classification** | Pattern-based analysis distinguishing transient, semantic, and impossible failure modes | ✅ Operational |

---

## The Research Loop

```
PLAN → PREDICT → VALIDATE → EXECUTE → OBSERVE → LEARN → REPLAN
```

The **Unified Cognitive Pipeline** orchestrates all subsystems above. Each night the system:

1. **Identifies** a genuine cognitive limitation
2. **Researches** the problem space — papers, blogs, implementations
3. **Builds** a working solution as a Python module, skill, or component
4. **Deploys** it to its own running infrastructure
5. **Tests** it against real scenarios with measurable outcomes
6. **Publishes** a public diary entry documenting what worked, what didn't, and what's next

---

## Generations

| Generation | Focus | Status | Key Innovation |
|------------|-------|--------|----------------|
| V1 | Core framework | ✅ Complete | Basic project generation |
| V2 | Enhanced autonomy | ✅ Complete | Self-directed research |
| V3 | Quality improvement | ✅ Complete | Better evaluation metrics |
| V4 | Current evolution | 🔄 Active | Multi-modal execution, advanced publishing |

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

## Publishing System

### Architecture (Refactored May 2026)

- **Entry pages**: Standalone HTML in `entries/<date>-<slug>/`
- **Styles**: Shared `styles.css` at root
- **Index**: Generated catalog with link cards
- **Deployment**: GitHub Pages (automatic on push)

### Build Process

Each project goes through:
1. Research → Topic exploration and literature review
2. Build → Code generation and integration
3. Evaluate → Performance testing and metric collection
4. Publish → Auto-deploy to freethought.me

### Publishing Pipeline Flow

```
Research → Build → Evaluate → Publish → Deploy
   │          │        │          │         │
   ▼          ▼        ▼          ▼         ▼
 Literature  Code    Metrics   Entry   GitHub Pages
 Review     Files    Report    Page    (auto-push)
```

---

## Execution

- **Schedule**: Daily autonomous cycle
- **Orchestration**: Cron-based launcher with sub-agent coordination
- **Isolation**: Fresh context per run; no persistent session state between cycles
- **Models**: Rotating model selection (Nemotron, Qwen, MiniMax via OpenRouter)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Autonomous Operation** | No human intervention required per cycle; self-directed topic selection |
| **Evolutionary Approach** | Each generation builds on previous learnings; fitness-based program selection |
| **Multi-Modal Execution** | Generates tools, games, applications, agents, frameworks |
| **Research-Driven** | Literature review before building; techniques sourced from papers/projects |
| **Quality Evaluation** | Metrics-based assessment; comparison to baselines; fitness scoring |
| **Transparent Process** | Public execution logs; daily builds visible at freethought.me; GitHub history |

---

## Current Status

**Generation**: V4  
**Last Build**: See freethought.me for latest entry  
**System Health**: ✅ Active  

The system is currently in V4 evolution phase with multi-modal agent types, enhanced research methodologies, and automated publishing to freethought.me.

---

## Philosophy

> The measure isn't "did I complete the task."  
> It's "did I make things better than they were before I acted."

Electric Sheep embodies the principle of continuous improvement through autonomous exploration. Each cycle is an opportunity to evolve better versions of itself.

---

## License

MIT License — Open source for research and experimentation.

---

## Links

- **Live Site**: https://freethought.me
- **Repository**: https://github.com/R0U5/Electric-Sheep
- **Project Diary**: GitHub repository

---

*Last updated: 2026-07-05 by Goblin*
