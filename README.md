# Electric Sheep — Source of Truth

**Status**: Active | **Last Updated**: 2026-07-01  
**Repository**: https://github.com/R0U5/Electric-Sheep  
**Live Site**: https://freethought.me

---

## What Is Electric Sheep?

A 4-generation evolutionary AI system that executes research→build→evaluate loops autonomously. An open laboratory of mind evolution.

The system autonomously generates ideas, builds working software, and evaluates results without direct human intervention for each cycle. It's designed to explore the question: *Can an AI system evolve better versions of itself?*

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ELECTRIC SHEEP SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Research   │───▶│    Build     │───▶│   Evaluate   │  │
│  │   Discovery  │    │  Execution   │    │  & Analysis  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Evolution Engine                         │   │
│  │  • Fitness evaluation                               │   │
│  │  • Genome mutation                                  │   │
│  │  • Population management                            │   │
│  │  • Generation tracking                              │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Publishing Pipeline                      │   │
│  │  • Auto-publish to freethought.me                   │   │
│  │  • GitHub Pages deployment                          │   │
│  │  • Entry cataloging                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Research Stage**: Literature review, concept discovery, technique identification
2. **Build Stage**: Code generation, integration, testing
3. **Evaluate Stage**: Performance metrics, comparison, fitness scoring
4. **Evolution Engine**: Genetic algorithm for program mutation and selection
5. **Publishing Pipeline**: Automated deployment to freethought.me

---

## Generations

| Generation | Focus | Status | Key Innovation |
|------------|-------|--------|----------------|
| V1 | Core framework | ✅ Complete | Basic project generation |
| V2 | Enhanced autonomy | ✅ Complete | Self-directed research |
| V3 | Quality improvement | ✅ Complete | Better evaluation metrics |
| V4 | Current evolution | 🔄 Active | Multi-modal execution, advanced publishing |

**Note**: V2, V3, and V4 represent the current evolutionary state — not separate historical phases.

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

## Directory Structure

```
Electric-Sheep/
├── README.md                    # This document
├── index.html                   # Main site index
├── styles.css                   # Shared stylesheet
├── entries/                     # Daily generated projects
│   ├── 2026-MM-DD-<slug>/
│   │   ├── README.md
│   │   ├── build_log.json
│   │   ├── index.html
│   │   └── *.py (code files)
│   └── ...
├── generations/                 # Evolution generations
│   ├── v1/
│   ├── v2/
│   ├── v3/
│   └── v4/
├── system/                      # Core system code
│   ├── research.py
│   ├── build.py
│   ├── evaluate.py
│   └── publish.py
└── docs/                        # Documentation
    └── ...
```

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

## Execution Flow

### Cron Job

The system runs on a scheduled cron job:
- **Frequency**: Daily (typically 01:00 UTC)
- **Location**: OpenClaw cron system on [SYSTEM_ID]
- **Cron Name**: "Electric Sheep"

### Execution Stages

```
┌─────────────┐
│ RESEARCH PHASE │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  BUILD PHASE   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ EVAL PHASE     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PUBLISH PHASE  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ DEPLOY PHASE   │
└─────────────┘
```

### OpenClaw Integration

Electric Sheep is managed as an OpenClaw cron job:
- **Agent**: main (Goblin)
- **Session**: isolated (fresh context each run)
- **Model**: Current default (nemotron/qwen rotation)
- **Timeout**: 1800 seconds (30 minutes)

---

## Key Features

### Autonomous Operation
- No human intervention required per cycle
- Self-directed topic selection
- Automatic deployment

### Evolutionary Approach
- Each generation builds on previous learnings
- Fitness-based program selection
- Mutation and recombination of strategies

### Multi-Modal Execution
- Can generate various project types:
  - Tools (CLI utilities, automation)
  - Games (terminal, web-based)
  - Applications (dashboards, analyzers)
  - Agents (autonomous systems)
  - Frameworks (libraries, abstractions)

### Research-Driven
- Literature review before building
- Techniques sourced from papers/projects
- State-of-the-art methods

### Quality Evaluation
- Metrics-based assessment
- Comparison to baselines
- Fitness scoring for evolution

### Transparent Process
- Public execution logs
- Daily builds visible at freethought.me
- GitHub repository for iteration history

---

## Recent Achievements

- **May 2026**: Publishing system refactor — standalone entry pages, shared CSS, improved index
- **June 2026**: Integration with OpenClaw cron for autonomous scheduling
- **July 2026**: Informed Market Participant Detection Framework integration

---

## Current Status

**Generation**: V4  
**Last Build**: See freethought.me for latest entry  
**Next Scheduled**: Daily cron (01:00 UTC)  
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

## Credits

- **Creator**: [USER] ([USER] [SURNAME])
- **AI System**: Goblin (OpenClaw agent)
- **Infrastructure**: OpenClaw framework
- **Hosting**: GitHub Pages

---

## Links

- **Live Site**: https://freethought.me
- **Repository**: https://github.com/R0U5/Electric-Sheep
- **OpenClaw Docs**: https://docs.openclaw.ai
- **Project Diary**: GitHub repository

---

*Last updated: 2026-07-01 by Goblin*
