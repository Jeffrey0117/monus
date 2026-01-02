# Monus v2 改善規格書

## 問題診斷

### 現狀問題
1. **無實際產出** - 只有 Markdown 報告，沒有 PDF、Excel 等實用檔案
2. **搜尋無價值** - LLM 本身就知道的東西，何必再搜尋？
3. **速度慢** - 多個 Agent 互相呼叫 LLM，浪費時間
4. **離題嚴重** - 搜尋結果混雜，報告內容偏離主題

### 核心洞察
> **Agent 的價值 = 執行能力，不是思考能力**
>
> 思考讓 LLM 做就好，Agent 要做的是「動手」

---

## 改善架構

### 新工具清單

| 工具 | 功能 | 實作方式 | 優先級 |
|------|------|----------|--------|
| `pdf.generate` | Markdown → PDF | WeasyPrint / pdfkit | P0 |
| `excel.create` | 資料 → Excel + 圖表 | openpyxl + matplotlib | P1 |
| `image.screenshot` | 網頁截圖 | Playwright | P1 |
| `chart.create` | 資料 → 圖表圖片 | matplotlib | P2 |
| `ppt.create` | 大綱 → PPT | python-pptx | P2 |

### 新流程設計

```
舊流程（沒價值）:
User Goal → Planner 規劃 → 搜尋 → 搜尋 → 搜尋 → LLM 寫報告 → Markdown

新流程（有價值）:
User Goal → LLM 直接寫內容 → 產出 PDF/Excel/PPT
                ↓
           需要真實數據時才搜尋
                ↓
           爬取結構化數據（價格、規格）
                ↓
           整合到報告中
```

---

## P0: PDF 輸出功能

### 檔案結構
```
tools/
├── pdf.py          # PDF 生成工具
├── browser.py      # 現有
├── fs.py           # 現有
└── code.py         # 現有
```

### pdf.py 規格

```python
"""
PDF Tool - Markdown 轉 PDF
"""
from weasyprint import HTML, CSS
import markdown
from pathlib import Path


class PDFTool:
    def __init__(self):
        self.default_css = """
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Noto Sans TC', sans-serif; line-height: 1.6; }
        h1 { color: #333; border-bottom: 2px solid #333; }
        h2 { color: #555; }
        code { background: #f4f4f4; padding: 2px 6px; }
        pre { background: #f4f4f4; padding: 1em; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f4f4f4; }
        """

    def generate(self, markdown_content: str, output_path: str,
                 title: str = "Report", custom_css: str = None) -> dict:
        """
        將 Markdown 轉換為 PDF

        Args:
            markdown_content: Markdown 文字內容
            output_path: PDF 輸出路徑
            title: 文件標題
            custom_css: 自訂 CSS（可選）

        Returns:
            {success: bool, path: str, pages: int, error?: str}
        """
        try:
            # Markdown → HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code', 'toc']
            )

            # 包裝成完整 HTML
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{title}</title>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # 準備 CSS
            css = CSS(string=custom_css or self.default_css)

            # 生成 PDF
            html = HTML(string=full_html)
            pdf_doc = html.render(stylesheets=[css])
            pdf_doc.write_pdf(output_path)

            return {
                "success": True,
                "path": output_path,
                "pages": len(pdf_doc.pages)
            }

        except Exception as e:
            return {
                "success": False,
                "path": output_path,
                "error": str(e)
            }

    def from_file(self, markdown_path: str, output_path: str = None) -> dict:
        """從 Markdown 檔案生成 PDF"""
        md_path = Path(markdown_path)
        if not md_path.exists():
            return {"success": False, "error": f"File not found: {markdown_path}"}

        content = md_path.read_text(encoding="utf-8")
        output = output_path or str(md_path.with_suffix(".pdf"))

        return self.generate(content, output, title=md_path.stem)
```

### 依賴安裝
```bash
pip install weasyprint markdown
# Windows 需要額外安裝 GTK3: https://github.com/niceno/Windows-Python-WeasyPrint
```

### 備用方案（如果 WeasyPrint 太難裝）
```python
# 使用 pdfkit + wkhtmltopdf
pip install pdfkit
# 需要安裝 wkhtmltopdf: https://wkhtmltopdf.org/downloads.html
```

---

## P1: Excel 輸出功能

### excel.py 規格

