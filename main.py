#!/usr/bin/env python3
"""
Monus - 你的自動研究 Agent (5 Agent 架構)
輸入任務目標 → 自動研究 → 產出 PDF/Slides/Web

5 Agents:
- Planner: 任務拆解與決策
- Reasoner: 推理思考與衝突處理
- Evaluator: 觀察評估與品質檢查
- Verifier: 規則驗證
- Renderer: HTML/CSS 多格式輸出
"""
import asyncio
import argparse
import sys
import io
from pathlib import Path

# Windows UTF-8 支援
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 確保可以 import 本地模組
sys.path.insert(0, str(Path(__file__).parent))

from agent.planner import Planner
from agent.reasoner import Reasoner
from agent.evaluator import Evaluator
from agent.loop import AgentLoop
from agent.verifier import Verifier
from agent.memory import Memory


def print_banner():
    """印出 Monus 標誌"""
    banner = """
    +==========================================+
    |                                          |
    |   M   M  OOO  N   N U   U  SSS           |
    |   MM MM O   O NN  N U   U S              |
    |   M M M O   O N N N U   U  SSS           |
    |   M   M O   O N  NN U   U     S          |
    |   M   M  OOO  N   N  UUU  SSSS           |
    |                                          |
    |   Your Autonomous Research Agent         |
    |   Powered by DeepSeek + 5 Agent System   |
    +==========================================+
    """
    print(banner)


async def run_task(goal: str, model: str = "deepseek-chat",
                   output_format: str = "pdf", theme: str = "default"):
    """執行研究任務"""
    print_banner()
    print(f"\n[Goal] {goal}")
    print(f"[Model] {model}")
    print(f"[Output] {output_format}" + (f" (theme: {theme})" if output_format in ["slides", "all"] else ""))
    print("=" * 50)

    # 初始化 5 個 Agent
    memory = Memory(runs_dir="runs")
    planner = Planner(model=model)
    reasoner = Reasoner(model=model)
    evaluator = Evaluator(model=model)
    verifier = Verifier(min_sources=5, min_word_count=800)

    print("\n[Agents initialized]")
    print("   - Planner: Task decomposition & planning")
    print("   - Reasoner: Thought generation & conflict resolution")
    print("   - Evaluator: Result evaluation & quality check")
    print("   - Verifier: Rule-based verification")
    print("   - Renderer: PDF / Slides / Web output")

    # 建立並執行 Agent Loop
    agent = AgentLoop(
        memory=memory,
        planner=planner,
        reasoner=reasoner,
        evaluator=evaluator,
        verifier=verifier,
        max_iterations=20
    )

    result = await agent.run(goal, output_format=output_format, theme=theme)

    # 輸出結果
    print("\n" + "=" * 50)
    if result["success"]:
        print("[OK] Task completed successfully!")
    else:
        print("[FAIL] Task completed with issues")

    print(f"\n[Run ID] {result.get('run_id', 'N/A')}")
    print(f"[Report] {result.get('report_path', 'N/A')}")

    # 顯示輸出檔案
    if "outputs" in result:
        print("\n[Output Files]")
        for fmt, info in result["outputs"].items():
            if info and info.get("success"):
                print(f"   [{fmt.upper()}] {info.get('path', 'N/A')}")

    # 顯示驗證結果
    if "verification" in result:
        print("\n[Verification Results]")
        for r in result["verification"]["results"]:
            status = "[PASS]" if r["passed"] else "[FAIL]"
            print(f"   {status} {r['rule']}: {r['message']}")

    # 顯示最終評估
    if "final_evaluation" in result:
        eval_result = result["final_evaluation"]
        print(f"\n[Quality Score] {eval_result.get('quality_score', 'N/A')}")

    return result


def list_runs():
    """列出所有執行記錄"""
    runs_dir = Path("runs")
    if not runs_dir.exists():
        print("No runs found.")
        return

    runs = sorted(runs_dir.iterdir(), reverse=True)
    if not runs:
        print("No runs found.")
        return

    print("\n[Recent Runs]")
    print("-" * 60)
    for run in runs[:10]:
        task_file = run / "task.json"
        if task_file.exists():
            import json
            task = json.loads(task_file.read_text(encoding="utf-8"))
            status_map = {
                "completed": "[OK]",
                "running": "[RUN]",
                "failed": "[FAIL]",
                "pending": "[WAIT]"
            }
            status = status_map.get(task["status"], "[?]")
            print(f"{status} {run.name}")
            print(f"   Goal: {task['goal'][:50]}...")
        print()


def show_run(run_id: str):
    """顯示特定執行記錄"""
    run_dir = Path("runs") / run_id
    if not run_dir.exists():
        print(f"Run not found: {run_id}")
        return

    task_file = run_dir / "task.json"
    report_file = run_dir / "report.md"

    if task_file.exists():
        import json
        task = json.loads(task_file.read_text(encoding="utf-8"))
        print(f"\n[Task] {task['goal']}")
        print(f"[Status] {task['status']}")
        print(f"\nSteps ({len(task['steps'])}):")
        for step in task["steps"]:
            status_map = {"done": "[OK]", "pending": "[--]", "running": "[>>]", "failed": "[XX]"}
            status = status_map.get(step["status"], "[?]")
            print(f"   {status} [{step['id']}] {step['title']}")

    if report_file.exists():
        print(f"\n[Report saved at] {report_file}")
        print("\nReport Preview (first 500 chars):")
        print("-" * 40)
        print(report_file.read_text(encoding="utf-8")[:500])


def main():
    parser = argparse.ArgumentParser(
        description="Monus - Your Autonomous Research Agent (5 Agent System)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run "Python asyncio 教學"
  python main.py run "Python asyncio 教學" --format slides
  python main.py run "Python asyncio 教學" --format all --theme dark
  python main.py list
  python main.py show 2026-01-02_123456_python_asyncio

5 Agent Architecture:
  - Planner: Decomposes tasks into steps
  - Reasoner: Generates thoughts and handles conflicts
  - Evaluator: Evaluates results and checks quality
  - Verifier: Validates against rules
  - Renderer: PDF / Slides / Web output
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run 命令
    run_parser = subparsers.add_parser("run", help="Run a research task")
    run_parser.add_argument("goal", type=str, help="The research goal")
    run_parser.add_argument(
        "--model", "-m",
        type=str,
        default="deepseek-chat",
        help="DeepSeek model to use (default: deepseek-chat)"
    )
    run_parser.add_argument(
        "--format", "-f",
        type=str,
        default="pdf",
        choices=["pdf", "slides", "web", "all"],
        help="Output format: pdf, slides, web, or all (default: pdf)"
    )
    run_parser.add_argument(
        "--theme", "-t",
        type=str,
        default="default",
        choices=["default", "dark", "minimal"],
        help="Theme for slides/web output (default: default)"
    )

    # list 命令
    subparsers.add_parser("list", help="List all runs")

    # show 命令
    show_parser = subparsers.add_parser("show", help="Show a specific run")
    show_parser.add_argument("run_id", type=str, help="The run ID to show")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run_task(args.goal, args.model, args.format, args.theme))
    elif args.command == "list":
        list_runs()
    elif args.command == "show":
        show_run(args.run_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
