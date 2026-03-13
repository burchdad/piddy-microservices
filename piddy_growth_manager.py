#!/usr/bin/env python3
"""
Piddy Growth Repository Integration Script

This script enables Piddy to:
1. Log learning sessions
2. Record experiments
3. Track performance metrics
4. Document discovered patterns
5. Auto-commit changes to growth repo
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


class PiddyGrowthManager:
    """Manages Piddy's autonomous learning and growth repository."""
    
    def __init__(self, growth_repo_path="/workspaces/piddy-growth"):
        self.repo_path = Path(growth_repo_path)
        self.learning_logs = self.repo_path / "learning-logs"
        self.experiments = self.repo_path / "experiments"
        self.patterns = self.repo_path / "patterns"
        self.metrics = self.repo_path / "performance-metrics"
        
    def log_session_learning(self, session_id: str, insights: dict):
        """Log insights from a completed session."""
        timestamp = datetime.now().isoformat()
        filename = f"{session_id}-{timestamp.split('T')[0]}.md"
        
        content = f"""# Session Learning Log - {timestamp}

## Session ID: {session_id}

### Key Insights
"""
        for insight in insights.get("insights", []):
            content += f"- {insight}\n"
            
        content += f"""
### Metrics
```json
{json.dumps(insights.get("metrics", {}), indent=2)}
```

### Recommendations
"""
        for rec in insights.get("recommendations", []):
            content += f"- {rec}\n"
            
        log_file = self.learning_logs / filename
        log_file.write_text(content)
        return str(log_file)
        
    def record_experiment(self, name: str, description: str, status: str):
        """Record a new experiment."""
        exp_file = self.experiments / f"{name}.md"
        content = f"""# Experiment: {name}

**Date Started**: {datetime.now().isoformat()}
**Status**: {status}

## Description
{description}

## Hypothesis
[To be filled]

## Results
[To be tracked]

## Learnings
[To be documented]
"""
        exp_file.write_text(content)
        return str(exp_file)
        
    def record_pattern(self, name: str, pattern_type: str, content: str):
        """Document a discovered pattern."""
        pattern_file = self.patterns / f"{name}.md"
        full_content = f"""# {pattern_type} Pattern: {name}

**Discovered**: {datetime.now().isoformat()}
**Status**: Documented

## Pattern Description
{content}

## Use Cases
[To be documented]

## Implementation Notes
[To be added]

## Performance Impact
[Metrics to be tracked]
"""
        pattern_file.write_text(full_content)
        return str(pattern_file)
        
    def commit_changes(self, message: str):
        """Auto-commit changes to growth repo."""
        try:
            subprocess.run(
                ["git", "-C", str(self.repo_path), "add", "-A"],
                check=True,
                capture_output=True
            )
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "commit", "-m", message],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"No changes to commit: {e.stderr}"
            

if __name__ == "__main__":
    # Example usage
    manager = PiddyGrowthManager()
    
    # Log a sample insight
    insights = {
        "insights": [
            "API design patterns improve code reusability",
            "Knowledge graphs scale better with proper indexing",
            "Reputation-weighted consensus improves decision accuracy"
        ],
        "metrics": {
            "session_duration_min": 45,
            "tasks_completed": 12,
            "success_rate": 0.98
        },
        "recommendations": [
            "Implement caching layer for frequently accessed patterns",
            "Create automated pattern validation system",
            "Build metrics dashboard for real-time monitoring"
        ]
    }
    
    log_file = manager.log_session_learning("growth-init", insights)
    print(f"✓ Logged learning to: {log_file}")
    
    # Record an experiment
    exp_file = manager.record_experiment(
        "knowledge-graph-optimization",
        "Testing bidirectional graph traversal for improved reasoning",
        "In Progress"
    )
    print(f"✓ Created experiment: {exp_file}")
    
    # Record a discovered pattern
    pattern_file = manager.record_pattern(
        "async-event-loop",
        "Performance",
        "Use async/await to prevent blocking operations and improve throughput"
    )
    print(f"✓ Documented pattern: {pattern_file}")
    
    # Commit changes
    commit_msg = manager.commit_changes("Auto-commit: Piddy growth tracking")
    print(f"✓ Committed: {commit_msg.strip()}")