```python
"""
Excel Tool - 資料轉 Excel + 圖表
"""
import openpyxl
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import json


class ExcelTool:
    def create(self, data: list[dict], output_path: str,
               sheet_name: str = "Data", chart_type: str = None) -> dict:
        """
        建立 Excel 檔案

        Args:
            data: 資料列表 [{col1: val1, col2: val2}, ...]
            output_path: 輸出路徑
            sheet_name: 工作表名稱
            chart_type: 圖表類型 (bar/line/pie/None)

        Returns:
            {success: bool, path: str, rows: int, error?: str}
        """
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name

            if not data:
                return {"success": False, "error": "No data provided"}

            # 寫入標題
            headers = list(data[0].keys())
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')

            # 寫入資料
            for row_idx, row_data in enumerate(data, 2):
                for col_idx, header in enumerate(headers, 1):
                    ws.cell(row=row_idx, column=col_idx, value=row_data.get(header))

            # 加入圖表
            if chart_type and len(data) > 0:
                self._add_chart(ws, chart_type, len(data), len(headers))

            # 自動調整欄寬
            for col in ws.columns:
                max_length = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

            wb.save(output_path)

            return {
                "success": True,
                "path": output_path,
                "rows": len(data)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _add_chart(self, ws, chart_type: str, data_rows: int, data_cols: int):
        """加入圖表"""
        if chart_type == "bar":
            chart = BarChart()
        elif chart_type == "line":
            chart = LineChart()
        elif chart_type == "pie":
            chart = PieChart()
        else:
            return

        # 設定資料範圍
        data_ref = Reference(ws, min_col=2, min_row=1, max_col=data_cols, max_row=data_rows + 1)
        cats_ref = Reference(ws, min_col=1, min_row=2, max_row=data_rows + 1)

        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.title = "Chart"

        ws.add_chart(chart, f"{chr(65 + data_cols + 1)}2")
```

---

## P1: 網頁截圖功能

### 在 browser.py 加強

```python
async def screenshot(self, url: str = None, output_path: str = "screenshot.png",
                     full_page: bool = True, selector: str = None) -> dict:
    """
    網頁截圖

    Args:
        url: 要截圖的網址（如果為 None，使用當前頁面）
        output_path: 輸出路徑
        full_page: 是否截取整頁
        selector: CSS 選擇器（只截取特定元素）

    Returns:
        {success: bool, path: str, error?: str}
    """
    await self._ensure_browser()

    try:
        if url:
            await self._page.goto(url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(1)

        if selector:
            element = await self._page.query_selector(selector)
            if element:
                await element.screenshot(path=output_path)
            else:
                return {"success": False, "error": f"Selector not found: {selector}"}
        else:
            await self._page.screenshot(path=output_path, full_page=full_page)

        return {"success": True, "path": output_path}

    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 新 Agent Loop 流程

### loop.py 修改重點

```python
async def run(self, goal: str) -> dict:
    """
    新流程：
    1. 分析任務類型
    2. 如果是純寫作任務 → 直接 LLM 生成 → 轉 PDF
    3. 如果需要真實數據 → 爬取 → 整合 → 生成 → 轉 PDF
    """

    # 1. 任務分類
    task_type = self._classify_task(goal)
    # "research" | "data_collection" | "comparison" | "report"

    # 2. 根據任務類型執行
    if task_type == "research":
        # 研究類：LLM 直接寫 + 可選搜尋補充
        report = self.planner.generate_report_direct(goal)

    elif task_type == "data_collection":
        # 數據收集：爬取真實數據
        data = await self._collect_real_data(goal)
        report = self.planner.generate_report_with_data(goal, data)

    elif task_type == "comparison":
        # 比較類：爬取多個來源 + 結構化比較
        items = await self._collect_comparison_data(goal)
        report = self.planner.generate_comparison_report(goal, items)

    # 3. 產出 PDF
    pdf_result = self.pdf.generate(report, f"{self.run_dir}/report.pdf")

    # 4. 如果有數據，也產出 Excel
    if data:
        excel_result = self.excel.create(data, f"{self.run_dir}/data.xlsx")

    return {
        "success": True,
        "pdf": pdf_result["path"],
        "excel": excel_result["path"] if data else None
    }
```

---

## 實作優先順序

### Phase 1（立即執行）
- [ ] 安裝 PDF 依賴
- [ ] 實作 `tools/pdf.py`
- [ ] 修改 `loop.py` 在報告生成後自動轉 PDF
- [ ] 測試：跑一次任務，確認產出 PDF

### Phase 2（接下來）
- [ ] 實作 `tools/excel.py`
- [ ] 強化 `browser.screenshot()`
- [ ] 加入任務分類邏輯

### Phase 3（優化）
- [ ] 簡化 Agent 架構（砍掉沒用的）
- [ ] 加入任務模板
- [ ] 支援 PPT 輸出

---

## 成功標準

跑完任務後，`runs/` 目錄應該包含：

```
runs/2026-01-02_xxxxx/
├── task.json           # 任務記錄
├── report.md           # Markdown 報告
├── report.pdf          # PDF 報告 ← 新增
├── data.xlsx           # Excel 數據（如有）← 新增
├── screenshots/        # 截圖（如有）← 新增
│   ├── source1.png
│   └── source2.png
└── sources.json        # 來源記錄
```

---

## 開始執行？

確認後我就開始實作 Phase 1：PDF 輸出功能。
