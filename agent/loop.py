"""
Agent Loop - Monus 的心臟
Decide / Act / Observe / Verify / Render
整合 5 個 Agent: Planner, Reasoner, Evaluator, Verifier, Renderer
"""
import asyncio
from typing import Optional
from .planner import Planner
from .reasoner import Reasoner
from .evaluator import Evaluator
from .verifier import Verifier
from .renderer import Renderer
from .memory import Memory

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.browser import BrowserTool
from tools.fs import FileTool
from tools.code import CodeTool
from tools.pdf import PDFTool
from tools.slides import SlidesTool
from tools.web import WebTool


class AgentLoop:
    def __init__(
        self,
        memory: Memory,
        planner: Planner,
        reasoner: Reasoner,
        evaluator: Evaluator,
        verifier: Verifier,
        max_iterations: int = 20,
        ui = None  # MonusUI 實例（可選）
    ):
        self.memory = memory
        self.planner = planner
        self.reasoner = reasoner
        self.evaluator = evaluator
        self.verifier = verifier
        self.max_iterations = max_iterations
        self.ui = ui  # UI 介面

        # 初始化 Renderer Agent
        self.renderer = Renderer()

        # 初始化工具
        self.browser = BrowserTool()
        self.fs = FileTool()
        self.code = CodeTool()
        self.pdf = PDFTool()
        self.slides = SlidesTool()
        self.web = WebTool()

        # 執行歷史（供 Reasoner 使用）
        self.history: list[dict] = []
        # 內容暫存（用於產生報告）
        self.collected_contents: list[str] = []
        # 輸出結果
        self.outputs: dict = {}

    def _log(self, message: str, level: str = "info"):
        """統一的日誌輸出"""
        if self.ui:
            # 使用 Rich UI
            if level == "phase":
                self.ui.update_phase(message)
            elif level == "step":
                self.ui.update_step(message, "running")
            elif level == "done":
                self.ui.update_step(message, "done")
            elif level == "fail":
                self.ui.update_step(message, "failed")
            else:
                pass  # 其他由 UI 方法處理
        else:
            # 基本輸出
            print(message)

    async def run(self, goal: str, output_format: str = "pdf", theme: str = "default") -> dict:
        """
        執行主循環
        返回 {success, run_id, report_path, verification, outputs}

        Args:
            goal: 任務目標
            output_format: 輸出格式 (pdf/slides/web/all)
            theme: 主題 (default/dark/minimal)
        """
        self.output_format = output_format
        self.theme = theme
        # 1. 建立執行記錄
        run_id = self.memory.create_run(goal)

        if self.ui:
            self.ui.start_run(run_id, goal)
        else:
            print(f"[Monus] Starting run: {run_id}")
            print(f"[Monus] Goal: {goal}")

        # 2. Planner: 建立初始計畫
        try:
            self._log("planning", "phase")
            initial_steps = self.planner.create_initial_plan(goal)
            for step in initial_steps:
                self.memory.add_step(
                    title=step["title"],
                    tool=step["tool"],
                    input_data=step["input"]
                )
            self._log(f"Plan created with {len(initial_steps)} steps", "done")
        except Exception as e:
            self._log(f"Error creating plan: {e}", "fail")
            self.memory.set_status("failed")
            return {"success": False, "error": str(e)}

        # 3. 主循環
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            if self.ui:
                self.ui.update_iteration(iteration, self.max_iterations)
            else:
                print(f"\n[Monus] === Iteration {iteration}/{self.max_iterations} ===")

            # 檢查是否有足夠來源可以生成報告
            sources = self.memory.get_sources()

            if self.ui:
                self.ui.update_sources(len(sources))

            # 快速模式：更積極地生成報告
            if len(sources) >= 5 and iteration >= 5:
                self._log("writing", "phase")
                await self._generate_final_report(goal)
                break

            # Planner: 決定下一步
            task_state = self.memory.get_state()
            action = self.planner.decide(task_state)

            if action is None:
                self._log("No more actions needed", "done")
                break

            # 顯示動作
            if self.ui:
                self.ui.show_action(action['tool'], action['input'])
            else:
                print(f"[Planner] Next action: {action['tool']} - {action.get('reason', '')}")

            # 特殊處理：產生報告
            if action["tool"] == "generate_report":
                await self._generate_final_report(goal)
                break

            # 快速模式：跳過 Reasoner 和 Evaluator 的冗長分析
            # 只在有問題時才啟用深度分析
            fast_mode = True  # 加速執行

            # Act: 直接執行行動
            result = await self._execute_action(action)
            observation = str(result)[:500]

            # 記錄歷史
            self.history.append({
                "action": f"{action['tool']}: {action['input']}",
                "observation": observation,
                "thought": ""
            })

            # 快速評估：根據結果判斷成功與否
            if fast_mode:
                # 簡單判斷是否成功
                is_success = True
                if isinstance(result, dict) and result.get("error"):
                    is_success = False
                elif isinstance(result, list) and len(result) == 0:
                    is_success = False
                elif isinstance(result, list) and result and "error" in result[0]:
                    is_success = False

                evaluation = {"success": is_success, "analysis": "Fast mode", "should_retry": not is_success}
                if self.ui:
                    self.ui.show_result(is_success)
                else:
                    print(f"[Fast] Action {'OK' if is_success else 'FAILED'}")

            # Observe: 根據評估更新狀態
            step_id = action.get("step_id")
            if step_id:
                if evaluation.get("success", False):
                    self.memory.update_step(step_id, "done", output=observation)
                else:
                    if evaluation.get("should_retry", False):
                        if not self.ui:
                            print("[Evaluator] Suggesting retry")
                    else:
                        self.memory.update_step(step_id, "failed", output=observation)
                        self.memory.add_failed_attempt(f"Step {step_id}: {evaluation.get('analysis', 'Failed')}")

            # 如果 Evaluator 建議額外行動
            next_action = evaluation.get("next_action")
            if next_action and isinstance(next_action, dict):
                self.memory.add_step(
                    title=f"Recovery: {next_action.get('tool', 'N/A')}",
                    tool=next_action.get("tool", ""),
                    input_data=next_action.get("input", "")
                )
                if not self.ui:
                    print(f"[Evaluator] Added recovery step: {next_action.get('tool', 'N/A')}")

            # 處理搜尋結果
            if action["tool"] == "browser.search":
                await self._process_search_results(result, action["input"])

            # 處理頁面開啟後提取
            if action["tool"] == "browser.open" and result.get("success"):
                self.memory.add_step(
                    title="Extract page content",
                    tool="browser.extract",
                    input_data="readability"
                )

            # 處理頁面提取
            if action["tool"] == "browser.extract":
                await self._process_extraction(result, goal)

        # 4. Verifier: 驗證結果
        report_content = ""
        report_path = self.memory.get_run_path() / "report.md"
        if report_path.exists():
            report_content = report_path.read_text(encoding="utf-8")

        self._log("verifying", "phase")
        verification = self.verifier.verify(self.memory.get_state(), report_content)

        # Evaluator: 最終評估
        final_eval = self.evaluator.evaluate_task_completion(
            goal, self.memory.get_state(), report_content
        )

        if not self.ui:
            print(f"\n[Evaluator] Final quality score: {final_eval.get('quality_score', 'N/A')}")
            if final_eval.get("suggestions"):
                print(f"[Evaluator] Suggestions: {final_eval.get('suggestions', [])}")

        # 5. 設定最終狀態
        if verification["passed"]:
            self.memory.set_status("completed")
            if not self.ui:
                print("\n[Monus] Task completed successfully!")
        else:
            self.memory.set_status("failed")
            if not self.ui:
                print("\n[Monus] Task completed with verification failures:")
                for r in verification["results"]:
                    status = "[PASS]" if r["passed"] else "[FAIL]"
                    print(f"  {status} {r['rule']}: {r['message']}")

        # 6. 儲存來源
        self.memory.save_sources_json()

        # 7. 關閉瀏覽器和 PDF 工具
        await self.browser.close()
        await self.pdf.close()

        return {
            "success": verification["passed"],
            "run_id": run_id,
            "report_path": str(report_path),
            "verification": verification,
            "final_evaluation": final_eval,
            "outputs": self.outputs
        }

    async def _execute_action(self, action: dict) -> dict:
        """執行指定的行動"""
        tool = action["tool"]
        input_data = action["input"]

        try:
            if tool == "browser.search":
                self.memory.add_keyword(input_data)
                return await self.browser.search(input_data)

            elif tool == "browser.open":
                return await self.browser.open(input_data)

            elif tool == "browser.extract":
                return await self.browser.extract()

            elif tool == "fs.write":
                parts = input_data.split("|", 1)
                if len(parts) == 2:
                    return self.fs.write(parts[0], parts[1])
                return {"success": False, "error": "Invalid fs.write format"}

            elif tool == "code.run":
                return self.code.run(input_data)

            else:
                return {"success": False, "error": f"Unknown tool: {tool}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_search_results(self, results: list, keyword: str):
        """處理搜尋結果"""
        if isinstance(results, list):
            for item in results[:5]:
                if "error" not in item and item.get("url"):
                    self.memory.add_source(
                        title=item.get("title", "Untitled"),
                        url=item["url"],
                        snippet=item.get("snippet", "")
                    )

                    self.memory.add_step(
                        title=f"Open: {item.get('title', 'Page')[:30]}",
                        tool="browser.open",
                        input_data=item["url"]
                    )

            if not self.ui:
                print(f"[Monus] Found {len(results)} results for '{keyword}'")

    async def _process_extraction(self, result: dict, goal: str):
        """處理頁面提取結果（快速模式）"""
        if result.get("content"):
            content = result["content"]
            # 快速模式：直接收集內容，跳過 LLM 相關性分析
            self.collected_contents.append(content)
            if not self.ui:
                print(f"[Fast] Content collected ({len(content)} chars)")

    async def _generate_final_report(self, goal: str):
        """產生最終報告 + 多格式輸出（使用 Renderer Agent 智能選擇版面）"""
        self._log("writing", "phase")

        sources = self.memory.get_sources()

        # 如果沒有收集到內容，使用來源摘要
        contents_to_use = self.collected_contents.copy()
        if not contents_to_use:
            for s in sources[:10]:
                snippet = s.get("snippet", "")
                if snippet:
                    contents_to_use.append(f"來源: {s.get('title', 'Unknown')}\n{snippet}")

        # 使用 Renderer Agent 分析內容類型
        self._log("Analyzing content type", "step")
        content_type = self.planner.analyze_content_type(goal, contents_to_use)
        self._log(f"Content type: {content_type}", "done")

        # 產生報告（使用對應的結構模板）
        self._log("Generating report content", "step")
        report = self.planner.generate_report(goal, sources, contents_to_use, content_type)

        # 儲存 Markdown
        self.memory.save_report(report)
        self._log("Markdown saved", "done")

        run_path = self.memory.get_run_path()
        title = goal[:50]

        # 使用 Renderer Agent 分析最佳版面配置
        self._log("Analyzing layout", "step")
        layout_analysis = self.renderer.analyze_content(report, goal)
        recommended_layout = layout_analysis.get("recommended_layout", "sidebar-nav")
        recommended_theme = layout_analysis.get("color_theme", self.theme)

        if not self.ui:
            print(f"[Renderer] Recommended layout: {recommended_layout}")
            print(f"[Renderer] Recommended theme: {recommended_theme}")
            print(f"[Renderer] Reason: {layout_analysis.get('reasoning', 'N/A')}")

        self._log(f"Layout: {recommended_layout}, Theme: {recommended_theme}", "done")

        # 根據 output_format 生成對應格式
        self._log("rendering", "phase")
        fmt = self.output_format

        # PDF
        if fmt in ["pdf", "all"]:
            self._log("Generating PDF", "step")
            pdf_path = str(run_path / "report.pdf")
            pdf_result = await self.pdf.generate(report, pdf_path, title=title)
            self.outputs["pdf"] = pdf_result
            if pdf_result["success"]:
                self._log("PDF generated", "done")
            else:
                self._log(f"PDF failed: {pdf_result.get('error', 'Unknown')}", "fail")

        # Slides
        if fmt in ["slides", "all"]:
            self._log("Generating Slides", "step")
            slides_md = self._convert_to_slides_md(report)
            slides_path = str(run_path / "slides.html")
            # 使用 Renderer 推薦的主題
            slides_result = await self.slides.generate(
                slides_md, slides_path,
                title=title,
                theme=recommended_theme if self.theme == "default" else self.theme
            )
            self.outputs["slides"] = slides_result
            if slides_result["success"]:
                self._log(f"Slides generated ({slides_result['slides_count']} slides)", "done")
            else:
                self._log(f"Slides failed: {slides_result.get('error', 'Unknown')}", "fail")

        # Web - 使用 Renderer Agent 的智能版面選擇
        if fmt in ["web", "all"]:
            self._log("Generating Web page", "step")
            web_path = str(run_path / "index.html")
            # 使用 Renderer 推薦的版面和主題
            web_result = await self.web.generate(
                report, web_path,
                title=title,
                style=recommended_layout,  # 使用智能推薦的版面
                theme=recommended_theme if self.theme == "default" else self.theme,
                goal=goal
            )
            self.outputs["web"] = web_result
            if web_result["success"]:
                self._log(f"Web page generated (layout: {web_result.get('layout', 'N/A')})", "done")
            else:
                self._log(f"Web failed: {web_result.get('error', 'Unknown')}", "fail")

    def _convert_to_slides_md(self, report: str) -> str:
        """將報告轉換為簡報格式 Markdown（用 --- 分隔）"""
        lines = report.split('\n')
        slides_parts = []
        current_slide = []

        for line in lines:
            # 遇到 ## 標題就分割
            if line.startswith('## '):
                if current_slide:
                    slides_parts.append('\n'.join(current_slide))
                current_slide = [line]
            else:
                current_slide.append(line)

        if current_slide:
            slides_parts.append('\n'.join(current_slide))

        # 用 --- 連接
        return '\n---\n'.join(slides_parts)
