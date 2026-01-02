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

# 嘗試使用 Rich UI，如果沒有則使用基本輸出
try:
    from ui import (
        print_banner, print_config, print_agents, MonusUI,
        console, success, error, info
    )
    USE_RICH = True
except ImportError:
    USE_RICH = False
    def print_banner():
        print("""
    +==========================================+
    |   M O N U S                              |
    |   Your Autonomous Research Agent         |
    +==========================================+
        """)


async def run_task(goal: str, model: str = "deepseek-chat",
                   output_format: str = "pdf", theme: str = "default"):
    """執行研究任務"""

    if USE_RICH:
        print_banner()
        print_config(goal, model, output_format, theme)
        print_agents()
        ui = MonusUI()
    else:
        print_banner()
        print(f"Goal: {goal}")
        print(f"Model: {model}")
        print(f"Output: {output_format}")
        ui = None

    # 初始化 5 個 Agent
    memory = Memory(runs_dir="runs")
    planner = Planner(model=model)
    reasoner = Reasoner(model=model)
    evaluator = Evaluator(model=model)
    verifier = Verifier(min_sources=5, min_word_count=800)

    # 建立並執行 Agent Loop
    agent = AgentLoop(
        memory=memory,
        planner=planner,
        reasoner=reasoner,
        evaluator=evaluator,
        verifier=verifier,
        max_iterations=20,
        ui=ui  # 傳入 UI
    )

    result = await agent.run(goal, output_format=output_format, theme=theme)

    # 顯示結果
    if USE_RICH:
        ui.show_outputs(result.get("outputs", {}))
        ui.show_verification(result.get("verification", {}))

        # 顯示建議
        final_eval = result.get("final_evaluation", {})
        if final_eval.get("suggestions"):
            ui.show_suggestions(final_eval["suggestions"])

        # 顯示最終結果
        ui.show_final_result(
            result["success"],
            result.get("run_id", "N/A"),
            final_eval.get("quality_score")
        )
    else:
        # 基本輸出
        print("\n" + "=" * 50)
        if result["success"]:
            print("[OK] Task completed successfully!")
        else:
            print("[FAIL] Task completed with issues")

        print(f"\n[Run ID] {result.get('run_id', 'N/A')}")
        print(f"[Report] {result.get('report_path', 'N/A')}")

        if "outputs" in result:
            print("\n[Output Files]")
            for fmt, info in result["outputs"].items():
                if info and info.get("success"):
                    print(f"   [{fmt.upper()}] {info.get('path', 'N/A')}")

    return result


def list_runs():
    """列出所有執行記錄"""
    runs_dir = Path("runs")
    if not runs_dir.exists():
        if USE_RICH:
            info("No runs found.")
        else:
            print("No runs found.")
        return

    runs = sorted(runs_dir.iterdir(), reverse=True)
    if not runs:
        if USE_RICH:
            info("No runs found.")
        else:
            print("No runs found.")
        return

    if USE_RICH:
        from rich.table import Table
        from rich.box import ROUNDED
        import json

        table = Table(title="Recent Runs", box=ROUNDED)
        table.add_column("Status", justify="center", width=6)
        table.add_column("Run ID", style="cyan", width=24, no_wrap=True)
        table.add_column("Goal", max_width=40, no_wrap=True, overflow="ellipsis")
        table.add_column("Files", justify="center", width=18)

        for run in runs[:10]:
            task_file = run / "task.json"
            if task_file.exists():
                task = json.loads(task_file.read_text(encoding="utf-8"))
                status_icons = {
                    "completed": "[green]✓[/]",
                    "running": "[yellow]⟳[/]",
                    "failed": "[red]✗[/]",
                    "pending": "[dim]○[/]"
                }
                status = status_icons.get(task["status"], "?")
                goal_text = task['goal'][:40] + "..." if len(task['goal']) > 40 else task['goal']

                # 計算輸出檔案數
                files = []
                if (run / "report.pdf").exists(): files.append("PDF")
                if (run / "slides.html").exists(): files.append("Slides")
                if (run / "index.html").exists(): files.append("Web")
                files_str = ", ".join(files) if files else "-"

                table.add_row(status, run.name, goal_text, files_str)

        console.print(table)
    else:
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
        if USE_RICH:
            error(f"Run not found: {run_id}")
        else:
            print(f"Run not found: {run_id}")
        return

    task_file = run_dir / "task.json"
    report_file = run_dir / "report.md"

    if USE_RICH:
        from rich.panel import Panel
        from rich.table import Table
        from rich.box import ROUNDED
        from rich.markdown import Markdown
        import json

        if task_file.exists():
            task = json.loads(task_file.read_text(encoding="utf-8"))

            # 任務資訊
            console.print(Panel(
                f"[bold]Goal:[/] {task['goal']}\n"
                f"[bold]Status:[/] {task['status']}\n"
                f"[bold]Created:[/] {task.get('created_at', 'N/A')}",
                title=f"[bold cyan]Run: {run_id}[/]",
                border_style="cyan"
            ))

            # 步驟表格
            table = Table(title="Steps", box=ROUNDED)
            table.add_column("ID", style="dim")
            table.add_column("Status", justify="center")
            table.add_column("Title")
            table.add_column("Tool", style="cyan")

            for step in task["steps"][:10]:  # 只顯示前 10 個
                status_icons = {"done": "[green]✓[/]", "pending": "[dim]○[/]",
                               "running": "[yellow]⟳[/]", "failed": "[red]✗[/]"}
                status = status_icons.get(step["status"], "?")
                table.add_row(str(step['id']), status, step['title'][:40], step.get('tool', '-'))

            console.print(table)

            # 輸出檔案
            files = []
            if (run_dir / "report.pdf").exists(): files.append(("PDF", "report.pdf"))
            if (run_dir / "slides.html").exists(): files.append(("Slides", "slides.html"))
            if (run_dir / "index.html").exists(): files.append(("Web", "index.html"))

            if files:
                console.print("\n[bold]Output Files:[/]")
                for fmt, name in files:
                    console.print(f"  📄 [{fmt}] {run_dir / name}")

        if report_file.exists():
            console.print("\n[bold]Report Preview:[/]")
            preview = report_file.read_text(encoding="utf-8")[:1000]
            console.print(Panel(Markdown(preview), border_style="dim"))

    else:
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
