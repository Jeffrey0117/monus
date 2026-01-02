"""
Monus UI - 精美的終端介面
使用 Rich 庫提供進度條、狀態顯示、表格等
"""
import sys
import io
import os

# Windows UTF-8 支援 (只在尚未設定時執行)
if sys.platform == "win32":
    # 設定環境變數讓 Python 使用 UTF-8
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    # 只在需要時包裝 stdout/stderr
    if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass  # 已經被包裝過了

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED, DOUBLE
from rich import print as rprint
from typing import Optional
import time


# 強制使用 UTF-8
console = Console(force_terminal=True, legacy_windows=False)


# 顏色主題
COLORS = {
    "primary": "#00d4aa",      # 青綠色
    "secondary": "#7c3aed",    # 紫色
    "success": "#10b981",      # 綠色
    "warning": "#f59e0b",      # 橙色
    "error": "#ef4444",        # 紅色
    "info": "#3b82f6",         # 藍色
    "muted": "#6b7280",        # 灰色
}


def print_banner():
    """印出精美的 Monus 標誌"""
    banner = """
[bold #00d4aa]    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║   [bold white]███╗   ███╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗[/]  ║
    ║   [bold white]████╗ ████║██╔═══██╗████╗  ██║██║   ██║██╔════╝[/]  ║
    ║   [bold white]██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║███████╗[/]  ║
    ║   [bold white]██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║╚════██║[/]  ║
    ║   [bold white]██║ ╚═╝ ██║╚██████╔╝██║ ╚████║╚██████╔╝███████║[/]  ║
    ║   [bold white]╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝[/]  ║
    ║                                           ║
    ║   [dim]Autonomous Research Agent[/]               ║
    ║   [dim]Powered by DeepSeek + 5 Agent System[/]    ║
    ╚═══════════════════════════════════════════╝[/]
    """
    console.print(banner)


def print_config(goal: str, model: str, output_format: str, theme: str):
    """顯示任務配置"""
    table = Table(box=ROUNDED, show_header=False, border_style="dim")
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("📎 Goal", goal)
    table.add_row("🤖 Model", model)
    table.add_row("📄 Output", output_format.upper())
    if output_format in ["slides", "all"]:
        table.add_row("🎨 Theme", theme)

    console.print(table)
    console.print()


def print_agents():
    """顯示 Agent 初始化狀態"""
    agents = [
        ("🧠", "Planner", "Task decomposition & planning", "#00d4aa"),
        ("💭", "Reasoner", "Thought generation & conflict resolution", "#7c3aed"),
        ("📊", "Evaluator", "Result evaluation & quality check", "#3b82f6"),
        ("✅", "Verifier", "Rule-based verification", "#10b981"),
        ("🎨", "Renderer", "PDF / Slides / Web output", "#f59e0b"),
    ]

    console.print("[bold]Agents Ready:[/]")
    for icon, name, desc, color in agents:
        console.print(f"  {icon} [bold {color}]{name}[/] [dim]- {desc}[/]")
    console.print()


