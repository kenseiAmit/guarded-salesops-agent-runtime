import argparse
import sys
import json
from typing import Optional
from salesops_agent.agent.core import SalesOpsAgent
from salesops_agent.evaluation.evaluator import EvaluationSuite
from salesops_agent.observability.metrics import MonitoringReportGenerator

def ask_command(args: argparse.Namespace) -> int:
    """Handles 'salesops-agent ask <question> [--approval approve|reject]'."""
    agent = SalesOpsAgent()
    result = agent.run(
        question=args.question,
        approval=args.approval,
        task_id=args.task_id,
        user_id=args.user_id,
    )

    print("\n" + "=" * 60)
    print(f"SalesOps Agent Run Result [{result['status'].upper()}]")
    print(f"Run ID: {result['run_id']}")
    if result.get("hitl_decision"):
        print(f"HITL Decision: {result['hitl_decision']}")
    if result.get("reason"):
        print(f"Policy Reason: {result['reason']}")
    print("-" * 60)
    print(result.get("answer", ""))
    print("=" * 60 + "\n")
    
    return 0 if result["status"] in ["success", "blocked", "rejected"] else 1

def evaluate_main() -> int:
    """CLI entry point for running the automated evaluation suite."""
    print("Running automated SalesOps Agent evaluation suite...")
    suite = EvaluationSuite()
    results = suite.run_suite()
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print("\n" + "=" * 70)
    print(f"Evaluation Complete: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
    print("Reports generated:")
    print(" - reports/evaluation_report.md")
    print(" - reports/evaluation_report.json")
    print(" - reports/monitoring_report.md")
    print("=" * 70 + "\n")
    
    return 0 if passed == total else 1

def monitoring_report_main() -> int:
    """CLI entry point for generating the monitoring summary report."""
    print("Generating operational monitoring report from logs...")
    generator = MonitoringReportGenerator()
    report_file = generator.save_report()
    print(f"Monitoring report updated: {report_file}")
    return 0

def cli_main() -> None:
    """Main CLI router for salesops-agent."""
    parser = argparse.ArgumentParser(
        prog="salesops-agent",
        description="SalesOps Agent: Production-grade Guarded & Monitored AI System",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 'ask' subcommand
    ask_parser = subparsers.add_parser("ask", help="Ask the agent a question or request an action")
    ask_parser.add_argument("question", type=str, help="The query or task for the agent")
    ask_parser.add_argument(
        "--approval",
        choices=["approve", "reject"],
        default=None,
        help="Human-in-the-loop approval decision for high-risk actions (e.g. email sending)",
    )
    ask_parser.add_argument("--task-id", type=str, default=None, help="Optional tracking task ID")
    ask_parser.add_argument("--user-id", type=str, default="cli_operator", help="User ID for session isolation")

    # 'evaluate' subcommand
    subparsers.add_parser("evaluate", help="Run the automated regression and evaluation suite")

    # 'generate-monitoring-report' subcommand
    subparsers.add_parser("generate-monitoring-report", help="Generate the operational monitoring report")

    args = parser.parse_args()

    if args.command == "ask":
        sys.exit(ask_command(args))
    elif args.command == "evaluate":
        sys.exit(evaluate_main())
    elif args.command == "generate-monitoring-report":
        sys.exit(monitoring_report_main())
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    cli_main()
