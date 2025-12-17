#!/usr/bin/env python3
"""
Utility script to analyze execution history from logs/execution_history.jsonl or .json

Supports both JSONL (default/preferred) and legacy JSON formats.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from agentic_fleet.utils.cfg import DEFAULT_HISTORY_PATH


def load_history() -> list[dict[str, Any]]:
    """Load execution history from JSON or JSONL file."""

    # Try JSONL first (new format)
    jsonl_file = Path(DEFAULT_HISTORY_PATH)
    if jsonl_file.exists():
        executions = []
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    executions.append(json.loads(line))
        if executions:
            print(f"✓ Loaded {len(executions)} executions from {jsonl_file}")
            return executions

    # Fall back to legacy JSON format
    json_file = jsonl_file.with_suffix(".json")
    if json_file.exists():
        with open(json_file) as f:
            executions = json.load(f)
        print(f"✓ Loaded {len(executions)} executions from {json_file}")
        return executions

    print(f"❌ No execution history found at {jsonl_file} or {json_file}")
    return []


def print_summary(executions: list[dict[str, Any]]):
    """Print overall statistics."""
    if not executions:
        return

    total = len(executions)
    times = [e.get("total_time_seconds", 0) for e in executions if "total_time_seconds" in e]
    scores = [
        e.get("quality", {}).get("score", 0)
        for e in executions
        if "quality" in e and "score" in e.get("quality", {})
    ]

    if not times or not scores:
        print("\n⚠️  Incomplete data in history - skipping summary")
        return

    print("\n📊 Execution Summary")
    print("=" * 80)
    print(f"Total Executions: {total}")
    print(f"Average Time: {statistics.mean(times):.2f}s")
    print(f"Min/Max Time: {min(times):.2f}s / {max(times):.2f}s")
    print(f"Average Quality Score: {statistics.mean(scores):.1f}/10")
    print(f"Min/Max Score: {min(scores):.1f}/10 / {max(scores):.1f}/10")


def print_executions(executions: list[dict[str, Any]], limit: int | None = None):
    """Print detailed execution information."""
    if not executions:
        print("❌ No executions found")
        return

    to_show = executions[-limit:] if limit is not None else executions

    print("\n📋 Execution History")
    print("=" * 80)

    for i, execution in enumerate(to_show, 1):
        task = execution.get("task", "Unknown task")
        task = task[:60] + "..." if len(task) > 60 else task

        print(f"\n{i}. {task}")
        if "total_time_seconds" in execution:
            print(f"   ⏰ Time: {execution['total_time_seconds']:.2f}s")
        if "quality" in execution and "score" in execution["quality"]:
            print(f"   📊 Quality: {execution['quality']['score']}/10")
        if "routing" in execution:
            routing = execution["routing"]
            if "mode" in routing:
                print(f"   🔀 Mode: {routing['mode'].upper()}")
            if "assigned_to" in routing:
                print(f"   👥 Agents: {', '.join(routing['assigned_to'])}")
        if "dspy_analysis" in execution and "complexity" in execution["dspy_analysis"]:
            print(f"   🎯 Complexity: {execution['dspy_analysis']['complexity']}")


def print_routing_stats(executions: list[dict[str, Any]]):
    """Print routing mode statistics."""
    if not executions:
        return

    modes: dict[str, int] = {}
    for execution in executions:
        if "routing" in execution and "mode" in execution["routing"]:
            mode = execution["routing"]["mode"]
            modes[mode] = modes.get(mode, 0) + 1

    if not modes:
        print("\n⚠️  No routing data available")
        return

    print("\n🔀 Routing Mode Distribution")
    print("=" * 80)
    for mode, count in sorted(modes.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(executions)) * 100
        print(f"{mode.upper():12} : {count:3} executions ({pct:5.1f}%)")


def print_agent_usage(executions: list[dict[str, Any]]):
    """Print agent usage statistics."""
    if not executions:
        return

    agents: dict[str, int] = {}
    for execution in executions:
        if "routing" in execution and "assigned_to" in execution["routing"]:
            for agent in execution["routing"]["assigned_to"]:
                agents[agent] = agents.get(agent, 0) + 1

    if not agents:
        print("\n⚠️  No agent usage data available")
        return

    print("\n👥 Agent Usage Statistics")
    print("=" * 80)
    for agent, count in sorted(agents.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(executions)) * 100
        print(f"{agent:12} : {count:3} tasks ({pct:5.1f}%)")


def print_timing_breakdown(executions: list[dict[str, Any]]):
    """Print average time breakdown by phase."""
    if not executions:
        return

    # Safely extract timing data with defaults
    analysis_times = [
        e.get("dspy_analysis", {}).get("analysis_time_seconds", 0)
        for e in executions
        if "dspy_analysis" in e and "analysis_time_seconds" in e.get("dspy_analysis", {})
    ]
    routing_times = [
        e.get("routing", {}).get("routing_time_seconds", 0)
        for e in executions
        if "routing" in e and "routing_time_seconds" in e.get("routing", {})
    ]
    quality_times = [
        e.get("quality", {}).get("quality_time_seconds", 0)
        for e in executions
        if "quality" in e and "quality_time_seconds" in e.get("quality", {})
    ]
    total_times = [e.get("total_time_seconds", 0) for e in executions if "total_time_seconds" in e]

    if not (analysis_times and routing_times and quality_times and total_times):
        print("\n⚠️  Incomplete timing data - skipping breakdown")
        return

    avg_analysis = statistics.mean(analysis_times)
    avg_routing = statistics.mean(routing_times)
    avg_quality = statistics.mean(quality_times)
    avg_total = statistics.mean(total_times)
    avg_execution = avg_total - avg_analysis - avg_routing - avg_quality

    print("\n⏱️  Average Time Breakdown")
    print("=" * 80)
    print(f"DSPy Analysis:    {avg_analysis:6.2f}s ({(avg_analysis / avg_total) * 100:5.1f}%)")
    print(f"DSPy Routing:     {avg_routing:6.2f}s ({(avg_routing / avg_total) * 100:5.1f}%)")
    print(f"Agent Execution:  {avg_execution:6.2f}s ({(avg_execution / avg_total) * 100:5.1f}%)")
    print(f"DSPy Quality:     {avg_quality:6.2f}s ({(avg_quality / avg_total) * 100:5.1f}%)")
    print(f"{'─' * 40}")
    print(f"Total Average:    {avg_total:6.2f}s")


def main():
    """Run the analysis script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze DSPy-Enhanced Agent Framework execution history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --summary              # Show overall statistics
  %(prog)s --executions           # List all executions
  %(prog)s --executions --last 5  # Show last 5 executions
  %(prog)s --routing              # Show routing mode distribution
  %(prog)s --agents               # Show agent usage statistics
  %(prog)s --timing               # Show time breakdown by phase
  %(prog)s --all                  # Show everything
        """,
    )

    parser.add_argument("--summary", action="store_true", help="Show overall statistics")
    parser.add_argument("--executions", action="store_true", help="List execution details")
    parser.add_argument("--last", type=int, metavar="N", help="Show last N executions")
    parser.add_argument("--routing", action="store_true", help="Show routing statistics")
    parser.add_argument("--agents", action="store_true", help="Show agent usage statistics")
    parser.add_argument("--timing", action="store_true", help="Show timing breakdown")
    parser.add_argument("--all", action="store_true", help="Show all statistics")

    args = parser.parse_args()

    # Load history
    executions = load_history()

    if not executions:
        return

    # If no flags, show summary and last 10
    if not any(
        [
            args.summary,
            args.executions,
            args.routing,
            args.agents,
            args.timing,
            args.all,
        ]
    ):
        args.summary = True
        args.executions = True
        args.last = 10

    # Show requested information
    if args.all:
        print_summary(executions)
        print_executions(executions)
        print_routing_stats(executions)
        print_agent_usage(executions)
        print_timing_breakdown(executions)
    else:
        if args.summary:
            print_summary(executions)
        if args.executions:
            print_executions(executions, limit=args.last)
        if args.routing:
            print_routing_stats(executions)
        if args.agents:
            print_agent_usage(executions)
        if args.timing:
            print_timing_breakdown(executions)

    print()


if __name__ == "__main__":
    main()