class MonusUI:
    """Monus 主要 UI 類別"""

    def __init__(self):
        self.console = console
        self.current_phase = ""
        self.current_step = ""
        self.sources_count = 0
        self.iteration = 0
        self.max_iterations = 20

    def start_run(self, run_id: str, goal: str):
        """開始執行任務"""
        self.console.print(Panel(
            f"[bold]Run ID:[/] {run_id}",
            title="[bold #00d4aa]Starting Task[/]",
            border_style="#00d4aa"
        ))

    def update_phase(self, phase: str):
        """更新當前階段"""
        self.current_phase = phase
        phases = {
            "planning": ("🧠", "Planning", "#00d4aa"),
            "searching": ("🔍", "Searching", "#3b82f6"),
            "extracting": ("📥", "Extracting", "#7c3aed"),
            "analyzing": ("💭", "Analyzing", "#f59e0b"),
            "writing": ("✍️", "Writing Report", "#10b981"),
            "rendering": ("🎨", "Rendering Output", "#ec4899"),
            "verifying": ("✅", "Verifying", "#10b981"),
        }
        if phase in phases:
            icon, name, color = phases[phase]
            self.console.print(f"\n[bold {color}]{icon} {name}...[/]")

    def update_step(self, step: str, status: str = "running"):
        """更新當前步驟"""
        self.current_step = step
        icons = {
            "running": "[bold yellow]⟳[/]",
            "done": "[bold green]✓[/]",
            "failed": "[bold red]✗[/]",
            "skipped": "[dim]○[/]",
        }
        icon = icons.get(status, "•")
        self.console.print(f"  {icon} {step}")

    def update_iteration(self, iteration: int, max_iterations: int):
        """更新迭代次數"""
        self.iteration = iteration
        self.max_iterations = max_iterations
        progress = iteration / max_iterations
        bar_width = 20
        filled = int(progress * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        self.console.print(f"\n[dim]Progress:[/] [{bar}] {iteration}/{max_iterations}")

    def update_sources(self, count: int):
        """更新來源數量"""
        self.sources_count = count
        self.console.print(f"  [cyan]📚 Sources collected: {count}[/]")

    def show_action(self, tool: str, input_data: str):
        """顯示正在執行的動作"""
        tool_icons = {
            "browser.search": "🔍",
            "browser.open": "🌐",
            "browser.extract": "📥",
            "fs.write": "💾",
            "code.run": "⚡",
        }
        icon = tool_icons.get(tool, "•")
        # 截斷過長的輸入
        display_input = input_data[:50] + "..." if len(input_data) > 50 else input_data
        self.console.print(f"  {icon} [bold]{tool}[/] [dim]{display_input}[/]")

    def show_result(self, success: bool, message: str = ""):
        """顯示動作結果"""
        if success:
            self.console.print(f"    [green]✓ OK[/] {message}")
        else:
            self.console.print(f"    [red]✗ Failed[/] {message}")

    def show_outputs(self, outputs: dict):
        """顯示輸出檔案"""
        if not outputs:
            return

        table = Table(
            title="[bold]Output Files[/]",
            box=ROUNDED,
            border_style="green"
        )
        table.add_column("Format", style="bold")
        table.add_column("Path", style="cyan")
        table.add_column("Status", justify="center")

        for fmt, info in outputs.items():
            if info:
                status = "[green]✓[/]" if info.get("success") else "[red]✗[/]"
                path = info.get("path", "N/A")
                extra = ""
                if fmt == "slides" and info.get("slides_count"):
                    extra = f" ({info['slides_count']} slides)"
                table.add_row(fmt.upper(), path + extra, status)

        self.console.print()
        self.console.print(table)

    def show_verification(self, verification: dict):
        """顯示驗證結果"""
        table = Table(
            title="[bold]Verification Results[/]",
            box=ROUNDED,
            border_style="blue"
        )
        table.add_column("Rule", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Message")

        for r in verification.get("results", []):
            status = "[green]PASS[/]" if r["passed"] else "[red]FAIL[/]"
            rule = r["rule"].replace("_", " ").title()
            table.add_row(rule, status, r["message"])

        self.console.print()
        self.console.print(table)

    def show_final_result(self, success: bool, run_id: str, quality_score: float = None):
        """顯示最終結果"""
        if success:
            panel = Panel(
                f"[bold green]Task Completed Successfully![/]\n\n"
                f"Run ID: [cyan]{run_id}[/]\n"
                + (f"Quality Score: [yellow]{quality_score:.2f}[/]" if quality_score else ""),
                title="[bold green]✓ Success[/]",
                border_style="green",
                box=DOUBLE
            )
        else:
            panel = Panel(
                f"[bold red]Task Completed with Issues[/]\n\n"
                f"Run ID: [cyan]{run_id}[/]",
                title="[bold red]✗ Failed[/]",
                border_style="red",
                box=DOUBLE
            )
        self.console.print()
        self.console.print(panel)

    def show_suggestions(self, suggestions: list):
        """顯示改進建議"""
        if not suggestions:
            return

        self.console.print("\n[bold yellow]💡 Suggestions for Improvement:[/]")
        for i, s in enumerate(suggestions[:3], 1):  # 只顯示前 3 個
            # 截斷過長的建議
            display_s = s[:80] + "..." if len(s) > 80 else s
            self.console.print(f"  {i}. [dim]{display_s}[/]")


class ProgressUI:
    """進度條 UI"""

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            console=console
        )
        self.task_id = None

    def start(self, description: str, total: int = 100):
        """開始進度"""
        self.progress.start()
        self.task_id = self.progress.add_task(description, total=total)

    def update(self, advance: int = 1, description: str = None):
        """更新進度"""
        if self.task_id is not None:
            self.progress.update(self.task_id, advance=advance, description=description)

    def finish(self):
        """完成進度"""
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=100)
        self.progress.stop()


def create_status_panel(phase: str, step: str, iteration: int, sources: int) -> Panel:
    """建立狀態面板"""
    content = f"""
[bold]Phase:[/] {phase}
[bold]Step:[/] {step}
[bold]Iteration:[/] {iteration}/20
[bold]Sources:[/] {sources}
    """
    return Panel(content, title="[bold cyan]Status[/]", border_style="cyan")


# 快速輔助函數
def success(message: str):
    console.print(f"[bold green]✓[/] {message}")

def error(message: str):
    console.print(f"[bold red]✗[/] {message}")

def warning(message: str):
    console.print(f"[bold yellow]![/] {message}")

def info(message: str):
    console.print(f"[bold blue]ℹ[/] {message}")


# 測試用
if __name__ == "__main__":
    print_banner()
    print_config("Python asyncio 基礎教學", "deepseek-chat", "all", "dark")
    print_agents()

    ui = MonusUI()
    ui.start_run("2026-01-02_123456_test", "Python asyncio 基礎教學")

    ui.update_phase("planning")
    ui.update_step("Creating initial plan", "done")

    ui.update_phase("searching")
    ui.show_action("browser.search", "Python asyncio tutorial 入門")
    ui.show_result(True, "Found 10 results")
    ui.update_sources(5)

    ui.update_iteration(5, 20)

    ui.update_phase("rendering")
    ui.update_step("Generating PDF", "done")
    ui.update_step("Generating Slides", "done")
    ui.update_step("Generating Web", "done")

    ui.show_outputs({
        "pdf": {"success": True, "path": "runs/test/report.pdf"},
        "slides": {"success": True, "path": "runs/test/slides.html", "slides_count": 6},
        "web": {"success": True, "path": "runs/test/index.html"},
    })

    ui.show_verification({
        "passed": True,
        "results": [
            {"rule": "_has_min_sources", "passed": True, "message": "Sources: 5/5"},
            {"rule": "_report_exists", "passed": True, "message": "Report exists"},
        ]
    })

    ui.show_suggestions([
        "增加更多程式碼範例",
        "補充常見問題解答",
        "加入視覺化圖表"
    ])

    ui.show_final_result(True, "2026-01-02_123456_test", 0.85)
