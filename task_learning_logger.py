#!/usr/bin/env python3
"""
Piddy Task-Based Learning Logger

Use this after completing significant tasks to automatically log learnings.
Can be called from Piddy's task completion handlers.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/workspaces/piddy-growth')
from piddy_growth_manager import PiddyGrowthManager


def log_task_completion(task_id: str, task_description: str, insights: dict) -> str:
    """
    Log learnings from a completed task.
    
    Args:
        task_id: Unique identifier for the task
        task_description: What the task accomplished
        insights: Dict with keys: discoveries, patterns, metrics, improvements
    
    Returns:
        Path to created log file
    """
    manager = PiddyGrowthManager("/workspaces/piddy-growth")
    
    full_insights = {
        "insights": insights.get("discoveries", []),
        "patterns": insights.get("patterns", []),
        "metrics": insights.get("metrics", {}),
        "improvements": insights.get("improvements", [])
    }
    
    log_file = manager.log_session_learning(task_id, full_insights)
    
    # Auto-commit
    manager.commit_changes(f"Task {task_id}: {task_description}")
    
    return log_file


def example_workflow():
    """Example: How Piddy would use this after completing a code generation task."""
    
    print("📝 Example Task-Based Learning:\n")
    
    # Simulated task completion
    task_insights = {
        "discoveries": [
            "FastAPI validation becomes simpler with Pydantic v2",
            "Using discriminated unions improves type safety for API responses",
            "RequestPattern with BaseModel inheritance reduces code duplication"
        ],
        "patterns": [
            "Request envelope pattern for consistent API responses",
            "Middleware chain for cross-cutting concerns",
            "Dependency injection for testability"
        ],
        "metrics": {
            "code_generation_time": 1.2,  # seconds
            "lines_generated": 45,
            "accuracy_score": 0.98,
            "user_satisfaction": 5.0  # out of 5
        },
        "improvements": [
            "Add caching for common endpoint patterns",
            "Create validation schema library",
            "Build response formatter utilities"
        ]
    }
    
    log_file = log_task_completion(
        "code-gen-fastapi-endpoints",
        "Generated 3 FastAPI endpoints with validation and JWT auth",
        task_insights
    )
    
    print(f"✓ Task learning logged to: {Path(log_file).name}")
    print("\nNow Piddy can:")
    print("  - Review this pattern for similar tasks")
    print("  - Track improvement suggestions")
    print("  - Monitor performance metrics over time")
    print("  - Promote successful patterns to main codebase")


if __name__ == "__main__":
    example_workflow()
