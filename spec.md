好，**Python + Playwright** 是對的，而且非常適合你現在要做的「工具型 Manus」。

下面我直接給你一份**可以開工的 Manus-mini（Python 版）完整藍圖**：
不是概念，是「你照這個結構寫，真的會跑」。

---

# Manus-mini（Python + Playwright）MVP 規格

## 🎯 目標（第一版只做一件事）

> **輸入一個任務目標 → 自動研究 → 自動抓資料 → 驗證 → 產出報告**

鎖死範圍＝成功。

---

## 一、專案結構（照這個建）

```txt
manus-mini/
├─ agent/
│  ├─ planner.py        # 任務拆解
│  ├─ loop.py           # Decide / Act / Observe / Verify / Recover
│  ├─ verifier.py       # 驗證規則
│  └─ memory.py         # state 存取
│
├─ tools/
│  ├─ browser.py        # Playwright 封裝
│  ├─ fs.py             # 檔案工具
│  ├─ code.py           # shell / python / git
│
├─ schemas/
│  └─ task.schema.json
│
├─ templates/
│  └─ report.md.jinja
│
├─ runs/
│  └─ 2026-01-02_xxx/
│     ├─ task.json
│     ├─ sources.json
│     ├─ report.md
│     └─ logs.txt
│
├─ main.py              # CLI 入口
└─ requirements.txt
```

---

## 二、核心：`task.json`（Manus 的外接大腦）

**這個檔案是關鍵，不要靠 prompt 記憶**

```json
{
  "goal": "研究 Manus AI 的技術原理並整理成報告",
  "status": "running",

  "steps": [
    {
      "id": 1,
      "title": "搜尋官方與分析文章",
      "tool": "browser.search",
      "input": "Manus AI technical architecture",
      "status": "pending",
      "output": null,
      "evidence": []
    }
  ],

  "artifacts": {
    "sources": "sources.json",
    "report": "report.md"
  },

  "memory": {
    "keywords_tried": [],
    "failed_attempts": []
  }
}
```

你之後所有 agent 決策，**都基於這個 JSON**。

---

## 三、工具層（最重要的封裝觀念）

### 1️⃣ browser.py（Playwright 不要外洩給 LLM）

```python
class BrowserTool:
    async def search(self, query: str) -> list:
        ...
    async def open(self, url: str):
        ...
    async def extract(self, mode="readability") -> str:
        ...
    async def screenshot(self, path: str):
        ...
```

LLM **只能說要用哪個工具＋參數**，
你負責處理 timeout、retry、反爬、DOM 爛掉。

---

### 2️⃣ fs.py（產物落地）

```python
class FileTool:
    def write(self, path: str, content: str):
        ...
    def read(self, path: str) -> str:
        ...
    def exists(self, path: str) -> bool:
        ...
```

---

### 3️⃣ code.py（整理、轉換、後處理）

```python
class CodeTool:
    def run(self, cmd: str, cwd: str = ".") -> str:
        ...
```

---

## 四、Agent Loop（Manus 的心臟）

### loop.py（骨架）

```python
while not task_completed:
    action = planner.decide(task_state)

    result = tools.run(action)

    observer.update(task_state, result)

    if verifier.pass(task_state):
        mark_step_done()
    else:
        recover_strategy()
```

這個 loop **永遠不變**，你未來加任務只換規則。

---

## 五、Planner（不是亂問 LLM）

### planner.py 的角色很清楚

* 根據 `task.json`
* 判斷「下一步要不要 browser / code / fs」
* 不負責做事，只負責決策

```python
def decide(task_state):
    """
    return {
      "tool": "browser.search",
      "input": "Manus AI agent architecture"
    }
    """
```

---

## 六、Verifier（讓它真的像 Manus）

### verifier.py（第一版就夠用的 6 條）

```python
def verify(task):
    rules = [
        has_min_sources(task, n=5),
        sources_have_url_and_title(task),
        report_exists(task),
        report_has_sections(task),
        not_all_from_same_domain(task),
        total_word_count(task) > 800
    ]
    return all(rules)
```

👉 **沒有 verifier = 玩具 agent**
👉 **有 verifier = 可用系統**

---

## 七、Report 模板（避免亂寫）

`templates/report.md.jinja`

```md
# {{ title }}

## 摘要
{{ summary }}

## 核心技術拆解
{% for item in core_points %}
- {{ item }}
{% endfor %}

## 系統架構
{{ architecture }}

## 優點與限制
{{ pros_cons }}

## 參考來源
{% for src in sources %}
- {{ src.title }} — {{ src.url }}
{% endfor %}
```

---

## 八、CLI（你第一版的產品）

```bash
python main.py run "研究 Manus AI 的技術原理"
```

執行後：

```txt
runs/
└─ 2026-01-02_manus_ai/
   ├─ task.json
   ├─ sources.json
   ├─ report.md
   └─ logs.txt
```

---

## 九、這東西為什麼「已經是 Manus 類系統」

因為你已經有：

* ✔ 外部狀態（state）
* ✔ 多工具協作
* ✔ 可失敗、可修正
* ✔ 有完成判準
* ✔ 非 token 記憶

模型換掉都沒差，這是**工程資產**。

