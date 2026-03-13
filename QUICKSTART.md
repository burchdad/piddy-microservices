# Piddy Growth Repository - Quick Start Guide

## 🚀 Quick Setup

```bash
# Clone the growth repo alongside main Piddy
cd /workspaces
git clone <piddy-growth-repo-url> piddy-growth
cd piddy-growth

# Verify structure
ls -la
```

## 📊 Using the Growth Manager

### Python Integration

```python
from piddy_growth_manager import PiddyGrowthManager

# Initialize manager
manager = PiddyGrowthManager("/workspaces/piddy-growth")

# Log session learnings
insights = {
    "insights": [
        "Pattern discovered about error handling",
        "Performance improvement found in caching"
    ],
    "metrics": {
        "tasks_completed": 42,
        "success_rate": 0.96
    },
    "recommendations": [
        "Implement this pattern in main codebase",
        "Create documentation for other agents"
    ]
}
manager.log_session_learning("session-001", insights)

# Record an experiment
manager.record_experiment(
    "feature-x-optimization",
    "Testing new approach to feature X",
    "In Progress"
)

# Document a pattern
manager.record_pattern(
    "circuit-breaker-pattern",
    "Resilience",
    "Implement circuit breaker for API calls to prevent cascading failures"
)

# Auto-commit growth tracking
manager.commit_changes("Session 001: New patterns discovered")
```

## 📁 Directory Structure

```
piddy-growth/
├── README.md                          # This file
├── piddy_growth_manager.py            # Python integration module
├── learning-logs/                     # Session insights & learnings
│   └── 2026-03-13-initialization.md  # Sample learning log
├── experiments/                       # Active experimental features
│   ├── knowledge-graph-optimization.md
│   └── async-event-loop.md
├── patterns/                          # Discovered architectural patterns
│   ├── api-design-patterns.md
│   ├── database-schema-patterns.md
│   └── ...
├── performance-metrics/               # Quantitative capability tracking
│   └── metrics-schema.md
└── knowledge-base-sync/               # Synced knowledge from KB
```

## 🎯 Daily Workflow

### At Session Start
```bash
# Update growth repo with latest patterns
git pull origin main

# Review recent learnings to understand current state
ls -lt learning-logs/ | head -5

# Check active experiments
cat experiments/active-experiments.md
```

### During Session
```python
# Import and use growth manager
manager = PiddyGrowthManager()

# Every time you discover something useful
manager.record_pattern("pattern-name", "Pattern Type", "Description")

# At completion of task
manager.commit_changes("Session: Task description and learnings")
```

### At Session End
```bash
# Verify all changes committed
git status

# Push changes if remote is configured
git push origin main

# Generate session summary
echo "Session complete - $(git log -1 --pretty=%H) patterns recorded"
```

## 🔄 Integration Points with Main Piddy

### 1. Learning Loop
```
Complete Task → Log Learning → Commit to Growth Repo → 
Review Patterns → Improve Main Code → Repeat
```

### 2. Pattern Promotion Pipeline
```
Experiment in Growth Repo → Validate → Document → 
Code Review → Merge to Main → Deploy
```

### 3. Performance Feedback Loop
```
Execute Task → Record Metrics → Analyze Trends → 
Optimize Approach → Update Patterns
```

## 📊 Performance Tracking Template

Create `performance-metrics/session-YYYY-MM-DD.json`:

```json
{
  "date": "2026-03-13",
  "session_duration_minutes": 45,
  "tasks_completed": 12,
  "tasks_success_rate": 0.96,
  "avg_response_time_ms": 1240,
  "cache_hit_rate": 0.87,
  "tool_effectiveness": {
    "code_generation": 0.98,
    "code_review": 0.92,
    "debugging": 0.95
  },
  "patterns_documented": 3,
  "experiments_completed": 1
}
```

## 🔗 Connecting to Remote Repository

```bash
# If you want to push to a remote git service (GitHub, GitLab, etc.)
git remote add origin https://github.com/burchdad/piddy-growth.git
git branch -M main
git push -u origin main
```

## 📈 Measuring Growth

Track these metrics over time:

- **Pattern Count**: Total patterns documented
- **Success Rate**: Task completion success rate
- **Response Time**: Average API response time
- **Code Quality**: Quality scores from reviews
- **Reusability**: Patterns reused in main codebase
- **Impact**: Performance improvements from adopted patterns

## 🆘 Troubleshooting

### Git Conflicts
```bash
# Resolve and commit
git status
git add <conflicted-files>
git commit -m "Resolved conflicts"
```

### Missing Directories
```bash
# Ensure all necessary directories exist
mkdir -p learning-logs experiments patterns performance-metrics knowledge-base-sync
```

### Manager Import Issues
```python
# Add growth repo to Python path
import sys
sys.path.insert(0, '/workspaces/piddy-growth')
from piddy_growth_manager import PiddyGrowthManager
```

---

**Version**: 1.0  
**Last Updated**: 2026-03-13  
**Maintained By**: Piddy Self-Growth System
