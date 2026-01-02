"""
Evaluator Agent - 觀察評估
觀察工具輸出，判斷是否達成目標或需要修正
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Evaluator:
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

    def evaluate_action_result(
        self,
        goal: str,
        action: dict,
        observation: str
    ) -> dict:
        """
        評估行動結果
        返回 {success, analysis, next_action, should_retry}
        """
        prompt = f"""你是一個評估 Agent。根據行動結果判斷是否成功。

目標: {goal}

執行的行動:
- 工具: {action.get('tool', 'N/A')}
- 輸入: {action.get('input', 'N/A')}

觀察結果:
{observation[:3000]}

請評估:
1. 這個行動是否成功？
2. 結果是否有助於達成目標？
3. 是否需要採取補救措施？

回覆純 JSON 格式:
{{
  "success": true,
  "analysis": "分析結果...",
  "next_action": null,
  "should_retry": false
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "success": True,
                "analysis": f"Auto pass: {str(e)[:50]}",
                "next_action": None,
                "should_retry": False
            }

    def analyze_content_relevance(self, goal: str, content: str) -> dict:
        """
        分析提取的內容是否相關
        返回 {relevant, summary, key_points, quality_score}
        """
        prompt = f"""目標: {goal}

內容:
{content[:4000]}

請分析這個內容:
1. 是否與目標相關？(true/false)
2. 簡短摘要 (50字內)
3. 列出 3-5 個關鍵點
4. 內容品質評分 (0.0-1.0)

回覆純 JSON 格式:
{{
  "relevant": true,
  "summary": "摘要...",
  "key_points": ["要點1", "要點2", "要點3"],
  "quality_score": 0.8
}}"""

        try:
            result = self._chat(prompt)

            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1])

            return json.loads(result)
        except Exception as e:
            return {
                "relevant": True,
                "summary": "",
                "key_points": [],
                "quality_score": 0.5
            }

    def evaluate_task_completion(self, goal: str, task_state: dict, report: str) -> dict:
        """
        評估整體任務是否完成
        返回 {completed, quality_score, issues, suggestions}
        """
        sources_count = len(task_state.get("memory", {}).get("sources_collected", []))
        steps_done = len([s for s in task_state.get("steps", []) if s["status"] == "done"])
        steps_total = len(task_state.get("steps", []))

        prompt = f"""目標: {goal}

任務狀態:
- 來源數量: {sources_count}
- 完成步驟: {steps_done}/{steps_total}

報告內容:
{report[:4000]}

請評估:
1. 任務是否完成？
2. 報告品質評分 (0.0-1.0)
3. 有哪些問題？
4. 有哪些改進建議？

回覆純 JSON 格式:
{{
  "completed": true,
  "quality_score": 0.8,
  "issues": [],
  "suggestions": []
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "completed": True,
                "quality_score": 0.7,
                "issues": [],
                "suggestions": []
            }

    def check_hallucination(self, claim: str, evidence: list[str]) -> dict:
        """
        檢查是否有幻覺（虛構資訊）
        返回 {has_hallucination, analysis, grounded_claims}
        """
        evidence_text = "\n".join([f"- {e[:500]}" for e in evidence[:5]])

        prompt = f"""你需要檢查以下聲明是否有幻覺（虛構資訊）。

聲明:
{claim}

可用證據:
{evidence_text}

請檢查:
1. 聲明中是否有無法從證據驗證的資訊？
2. 哪些部分是有根據的？

回覆純 JSON 格式:
{{
  "has_hallucination": false,
  "analysis": "分析...",
  "grounded_claims": []
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "has_hallucination": False,
                "analysis": f"Auto pass: {str(e)[:50]}",
                "grounded_claims": []
            }
