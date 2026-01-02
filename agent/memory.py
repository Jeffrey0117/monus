"""
Memory - 任務狀態存取
這是 Monus 的外接大腦，不依賴 prompt 記憶
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import re


class Memory:
    def __init__(self, runs_dir: str = "runs"):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(exist_ok=True)
        self.current_run: Optional[Path] = None
        self.task_state: dict = {}

    def create_run(self, goal: str) -> str:
        """
        建立新的執行記錄目錄
        返回 run_id
        """
        # 產生 run_id: 日期_目標簡稱
        date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        # 清理目標文字作為目錄名
        goal_slug = re.sub(r'[^\w\s-]', '', goal)[:30].strip().replace(' ', '_')
        run_id = f"{date_str}_{goal_slug}"

        self.current_run = self.runs_dir / run_id
        self.current_run.mkdir(exist_ok=True)

        # 初始化 task.json
        self.task_state = {
            "goal": goal,
            "status": "running",
            "steps": [],
            "artifacts": {
                "sources": "sources.json",
                "report": "report.md"
            },
            "memory": {
                "keywords_tried": [],
                "failed_attempts": [],
                "sources_collected": []
            }
        }

        self._save_task()
        self._log(f"Task created: {goal}")

        return run_id

    def _save_task(self):
        """儲存 task.json"""
        if self.current_run:
            task_path = self.current_run / "task.json"
            task_path.write_text(
                json.dumps(self.task_state, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    def load_run(self, run_id: str) -> dict:
        """載入現有的執行記錄"""
        self.current_run = self.runs_dir / run_id
        task_path = self.current_run / "task.json"

        if task_path.exists():
            self.task_state = json.loads(task_path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"Task not found: {run_id}")

        return self.task_state

    def get_state(self) -> dict:
        """取得當前任務狀態"""
        return self.task_state

    def add_step(self, title: str, tool: str, input_data: str) -> int:
        """
        新增執行步驟
        返回 step_id
        """
        step_id = len(self.task_state["steps"]) + 1

        step = {
            "id": step_id,
            "title": title,
            "tool": tool,
            "input": input_data,
            "status": "pending",
            "output": None,
            "evidence": []
        }

        self.task_state["steps"].append(step)
        self._save_task()
        self._log(f"Step added: [{step_id}] {title}")

        return step_id

    def update_step(self, step_id: int, status: str, output: Any = None, evidence: list = None):
        """更新步驟狀態"""
        for step in self.task_state["steps"]:
            if step["id"] == step_id:
                step["status"] = status
                if output is not None:
                    step["output"] = output
                if evidence is not None:
                    step["evidence"] = evidence
                break

        self._save_task()
        self._log(f"Step [{step_id}] updated: {status}")

    def get_pending_steps(self) -> list:
        """取得待處理的步驟"""
        return [s for s in self.task_state["steps"] if s["status"] == "pending"]

    def get_current_step(self) -> Optional[dict]:
        """取得當前正在執行的步驟"""
        for step in self.task_state["steps"]:
            if step["status"] == "running":
                return step
        pending = self.get_pending_steps()
        return pending[0] if pending else None

    def add_source(self, title: str, url: str, snippet: str = ""):
        """記錄來源"""
        source = {
            "title": title,
            "url": url,
            "snippet": snippet
        }

        if "sources_collected" not in self.task_state["memory"]:
            self.task_state["memory"]["sources_collected"] = []

        # 避免重複
        existing_urls = [s["url"] for s in self.task_state["memory"]["sources_collected"]]
        if url not in existing_urls:
            self.task_state["memory"]["sources_collected"].append(source)
            self._save_task()
            self._log(f"Source added: {title}")

    def get_sources(self) -> list:
        """取得所有來源"""
        return self.task_state["memory"].get("sources_collected", [])

    def add_keyword(self, keyword: str):
        """記錄已嘗試的關鍵字"""
        if keyword not in self.task_state["memory"]["keywords_tried"]:
            self.task_state["memory"]["keywords_tried"].append(keyword)
            self._save_task()

    def add_failed_attempt(self, description: str):
        """記錄失敗嘗試"""
        self.task_state["memory"]["failed_attempts"].append(description)
        self._save_task()
        self._log(f"Failed attempt: {description}")

    def set_status(self, status: str):
        """設定任務狀態"""
        self.task_state["status"] = status
        self._save_task()
        self._log(f"Task status: {status}")

    def save_sources_json(self):
        """儲存 sources.json"""
        if self.current_run:
            sources_path = self.current_run / "sources.json"
            sources_path.write_text(
                json.dumps(self.get_sources(), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    def save_report(self, content: str):
        """儲存報告"""
        if self.current_run:
            report_path = self.current_run / "report.md"
            report_path.write_text(content, encoding="utf-8")
            self._log("Report saved")

    def _log(self, message: str):
        """寫入 log"""
        if self.current_run:
            log_path = self.current_run / "logs.txt"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")

    def get_run_path(self) -> Optional[Path]:
        """取得當前執行目錄"""
        return self.current_run
