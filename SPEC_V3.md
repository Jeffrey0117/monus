# Monus v3 執行力強化規格書

## 核心理念

> **HTML/CSS 打天下** - 一套渲染引擎，多種輸出格式
>
> Agent 的價值在「執行」，不在「思考」

---

## 架構概覽

### 5 Agent 系統

| Agent | 職責 | 何時介入 |
|-------|------|----------|
| **Planner** | 任務分解、流程規劃、任務分類 | 開始時 |
| **Researcher** | 資料搜尋與提取（可選） | 需要外部資料時 |
| **Writer** | 內容生成（Markdown） | 核心產出 |
| **Renderer** | HTML/CSS 渲染輸出 | 最終輸出 |
| **Verifier** | 品質驗證 | 結束前 |

### 輸出格式矩陣

```
                    ┌─────────────┐
                    │   Writer    │
                    │ (Markdown)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Renderer   │
                    │ (HTML/CSS)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼─────┐      ┌─────▼─────┐
   │   PDF   │       │   Slides  │      │    Web    │
   │ (A4頁面) │       │ (Slidev)  │      │ (單頁HTML) │
   └─────────┘       └───────────┘      └───────────┘
```

---

## 工具清單

### 核心輸出工具

| 工具 | 功能 | 技術實作 | 優先級 |
|------|------|----------|--------|
| `render.pdf` | Markdown → PDF | Playwright + HTML | ✅ 已完成 |
| `render.slides` | Markdown → 簡報 | Slidev 風格 HTML | P0 |
| `render.web` | Markdown → 網頁 | 單檔 HTML + CSS | P0 |
| `render.preview` | 即時預覽 | 本地 HTTP Server | P1 |

### 資料工具（可選）

| 工具 | 功能 | 何時使用 |
|------|------|----------|
| `browser.search` | 網路搜尋 | 需要最新/真實資料 |
| `browser.open` | 開啟網頁 | 深入閱讀來源 |
| `browser.extract` | 提取內容 | 結構化資料擷取 |
| `browser.screenshot` | 網頁截圖 | 視覺證據 |

---

## P0: Slides 輸出 (Slidev 風格)

### 設計原則

1. **Markdown 語法** - 用 `---` 分隔投影片
2. **純 HTML/CSS** - 不依賴 Node.js
3. **響應式設計** - 支援全螢幕、鍵盤控制
4. **程式碼高亮** - 內建 highlight.js

### tools/slides.py 規格

```python
"""
Slides Tool - Markdown 轉 Slidev 風格簡報
純 HTML/CSS，無需 Node.js
"""
import markdown
from pathlib import Path


class SlidesTool:
    def __init__(self):
        self.themes = ["default", "dark", "minimal"]

    async def generate(self, markdown_content: str, output_path: str,
                       title: str = "Presentation", theme: str = "default") -> dict:
        """
        將 Markdown 轉換為 HTML 簡報

        Markdown 格式：
        ---
        # 標題頁
        副標題
        ---
        # 第一張
        - 重點一
        - 重點二
        ---

        Args:
            markdown_content: Markdown 內容（用 --- 分隔投影片）
            output_path: 輸出路徑 (.html)
            title: 簡報標題
            theme: 主題 (default/dark/minimal)

        Returns:
            {success: bool, path: str, slides_count: int, error?: str}
        """
        # 分割投影片
        slides = markdown_content.split('\n---\n')
        slides = [s.strip() for s in slides if s.strip()]

        # 轉換每張投影片為 HTML
        slides_html = []
        for i, slide_md in enumerate(slides):
            slide_html = markdown.markdown(
                slide_md,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
            slides_html.append(f'''
            <section class="slide" id="slide-{i}">
                <div class="content">{slide_html}</div>
            </section>
            ''')

        # 組合完整 HTML（含 CSS 和 JS）
        full_html = self._build_html(slides_html, title, theme)
        Path(output_path).write_text(full_html, encoding='utf-8')

        return {
            "success": True,
            "path": output_path,
            "slides_count": len(slides)
        }
```

### 簡報功能
- ⬅️ ➡️ 鍵盤切換
- `F` 全螢幕
- 進度條顯示
- 程式碼高亮
- 三種主題可選

---

## P0: Web 單頁輸出

### tools/web.py 規格

```python
"""
Web Tool - Markdown 轉單頁網站
自包含 HTML + CSS，可直接分享
"""
import markdown
from pathlib import Path


class WebTool:
    async def generate(self, markdown_content: str, output_path: str,
                       title: str = "Document", style: str = "article") -> dict:
        """
        將 Markdown 轉換為精美的單頁網站

        Args:
            markdown_content: Markdown 內容
            output_path: 輸出路徑 (.html)
            title: 頁面標題
            style: 樣式 (article/landing/docs)

        Returns:
            {success: bool, path: str, error?: str}
        """
```

