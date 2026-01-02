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

    def analyze_content_type(self, goal: str, contents: list) -> str:
        """
        分析內容類型，決定最適合的報告格式
        返回: tutorial / comparison / report / reference / list / overview
        """
        preview = "\n".join(contents[:3])[:2000] if contents else ""

        prompt = f"""分析以下研究目標和內容，判斷最適合的報告類型。

目標: {goal}

內容預覽:
{preview}

可選類型:
- tutorial: 教學文章（有步驟、程式碼範例）
- comparison: 比較分析（對比多個選項）
- report: 研究報告（深度分析、學術風格）
- reference: 參考文件（API、技術規格）
- list: 列表彙整（推薦清單、排名）
- overview: 概述介紹（入門、基礎介紹）

只回覆類型 ID，不要其他文字。"""

        try:
            result = self._chat(prompt).lower().strip()
            valid_types = ["tutorial", "comparison", "report", "reference", "list", "overview"]
            if result in valid_types:
                return result
        except Exception:
            pass

        # 基於關鍵字的回退判斷
        goal_lower = goal.lower()
        if any(k in goal_lower for k in ["教學", "教程", "how to", "步驟", "tutorial"]):
            return "tutorial"
        elif any(k in goal_lower for k in ["比較", "對比", "vs", "差異"]):
            return "comparison"
        elif any(k in goal_lower for k in ["api", "參考", "reference", "文件"]):
            return "reference"
        elif any(k in goal_lower for k in ["推薦", "列表", "top", "最佳"]):
            return "list"
        elif any(k in goal_lower for k in ["什麼是", "介紹", "概述", "入門"]):
            return "overview"

        return "report"

    def generate_report(self, goal: str, sources: list, contents: list,
                        content_type: str = None) -> str:
        """
        根據收集的資料產生報告
        支援多種報告類型和格式
        """
        # 自動判斷內容類型
        if content_type is None:
            content_type = self.analyze_content_type(goal, contents)

        sources_text = "\n".join([f"- {s['title']}: {s['url']}" for s in sources])
        contents_text = "\n\n---\n\n".join(contents[:5])

        # 根據類型選擇報告結構
        structure = self._get_report_structure(content_type)

        prompt = f"""目標: {goal}
內容類型: {content_type}

收集的來源:
{sources_text}

內容摘要:
{contents_text[:8000]}

請根據以上資料撰寫一份{self._get_type_description(content_type)}。

{structure}

撰寫要求:
1. 使用繁體中文
2. 報告需超過 1000 字
3. 內容要有深度，不要泛泛而談
4. 適當使用 Markdown 格式（標題、列表、程式碼區塊、表格等）
5. 如果是教學類，要有清晰的步驟和程式碼範例
6. 如果是比較類，要有表格對比
7. 引用來源時標註出處"""

        return self._chat(prompt)

    def _get_type_description(self, content_type: str) -> str:
        """取得內容類型的描述"""
        descriptions = {
            "tutorial": "實用教學文章",
            "comparison": "深度比較分析報告",
            "report": "研究報告",
            "reference": "技術參考文件",
            "list": "精選列表",
            "overview": "概述介紹文章"
        }
        return descriptions.get(content_type, "研究報告")

    def _get_report_structure(self, content_type: str) -> str:
        """根據內容類型取得報告結構模板"""

        structures = {
            "tutorial": """請按照以下結構撰寫教學文章:

# [主題] 完整教學

## 簡介
[說明這個教學的目標和學習成果]

## 前置需求
- [需求 1]
- [需求 2]
- [需求 3]

## 步驟一：[標題]
[說明]

```[程式語言]
[程式碼範例]
```

[解釋程式碼]

## 步驟二：[標題]
[說明和程式碼]

## 步驟三：[標題]
[說明和程式碼]

## 實戰範例
[完整的實作範例]

## 常見問題與解決方案
### Q: [問題]
A: [解答]

## 進階延伸
[進階主題和資源]

## 總結
[重點回顧]

## 參考資源
[來源列表]""",

            "comparison": """請按照以下結構撰寫比較分析:

# [主題] 深度比較分析

## 概述
[比較的背景和目的]

## 比較項目一覽

| 特徵 | 選項 A | 選項 B | 選項 C |
|------|--------|--------|--------|
| [特徵 1] | [值] | [值] | [值] |
| [特徵 2] | [值] | [值] | [值] |
| [特徵 3] | [值] | [值] | [值] |
| [特徵 4] | [值] | [值] | [值] |

## 選項 A 詳細分析

### 優點
- [優點 1]
- [優點 2]

### 缺點
- [缺點 1]
- [缺點 2]

### 適用場景
[說明]

## 選項 B 詳細分析
[同上結構]

## 選項 C 詳細分析
[同上結構]

## 效能/價格/易用性對比
[深入分析]

## 使用情境建議
- **適合選擇 A 的情況:** [說明]
- **適合選擇 B 的情況:** [說明]
- **適合選擇 C 的情況:** [說明]

## 結論與建議
[總結分析和最終建議]

## 參考來源
[來源列表]""",

            "report": """請按照以下結構撰寫研究報告:

# [研究主題]

## 摘要
[150-200 字的研究摘要，包含目的、方法、主要發現和結論]

## 研究背景
[為什麼這個主題重要，研究動機]

## 核心概念解析

### [概念 1]
[深入解釋]

### [概念 2]
[深入解釋]

### [概念 3]
[深入解釋]

## 技術架構分析
[系統架構、運作原理]

```
[架構圖或流程圖（用 ASCII 或描述）]
```

## 實際應用案例
[案例分析]

## 優勢與挑戰

### 優勢
- [優勢 1]
- [優勢 2]
- [優勢 3]

### 挑戰與限制
- [挑戰 1]
- [挑戰 2]

## 未來發展趨勢
[趨勢預測]

## 結論
[總結研究發現]

## 參考文獻
[來源列表]""",

            "reference": """請按照以下結構撰寫技術參考文件:

# [技術/API] 參考手冊

## 概述
[簡介功能和用途]

## 安裝與設置

```bash
[安裝指令]
```

## 快速開始

```[語言]
[最簡單的使用範例]
```

## 核心 API

### `function_name(param1, param2)`

**功能描述:** [說明]

**參數:**

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| param1 | string | 是 | - | [說明] |
| param2 | number | 否 | 0 | [說明] |

**回傳值:** [說明]

**範例:**

```[語言]
[使用範例]
```

### `another_function()`
[同上結構]

## 進階用法

### [進階主題 1]
[說明和範例]

### [進階主題 2]
[說明和範例]

## 錯誤處理
[常見錯誤和解決方案]

## 最佳實踐
[建議的使用方式]

## 版本歷史
[版本更新記錄]

## 參考連結
[相關資源]""",

            "list": """請按照以下結構撰寫推薦列表:

# [主題] 精選推薦

## 簡介
[說明選擇標準和評估方式]

## 總覽比較

| 排名 | 名稱 | 評分 | 價格 | 最適合 |
|------|------|------|------|--------|
| 1 | [名稱] | ⭐⭐⭐⭐⭐ | [價格] | [適用] |
| 2 | [名稱] | ⭐⭐⭐⭐ | [價格] | [適用] |
| 3 | [名稱] | ⭐⭐⭐⭐ | [價格] | [適用] |

## 1. [第一名名稱]

**評分:** ⭐⭐⭐⭐⭐ (5/5)

[詳細介紹]

**優點:**
- [優點 1]
- [優點 2]

**缺點:**
- [缺點 1]

**最適合:** [說明]

## 2. [第二名名稱]

**評分:** ⭐⭐⭐⭐ (4/5)

[同上結構]

## 3. [第三名名稱]
[同上結構]

## 選擇指南
- **預算有限:** 推薦 [名稱]
- **追求效能:** 推薦 [名稱]
- **初學者:** 推薦 [名稱]

## 常見問題

### Q: [問題]
A: [答案]

## 結論
[總結建議]

## 參考資料
[來源]""",

            "overview": """請按照以下結構撰寫概述介紹:

# [主題] 完整指南

## 什麼是 [主題]？
[清晰簡潔的定義]

## 為什麼 [主題] 重要？
[說明重要性和應用價值]

## 核心特點

### 🔹 [特點 1]
[說明]

### 🔹 [特點 2]
[說明]

### 🔹 [特點 3]
[說明]

## 運作原理
[簡單解釋原理]

## 主要應用場景
1. **[場景 1]:** [說明]
2. **[場景 2]:** [說明]
3. **[場景 3]:** [說明]

## 優缺點分析

| 優點 | 缺點 |
|------|------|
| [優點 1] | [缺點 1] |
| [優點 2] | [缺點 2] |
| [優點 3] | [缺點 3] |

## 入門指南

### 第一步：[動作]
[說明]

### 第二步：[動作]
[說明]

## 相關技術/概念
- [相關 1]
- [相關 2]
- [相關 3]

## 常見誤解
[澄清常見的錯誤認知]

## 結論
[總結]

## 延伸學習資源
[推薦資源]

## 參考來源
[來源列表]"""
        }

        return structures.get(content_type, structures["report"])
