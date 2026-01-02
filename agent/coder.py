"""
Coder Agent - 程式碼生成 Agent
持續呼叫 LLM 生成/修改程式碼
"""
import json
import os
from typing import Optional, Generator
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Coder:
    """
    程式碼生成 Agent
    負責理解需求、規劃檔案結構、生成程式碼
    """

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        self.conversation_history = []

    def _call_llm(self, messages: list, stream: bool = False):
        """呼叫 LLM"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                stream=stream
            )

            if stream:
                return response
            else:
                return response.choices[0].message.content

        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_task(self, goal: str, template: str = "html") -> dict:
        """
        分析任務，產生專案計畫

        Args:
            goal: 使用者目標
            template: 專案模板 (html, vite-react, python, node)

        Returns:
            {project_name, files_to_create, steps}
        """
        system_prompt = """你是一個專業的程式碼架構師。
分析使用者需求，規劃專案結構。

回傳 JSON 格式：
{
    "project_name": "專案名稱（英文，用底線分隔）",
    "description": "專案描述",
    "files": [
        {"path": "檔案路徑", "description": "檔案說明"}
    ],
    "steps": [
        {"step": 1, "action": "create_file", "file": "檔案路徑", "description": "說明"}
    ]
}

注意：
1. 專案名稱用英文小寫加底線
2. 列出所有需要建立的檔案
3. 步驟要按順序，從基礎結構開始"""

        template_hints = {
            "html": "使用純 HTML + CSS + JavaScript，不需要建置工具",
            "vite-react": "使用 Vite + React，現代化前端架構",
            "python": "使用 Python，可搭配 Flask 或純腳本",
            "node": "使用 Node.js"
        }

        user_prompt = f"""使用者需求：{goal}

專案模板：{template}
模板說明：{template_hints.get(template, template)}

請分析並規劃專案結構。回傳 JSON。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_llm(messages)

        try:
            # 嘗試解析 JSON
            # 處理可能的 markdown code block
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except:
            # 解析失敗，返回基本結構
            return {
                "project_name": "monus_project",
                "description": goal,
                "files": [
                    {"path": "index.html", "description": "主頁面"},
                    {"path": "style.css", "description": "樣式"},
                    {"path": "script.js", "description": "腳本"}
                ],
                "steps": [
                    {"step": 1, "action": "create_file", "file": "index.html", "description": "建立主頁面"},
                    {"step": 2, "action": "create_file", "file": "style.css", "description": "建立樣式"},
                    {"step": 3, "action": "create_file", "file": "script.js", "description": "建立腳本"}
                ]
            }

    def generate_file(self, goal: str, file_path: str, file_description: str,
                      existing_files: dict = None, context: str = "") -> Generator[str, None, None]:
        """
        生成單一檔案內容（串流輸出）

        Args:
            goal: 整體目標
            file_path: 檔案路徑
            file_description: 檔案說明
            existing_files: 已存在的檔案 {path: content}
            context: 額外上下文

        Yields:
            程式碼片段（串流）
        """
        system_prompt = """你是一個專業的程式碼開發者。
根據需求生成完整、可運行的程式碼。

規則：
1. 只輸出程式碼，不要解釋
2. 程式碼要完整可運行
3. 加入適當的註解
4. 使用現代化的最佳實踐
5. 不要使用 markdown code block，直接輸出程式碼內容"""

        # 構建已存在檔案的上下文
        files_context = ""
        if existing_files:
            files_context = "\n\n已存在的檔案：\n"
            for path, content in existing_files.items():
                # 只顯示前 500 字元避免太長
                preview = content[:500] + "..." if len(content) > 500 else content
                files_context += f"\n--- {path} ---\n{preview}\n"

        user_prompt = f"""專案目標：{goal}

現在需要生成：{file_path}
檔案說明：{file_description}
{files_context}
{context}

請生成完整的 {file_path} 檔案內容。直接輸出程式碼，不要 markdown。"""

        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[-4:],  # 保留最近 4 輪對話
            {"role": "user", "content": user_prompt}
        ]

        # 串流輸出
        response_stream = self._call_llm(messages, stream=True)

        full_response = ""
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        # 記錄對話歷史
        self.conversation_history.append({"role": "user", "content": user_prompt})
        self.conversation_history.append({"role": "assistant", "content": full_response})

    def modify_file(self, goal: str, file_path: str, current_content: str,
                    modification_request: str) -> Generator[str, None, None]:
        """
        修改現有檔案（串流輸出）

        Args:
            goal: 整體目標
            file_path: 檔案路徑
            current_content: 目前內容
            modification_request: 修改要求

        Yields:
            修改後的程式碼（串流）
        """
        system_prompt = """你是一個專業的程式碼開發者。
根據要求修改程式碼。

規則：
1. 只輸出修改後的完整程式碼
2. 不要解釋
3. 保持原有的風格和結構
4. 不要使用 markdown code block"""

        user_prompt = f"""專案目標：{goal}

檔案：{file_path}

目前內容：
{current_content}

修改要求：{modification_request}

請輸出修改後的完整檔案內容。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_stream = self._call_llm(messages, stream=True)

        full_response = ""
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

    def fix_error(self, file_path: str, current_content: str,
                  error_message: str) -> Generator[str, None, None]:
        """
        修復錯誤（串流輸出）

        Args:
            file_path: 檔案路徑
            current_content: 目前內容
            error_message: 錯誤訊息

        Yields:
            修復後的程式碼（串流）
        """
        system_prompt = """你是一個專業的程式碼除錯專家。
分析錯誤並修復程式碼。

規則：
1. 分析錯誤原因
2. 輸出修復後的完整程式碼
3. 不要使用 markdown code block"""

        user_prompt = f"""檔案：{file_path}

目前內容：
{current_content}

錯誤訊息：
{error_message}

請修復錯誤，輸出完整的修復後程式碼。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_stream = self._call_llm(messages, stream=True)

        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat(self, message: str, context: dict = None) -> Generator[str, None, None]:
        """
        一般對話（用於澄清需求等）

        Args:
            message: 使用者訊息
            context: 上下文（專案資訊等）

        Yields:
            回應（串流）
        """
        system_prompt = """你是一個友善的程式開發助手。
幫助使用者澄清需求、解答問題。
回答要簡潔明確。"""

        context_str = ""
        if context:
            context_str = f"\n\n專案上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        messages = [
            {"role": "system", "content": system_prompt + context_str},
            *self.conversation_history[-6:],
            {"role": "user", "content": message}
        ]

        response_stream = self._call_llm(messages, stream=True)

        full_response = ""
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": full_response})

    def clear_history(self):
        """清除對話歷史"""
        self.conversation_history = []