### 網頁樣式
- **article** - 文章閱讀風格
- **landing** - 產品頁面風格
- **docs** - 技術文件風格

---

## 新 Agent Loop 流程

### 快速模式（預設）

```
User Goal
    │
    ▼
┌─────────┐     分析任務類型
│ Planner │─────────────────────────┐
└─────────┘                         │
    │                               │
    │ 任務類型？                     │
    │                               ▼
    ├── knowledge ──────────────► 直接寫
    │   (純知識)                     │
    │                               │
    ├── research ───────────────► 搜尋後寫
    │   (需查資料)                   │
    │                               ▼
    │                          ┌─────────┐
    │                          │ Writer  │
    │                          └────┬────┘
    │                               │
    │                               ▼
    │                          ┌──────────┐
    │                          │ Renderer │
    │                          └────┬─────┘
    │                               │
    │                     ┌────────┼────────┐
    │                     ▼        ▼        ▼
    │                    PDF    Slides     Web
    │                     │        │        │
    └────────────────────►└────────┴────────┘
                                   │
                                   ▼
                            ┌──────────┐
                            │ Verifier │
                            └──────────┘
```

### 任務分類邏輯

```python
def classify_task(goal: str) -> str:
    """
    分類任務類型，決定是否需要搜尋

    Returns:
        "knowledge" - 純知識型，LLM 直接寫
        "research"  - 需要搜尋最新/真實資料
        "comparison" - 比較型，需要多來源
        "tutorial"  - 教學型，可直接寫
    """
    # 需要搜尋的關鍵詞
    research_keywords = [
        "最新", "今天", "現在", "價格", "股價",
        "新聞", "即時", "真實", "數據", "統計"
    ]

    # 可直接寫的類型
    knowledge_keywords = [
        "教學", "原理", "概念", "是什麼", "如何",
        "基礎", "入門", "解釋", "說明"
    ]

    goal_lower = goal.lower()

    for kw in research_keywords:
        if kw in goal_lower:
            return "research"

    for kw in knowledge_keywords:
        if kw in goal_lower:
            return "knowledge"

    # 預設為 knowledge（加速執行）
    return "knowledge"
```

---

## 檔案結構

```
monus/
├── agent/
│   ├── loop.py          # 主循環 (修改)
│   ├── planner.py       # 規劃 + 任務分類 (修改)
│   ├── writer.py        # 新增: 內容生成
│   ├── researcher.py    # 新增: 資料搜尋 (簡化版)
│   ├── evaluator.py     # 保留 (簡化)
│   └── verifier.py      # 保留
├── tools/
│   ├── browser.py       # 瀏覽器 (已有)
│   ├── pdf.py           # PDF 輸出 (已完成 ✅)
│   ├── slides.py        # 新增: 簡報輸出
│   ├── web.py           # 新增: 網頁輸出
│   └── fs.py            # 檔案系統 (已有)
├── main.py              # 修改: 加入 --format 參數
└── runs/
```

---

## CLI 使用方式

```bash
# 生成 PDF（預設）
python main.py run "Python asyncio 教學"

# 生成簡報
python main.py run "Python asyncio 教學" --format slides

# 生成網頁
python main.py run "Python asyncio 教學" --format web

# 全部格式
python main.py run "Python asyncio 教學" --format all

# 指定主題
python main.py run "Python asyncio 教學" --format slides --theme dark
```

---

## 實作優先順序

### Phase 1 (立即執行)
- [x] PDF 輸出 ✅ 已完成
- [ ] 實作 `tools/slides.py`
- [ ] 實作 `tools/web.py`
- [ ] 修改 `main.py` 支援 `--format` 參數
- [ ] 修改 `loop.py` 整合新輸出工具

### Phase 2 (接下來)
- [ ] 新增 `agent/writer.py` (專門寫內容)
- [ ] 簡化 Reasoner → Researcher
- [ ] 加入任務分類邏輯到 Planner

### Phase 3 (優化)
- [ ] 更多主題樣式
- [ ] 即時預覽功能
- [ ] 模板客製化

---

## 成功標準

執行 `python main.py run "XXX主題" --format all` 後：

```
runs/2026-01-02_xxxxx/
├── task.json
├── report.md          # Markdown 原稿
├── report.pdf         # PDF 文件 ✅
├── slides.html        # HTML 簡報（可全螢幕）
├── index.html         # 單頁網站（可分享）
└── sources.json       # 來源記錄
```

所有輸出：
- ✅ 中文編碼正確
- ✅ 排版美觀
- ✅ 可直接開啟使用
- ✅ 不需要額外安裝

---

## 開始執行？

確認後開始實作 Phase 1：Slides 和 Web 輸出工具。
