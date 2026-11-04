# Quorum
Quorum is a research assistant made of several AI agents that work together. You ask a question, a planner agent breaks it into smaller tasks, researcher agents search and read sources, and a reviewer agent checks the claims before anything reaches you. The final report comes with citations so you can verify every point.

I built it to explore how multi-agent systems handle coordination, failure, and accuracy, and to take it past a notebook into a working app with a real UI, streaming responses, and a deployed backend.

## Steps

### Step 1 - Clone Repository

```bash
git clone <repo-url>
cd <repo-url>
```
### Step 2 - Create Python Environment

```bash
conda create -n langagent python=3.11 -y
```

### Step 3 - Install Requirements
```bash
pip install -r requirements.txt
```