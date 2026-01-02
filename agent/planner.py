"""
Planner Agent - 任務拆解
將 User Prompt 拆解為 Step[]
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Planner:
    def __init__(self, model: str = "deepseek-chat"):
        self.model_name = model
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

    def _chat(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    def create_initial_plan(self, goal: str) -> list[dict]:
        """
        根據目標建立初始計畫
        返回 [{title, tool, input}, ...]
        """
        prompt = f"""你是一個研究助理 AI。用戶給你一個研究目標，你需要規劃執行步驟。

目標: {goal}

可用的工具:
- browser.search: 搜尋網路資料（輸入搜尋關鍵字）
- browser.open: 開啟特定網頁（輸入 URL）
- browser.extract: 提取當前頁面內容
- fs.write: 寫入檔案
- code.run: 執行命令

請規劃 3-5 個步驟來完成這個研究任務。
每個步驟格式:
- title: 步驟標題
- tool: 使用的工具
- input: 工具輸入

回覆純 JSON 格式（不要 markdown 包裹）:
[
  {{"title": "步驟1標題", "tool": "browser.search", "input": "搜尋關鍵字"}},
  ...
]"""

        content = self._chat(prompt)

        # 處理可能的 markdown 包裹
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
            if content.startswith("json"):
                content = content[4:]

        return json.loads(content)

    def decide(self, task_state: dict) -> dict | None:
        """
        根據當前狀態決定下一步行動
        返回 {tool, input, reason} 或 None（如果任務完成）
        """
        goal = task_state.get("goal", "")
        steps = task_state.get("steps", [])
        memory = task_state.get("memory", {})

        # 找出待處理的步驟
        pending = [s for s in steps if s["status"] == "pending"]

        # 如果沒有待處理步驟，檢查是否需要補充
        if not pending:
            sources = memory.get("sources_collected", [])

            # 來源不足，需要更多搜尋
            if len(sources) < 5:
                keywords_tried = memory.get("keywords_tried", [])
                return self._generate_new_search(goal, keywords_tried)

            # 來源足夠，可以產生報告
            return {
                "tool": "generate_report",
                "input": goal,
                "reason": "Enough sources collected, generating report"
            }

        # 返回下一個待處理步驟
        next_step = pending[0]
        return {
            "tool": next_step["tool"],
            "input": next_step["input"],
            "step_id": next_step["id"],
            "reason": next_step["title"]
        }

    def _generate_new_search(self, goal: str, keywords_tried: list) -> dict:
        """產生新的搜尋關鍵字"""
        prompt = f"""目標: {goal}
已嘗試的關鍵字: {keywords_tried}

請產生一個新的、不同角度的搜尋關鍵字來找到更多相關資料。
只回覆關鍵字本身，不要其他文字。"""

        new_keyword = self._chat(prompt)

        return {
            "tool": "browser.search",
            "input": new_keyword,
            "reason": f"Searching for more sources with: {new_keyword}"
        }

    def generate_report(self, goal: str, sources: list, contents: list) -> str:
        """
        根據收集的資料產生報告
        """
        sources_text = "\n".join([f"- {s['title']}: {s['url']}" for s in sources])
        contents_text = "\n\n---\n\n".join(contents[:5])

        prompt = f"""目標: {goal}

收集的來源:
{sources_text}

內容摘要:
{contents_text[:8000]}

請根據以上資料撰寫一份研究報告，格式如下:

# [標題]

## 摘要
[100-150字的摘要]

## 核心技術拆解
- [要點1]
- [要點2]
- [要點3]
...

## 系統架構
[描述系統架構]

## 優點與限制
[分析優缺點]

## 參考來源
[列出所有來源]

請用繁體中文撰寫，報告需超過 1000 字。"""

        return self._chat(prompt)
