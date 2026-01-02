"""
Reasoner Agent - 推理思考
在每個步驟執行前，生成 Thought（為什麼要做這一步）
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Reasoner:
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

    def generate_thought(self, goal: str, current_step: dict, history: list) -> dict:
        """
        為當前步驟生成推理思考
        返回 {thought, should_proceed, alternative_action}
        """
        history_text = ""
        for h in history[-5:]:
            history_text += f"- {h.get('action', 'N/A')}: {h.get('observation', 'N/A')[:100]}...\n"

        prompt = f"""你是一個推理 Agent。根據當前情況，分析下一步行動的必要性。

目標: {goal}

當前步驟:
- 標題: {current_step.get('title', 'N/A')}
- 工具: {current_step.get('tool', 'N/A')}
- 輸入: {current_step.get('input', 'N/A')}

執行歷史:
{history_text if history_text else '（尚無歷史）'}

請分析:
1. 為什麼需要執行這個步驟？
2. 這個步驟是否合理？
3. 是否有更好的替代方案？

回覆純 JSON 格式:
{{
  "thought": "這一步的推理原因...",
  "should_proceed": true,
  "alternative_action": null
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "thought": f"Auto proceed: {str(e)[:50]}",
                "should_proceed": True,
                "alternative_action": None
            }

    def analyze_context(self, goal: str, sources: list, current_knowledge: str) -> dict:
        """
        分析當前收集的資訊是否足夠
        返回 {sufficient, missing_aspects, next_focus}
        """
        sources_text = "\n".join([f"- {s.get('title', 'N/A')}" for s in sources[:10]])

        prompt = f"""目標: {goal}

已收集的來源:
{sources_text}

當前知識摘要:
{current_knowledge[:2000]}

請分析:
1. 目前收集的資訊是否足以回答目標問題？
2. 還缺少哪些面向的資訊？
3. 下一步應該關注什麼？

回覆純 JSON 格式:
{{
  "sufficient": true,
  "missing_aspects": [],
  "next_focus": ""
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "sufficient": True,
                "missing_aspects": [],
                "next_focus": goal
            }

    def resolve_conflict(self, goal: str, conflicting_info: list[dict]) -> dict:
        """
        處理資訊矛盾
        返回 {resolution, reasoning, confidence}
        """
        conflicts_text = ""
        for i, info in enumerate(conflicting_info):
            conflicts_text += f"來源 {i+1} ({info.get('source', 'N/A')}): {info.get('content', 'N/A')[:200]}\n"

        prompt = f"""你需要處理資訊矛盾。

目標: {goal}

矛盾的資訊:
{conflicts_text}

請根據以下優先級進行決策:
1. 官方來源 > 第三方來源
2. 最新時間 > 舊時間
3. 多數共識 > 少數意見

回覆純 JSON 格式:
{{
  "resolution": "採納的結論...",
  "reasoning": "為什麼這樣決定...",
  "confidence": 0.8
}}"""

        try:
            content = self._chat(prompt)

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception as e:
            return {
                "resolution": conflicting_info[0].get("content", "") if conflicting_info else "",
                "reasoning": f"Auto resolve: {str(e)[:50]}",
                "confidence": 0.5
            }
