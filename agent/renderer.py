"""
Renderer Agent - 智能內容渲染與版面選擇
負責分析內容類型並選擇最適合的版面樣式

功能:
1. 內容分析 - 判斷內容類型（教學、報告、比較、列表等）
2. 版面推薦 - 根據內容特徵選擇最佳版面
3. 樣式生成 - 動態生成適合的 CSS 樣式
4. 多格式輸出 - PDF / Slides / Web
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Renderer:
    """智能渲染 Agent"""

    # 內容類型定義
    CONTENT_TYPES = {
        "tutorial": {
            "name": "教學文章",
            "features": ["步驟", "程式碼", "示例", "說明"],
            "best_layouts": ["step-by-step", "sidebar-nav", "code-heavy"]
        },
        "comparison": {
            "name": "比較分析",
            "features": ["表格", "對比", "優缺點", "vs"],
            "best_layouts": ["table-centric", "split-view", "cards"]
        },
        "report": {
            "name": "研究報告",
            "features": ["摘要", "結論", "數據", "分析"],
            "best_layouts": ["academic", "executive", "data-viz"]
        },
        "overview": {
            "name": "概述介紹",
            "features": ["什麼是", "介紹", "概念", "基礎"],
            "best_layouts": ["landing", "hero-sections", "visual"]
        },
        "reference": {
            "name": "參考文件",
            "features": ["API", "參數", "函數", "方法"],
            "best_layouts": ["docs", "sidebar-toc", "searchable"]
        },
        "list": {
            "name": "列表彙整",
            "features": ["清單", "列表", "排名", "推薦"],
            "best_layouts": ["card-grid", "numbered-list", "timeline"]
        }
    }

    # 版面樣式庫
    LAYOUTS = {
        # 教學類版面
        "step-by-step": {
            "name": "步驟教學",
            "description": "清晰的編號步驟，適合教程",
            "css_class": "layout-steps",
            "features": ["numbered-sections", "progress-indicator", "code-blocks"]
        },
        "sidebar-nav": {
            "name": "側邊導航",
            "description": "帶有目錄側邊欄的文章",
            "css_class": "layout-sidebar",
            "features": ["sticky-toc", "section-links", "scroll-spy"]
        },
        "code-heavy": {
            "name": "程式碼主導",
            "description": "大量程式碼的技術文章",
            "css_class": "layout-code",
            "features": ["syntax-highlight", "copy-button", "line-numbers"]
        },

        # 比較類版面
        "table-centric": {
            "name": "表格中心",
            "description": "以表格為主的比較分析",
            "css_class": "layout-table",
            "features": ["responsive-table", "zebra-stripes", "sticky-header"]
        },
        "split-view": {
            "name": "分欄對比",
            "description": "左右對比的版面",
            "css_class": "layout-split",
            "features": ["two-column", "sync-scroll", "highlight-diff"]
        },
        "cards": {
            "name": "卡片式",
            "description": "卡片網格展示",
            "css_class": "layout-cards",
            "features": ["grid-layout", "hover-effects", "icons"]
        },

        # 報告類版面
        "academic": {
            "name": "學術報告",
            "description": "正式的學術風格",
            "css_class": "layout-academic",
            "features": ["serif-font", "footnotes", "citations"]
        },
        "executive": {
            "name": "商業摘要",
            "description": "精簡的執行摘要風格",
            "css_class": "layout-executive",
            "features": ["key-points", "callouts", "summary-boxes"]
        },
        "data-viz": {
            "name": "數據視覺化",
            "description": "強調數據圖表",
            "css_class": "layout-dataviz",
            "features": ["chart-ready", "stat-cards", "infographic"]
        },

        # 概述類版面
        "landing": {
            "name": "登陸頁",
            "description": "吸引眼球的介紹頁",
            "css_class": "layout-landing",
            "features": ["hero-section", "feature-grid", "cta-buttons"]
        },
        "hero-sections": {
            "name": "區塊式",
            "description": "大區塊分隔的視覺風格",
            "css_class": "layout-hero",
            "features": ["full-width-sections", "alternating-bg", "images"]
        },
        "visual": {
            "name": "視覺豐富",
            "description": "圖片和視覺元素為主",
            "css_class": "layout-visual",
            "features": ["image-gallery", "icons", "gradients"]
        },

        # 參考類版面
        "docs": {
            "name": "技術文件",
            "description": "標準技術文件風格",
            "css_class": "layout-docs",
            "features": ["api-blocks", "parameters", "examples"]
        },
        "sidebar-toc": {
            "name": "目錄導航",
            "description": "帶有詳細目錄的文件",
            "css_class": "layout-toc",
            "features": ["nested-toc", "breadcrumbs", "search"]
        },

        # 列表類版面
        "card-grid": {
            "name": "卡片網格",
            "description": "網格排列的卡片",
            "css_class": "layout-grid",
            "features": ["masonry", "filters", "tags"]
        },
        "numbered-list": {
            "name": "編號列表",
            "description": "清晰的編號列表",
            "css_class": "layout-list",
            "features": ["large-numbers", "descriptions", "links"]
        },
        "timeline": {
            "name": "時間線",
            "description": "時間軸展示",
            "css_class": "layout-timeline",
            "features": ["vertical-line", "dates", "events"]
        }
    }

    # 色彩主題
    COLOR_THEMES = {
        "default": {
            "primary": "#00d4aa",
            "secondary": "#7c3aed",
            "bg": "#ffffff",
            "text": "#1e293b",
            "accent": "#f59e0b"
        },
        "dark": {
            "primary": "#00d4aa",
            "secondary": "#a78bfa",
            "bg": "#0f172a",
            "text": "#f8fafc",
            "accent": "#fbbf24"
        },
        "ocean": {
            "primary": "#0ea5e9",
            "secondary": "#06b6d4",
            "bg": "#f0f9ff",
            "text": "#0c4a6e",
            "accent": "#f97316"
        },
        "forest": {
            "primary": "#22c55e",
            "secondary": "#14b8a6",
            "bg": "#f0fdf4",
            "text": "#14532d",
            "accent": "#eab308"
        },
        "sunset": {
            "primary": "#f97316",
            "secondary": "#ef4444",
            "bg": "#fff7ed",
            "text": "#7c2d12",
            "accent": "#a855f7"
        },
        "minimal": {
            "primary": "#525252",
            "secondary": "#737373",
            "bg": "#fafafa",
            "text": "#171717",
            "accent": "#2563eb"
        },
        "pro": {
            "primary": "#3b82f6",
            "secondary": "#6366f1",
            "bg": "#ffffff",
            "text": "#1e293b",
            "accent": "#10b981"
        }
    }

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )

    def analyze_content(self, content: str, goal: str = "") -> dict:
        """
        分析內容並推薦最佳版面配置

        Args:
            content: Markdown 內容
            goal: 原始任務目標

        Returns:
            {
                "content_type": "tutorial",
                "recommended_layout": "step-by-step",
                "color_theme": "default",
                "features": [...],
                "reasoning": "..."
            }
        """
        # 快速特徵分析
        features = self._extract_features(content)

        # 使用 LLM 進行深度分析
        prompt = f"""分析以下內容，判斷最適合的版面配置。

任務目標: {goal}

內容預覽 (前 1500 字):
{content[:1500]}

已檢測到的特徵:
- 程式碼區塊數量: {features['code_blocks']}
- 表格數量: {features['tables']}
- 圖片數量: {features['images']}
- 標題層級: {features['heading_levels']}
- 列表項目數: {features['list_items']}
- 總字數: {features['word_count']}

可用的內容類型:
{self._format_content_types()}

可用的版面樣式:
{self._format_layouts()}

可用的色彩主題:
{', '.join(self.COLOR_THEMES.keys())}

請回覆 JSON 格式:
{{
    "content_type": "類型ID",
    "recommended_layout": "版面ID",
    "color_theme": "主題ID",
    "reasoning": "選擇原因（30字內）"
}}

只回覆 JSON，不要其他文字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            # 清理可能的 markdown 標記
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            import json
            result = json.loads(result_text)

            # 驗證並填充預設值
            result["content_type"] = result.get("content_type", "report")
            result["recommended_layout"] = result.get("recommended_layout", "sidebar-nav")
            result["color_theme"] = result.get("color_theme", "default")
            result["features"] = features

            return result

        except Exception as e:
            # 使用規則分析作為備選
            return self._rule_based_analysis(features, content)

    def _extract_features(self, content: str) -> dict:
        """快速提取內容特徵"""
        import re

        # 計算程式碼區塊
        code_blocks = len(re.findall(r'```[\s\S]*?```', content))

        # 計算表格
        tables = len(re.findall(r'\|.*\|.*\|', content))

        # 計算圖片
        images = len(re.findall(r'!\[.*?\]\(.*?\)', content))

        # 計算標題層級
        h1 = len(re.findall(r'^# ', content, re.MULTILINE))
        h2 = len(re.findall(r'^## ', content, re.MULTILINE))
        h3 = len(re.findall(r'^### ', content, re.MULTILINE))

        # 計算列表項目
        list_items = len(re.findall(r'^[\*\-\+] |^\d+\. ', content, re.MULTILINE))

        # 計算字數
        word_count = len(content)

        # 檢測關鍵字
        keywords = {
            "tutorial": ["步驟", "教學", "如何", "step", "tutorial", "guide"],
            "comparison": ["比較", "對比", "vs", "優缺點", "差異"],
            "report": ["報告", "分析", "結論", "摘要", "研究"],
            "reference": ["API", "參數", "函數", "方法", "參考"],
            "list": ["清單", "列表", "排名", "推薦", "top"]
        }

        detected_types = []
        content_lower = content.lower()
        for type_name, words in keywords.items():
            if any(word.lower() in content_lower for word in words):
                detected_types.append(type_name)

        return {
            "code_blocks": code_blocks,
            "tables": tables,
            "images": images,
            "heading_levels": {"h1": h1, "h2": h2, "h3": h3},
            "list_items": list_items,
            "word_count": word_count,
            "detected_types": detected_types
        }

    def _rule_based_analysis(self, features: dict, content: str) -> dict:
        """基於規則的內容分析（LLM 失敗時的備選）"""

        # 判斷內容類型
        content_type = "report"  # 預設

        if features["code_blocks"] >= 3:
            content_type = "tutorial"
        elif features["tables"] >= 2:
            content_type = "comparison"
        elif "tutorial" in features.get("detected_types", []):
            content_type = "tutorial"
        elif "comparison" in features.get("detected_types", []):
            content_type = "comparison"
        elif "reference" in features.get("detected_types", []):
            content_type = "reference"
        elif "list" in features.get("detected_types", []):
            content_type = "list"

        # 根據類型選擇版面
        layout_map = {
            "tutorial": "step-by-step" if features["code_blocks"] > 5 else "sidebar-nav",
            "comparison": "table-centric" if features["tables"] >= 2 else "cards",
            "report": "executive" if features["word_count"] < 3000 else "academic",
            "reference": "docs",
            "list": "card-grid" if features["list_items"] > 10 else "numbered-list",
            "overview": "landing"
        }

        # 根據特徵選擇色彩主題
        theme = "default"
        if features["code_blocks"] >= 3:
            theme = "dark"  # 程式碼多用暗色主題
        elif features["tables"] >= 2:
            theme = "pro"  # 表格多用專業主題

        return {
            "content_type": content_type,
            "recommended_layout": layout_map.get(content_type, "sidebar-nav"),
            "color_theme": theme,
            "features": features,
            "reasoning": "基於規則分析"
        }

    def _format_content_types(self) -> str:
        """格式化內容類型說明"""
        lines = []
        for type_id, info in self.CONTENT_TYPES.items():
            lines.append(f"- {type_id}: {info['name']} (特徵: {', '.join(info['features'][:3])})")
        return "\n".join(lines)

    def _format_layouts(self) -> str:
        """格式化版面說明"""
        lines = []
        for layout_id, info in self.LAYOUTS.items():
            lines.append(f"- {layout_id}: {info['name']} - {info['description']}")
        return "\n".join(lines)

    def get_layout_css(self, layout_id: str, theme_id: str = "default") -> str:
        """
        生成指定版面的 CSS 樣式

        Args:
            layout_id: 版面 ID
            theme_id: 色彩主題 ID

        Returns:
            CSS 樣式字串
        """
        layout = self.LAYOUTS.get(layout_id, self.LAYOUTS["sidebar-nav"])
        theme = self.COLOR_THEMES.get(theme_id, self.COLOR_THEMES["default"])

        # 基礎 CSS 變數
        css = f"""
:root {{
    --primary: {theme['primary']};
    --secondary: {theme['secondary']};
    --bg: {theme['bg']};
    --text: {theme['text']};
    --accent: {theme['accent']};

    --font-sans: 'Inter', 'Noto Sans TC', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-6: 1.5rem;
    --space-8: 2rem;
    --space-12: 3rem;
    --space-16: 4rem;

    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-4);
}}

h1, h2, h3, h4 {{
    color: var(--text);
    margin-bottom: var(--space-4);
    line-height: 1.3;
}}

h1 {{ font-size: 2.5rem; font-weight: 700; }}
h2 {{ font-size: 1.875rem; font-weight: 600; }}
h3 {{ font-size: 1.5rem; font-weight: 600; }}

a {{
    color: var(--primary);
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

code {{
    font-family: var(--font-mono);
    background: rgba(0,0,0,0.05);
    padding: 0.2em 0.4em;
    border-radius: var(--radius-sm);
    font-size: 0.9em;
}}

pre {{
    background: #1e293b;
    color: #e2e8f0;
    padding: var(--space-4);
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: var(--space-4) 0;
}}

pre code {{
    background: transparent;
    padding: 0;
    color: inherit;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: var(--space-4) 0;
}}

th, td {{
    padding: var(--space-3);
    border: 1px solid rgba(0,0,0,0.1);
    text-align: left;
}}

th {{
    background: rgba(0,0,0,0.05);
    font-weight: 600;
}}

blockquote {{
    border-left: 4px solid var(--primary);
    padding-left: var(--space-4);
    margin: var(--space-4) 0;
    color: var(--text);
    opacity: 0.8;
    font-style: italic;
}}

img {{
    max-width: 100%;
    height: auto;
    border-radius: var(--radius-md);
}}

ul, ol {{
    padding-left: var(--space-6);
    margin: var(--space-4) 0;
}}

li {{
    margin-bottom: var(--space-2);
}}
"""

        # 版面特定樣式
        layout_css = self._get_layout_specific_css(layout_id)

        return css + "\n" + layout_css

    def _get_layout_specific_css(self, layout_id: str) -> str:
        """取得版面特定的 CSS"""

        css_map = {
            "step-by-step": """
/* Step-by-Step Layout */
.content {
    max-width: 800px;
    margin: 0 auto;
}

.content h2 {
    counter-increment: step;
    display: flex;
    align-items: center;
    gap: var(--space-3);
}

.content h2::before {
    content: counter(step);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    background: var(--primary);
    color: white;
    border-radius: 50%;
    font-size: 1.25rem;
    font-weight: 700;
    flex-shrink: 0;
}

.content {
    counter-reset: step;
}

.progress-bar {
    position: fixed;
    top: 0;
    left: 0;
    height: 4px;
    background: var(--primary);
    transition: width 0.3s;
    z-index: 1000;
}
""",
            "sidebar-nav": """
/* Sidebar Navigation Layout */
.page-wrapper {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: var(--space-8);
    max-width: 1400px;
    margin: 0 auto;
    padding: var(--space-8);
}

.sidebar {
    position: sticky;
    top: var(--space-4);
    height: fit-content;
    max-height: calc(100vh - var(--space-8));
    overflow-y: auto;
}

.toc {
    background: rgba(0,0,0,0.02);
    padding: var(--space-4);
    border-radius: var(--radius-md);
}

.toc-title {
    font-weight: 600;
    margin-bottom: var(--space-3);
    color: var(--text);
}

.toc a {
    display: block;
    padding: var(--space-2);
    color: var(--text);
    opacity: 0.7;
    border-radius: var(--radius-sm);
    transition: all 0.2s;
}

.toc a:hover,
.toc a.active {
    opacity: 1;
    background: var(--primary);
    color: white;
    text-decoration: none;
}

.content {
    min-width: 0;
}

@media (max-width: 900px) {
    .page-wrapper {
        grid-template-columns: 1fr;
    }
    .sidebar {
        position: relative;
    }
}
""",
            "code-heavy": """
/* Code-Heavy Layout */
.content {
    max-width: 900px;
    margin: 0 auto;
}

pre {
    position: relative;
    background: #0f172a;
    border: 1px solid #334155;
}

pre::before {
    content: attr(data-lang);
    position: absolute;
    top: 0;
    right: 0;
    padding: var(--space-1) var(--space-3);
    background: var(--primary);
    color: white;
    font-size: 0.75rem;
    border-radius: 0 var(--radius-md) 0 var(--radius-sm);
}

.copy-btn {
    position: absolute;
    top: var(--space-2);
    right: var(--space-2);
    padding: var(--space-1) var(--space-2);
    background: rgba(255,255,255,0.1);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
}

pre:hover .copy-btn {
    opacity: 1;
}

.line-numbers {
    counter-reset: line;
}

.line-numbers .line::before {
    counter-increment: line;
    content: counter(line);
    display: inline-block;
    width: 2rem;
    margin-right: 1rem;
    color: #64748b;
    text-align: right;
}
""",
            "table-centric": """
/* Table-Centric Layout */
.content {
    max-width: 1000px;
    margin: 0 auto;
}

table {
    background: white;
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-md);
}

th {
    background: var(--primary);
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.875rem;
    letter-spacing: 0.05em;
}

tr:nth-child(even) {
    background: rgba(0,0,0,0.02);
}

tr:hover {
    background: rgba(0,0,0,0.05);
}

.table-wrapper {
    overflow-x: auto;
    margin: var(--space-6) 0;
}
""",
            "cards": """
/* Cards Layout */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--space-6);
    margin: var(--space-6) 0;
}

.card {
    background: white;
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    box-shadow: var(--shadow-md);
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}

.card-icon {
    width: 48px;
    height: 48px;
    background: var(--primary);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-4);
    color: white;
    font-size: 1.5rem;
}

.card h3 {
    margin-bottom: var(--space-2);
}

.card p {
    color: var(--text);
    opacity: 0.7;
}
""",
            "landing": """
/* Landing Page Layout */
.hero {
    text-align: center;
    padding: var(--space-16) var(--space-4);
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    color: white;
    margin-bottom: var(--space-12);
}

.hero h1 {
    font-size: 3.5rem;
    color: white;
    margin-bottom: var(--space-4);
}

.hero p {
    font-size: 1.25rem;
    opacity: 0.9;
    max-width: 600px;
    margin: 0 auto var(--space-8);
}

.btn {
    display: inline-block;
    padding: var(--space-3) var(--space-6);
    background: white;
    color: var(--primary);
    border-radius: var(--radius-md);
    font-weight: 600;
    transition: transform 0.2s;
}

.btn:hover {
    transform: scale(1.05);
    text-decoration: none;
}

.features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--space-8);
    padding: var(--space-8);
}

.feature {
    text-align: center;
    padding: var(--space-6);
}

.feature-icon {
    font-size: 3rem;
    margin-bottom: var(--space-4);
}
""",
            "academic": """
/* Academic Report Layout */
.content {
    max-width: 700px;
    margin: 0 auto;
    font-family: 'Georgia', 'Noto Serif TC', serif;
    font-size: 1.1rem;
}

.content h1 {
    text-align: center;
    margin-bottom: var(--space-8);
    padding-bottom: var(--space-4);
    border-bottom: 2px solid var(--text);
}

.abstract {
    background: rgba(0,0,0,0.03);
    padding: var(--space-6);
    border-left: 4px solid var(--primary);
    margin: var(--space-8) 0;
    font-style: italic;
}

.footnote {
    font-size: 0.85rem;
    color: var(--text);
    opacity: 0.7;
    border-top: 1px solid rgba(0,0,0,0.1);
    padding-top: var(--space-4);
    margin-top: var(--space-8);
}

.citation {
    vertical-align: super;
    font-size: 0.75rem;
    color: var(--primary);
}
""",
            "docs": """
/* Documentation Layout */
.page-wrapper {
    display: grid;
    grid-template-columns: 250px 1fr 200px;
    gap: var(--space-6);
    max-width: 1400px;
    margin: 0 auto;
}

.sidebar-left {
    position: sticky;
    top: var(--space-4);
    height: fit-content;
}

.sidebar-right {
    position: sticky;
    top: var(--space-4);
    height: fit-content;
}

.api-block {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: var(--radius-md);
    padding: var(--space-4);
    margin: var(--space-4) 0;
}

.api-method {
    display: inline-block;
    padding: var(--space-1) var(--space-2);
    background: var(--primary);
    color: white;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    margin-right: var(--space-2);
}

.param-table {
    font-size: 0.9rem;
}

.param-table th {
    background: transparent;
    border-bottom: 2px solid var(--primary);
}

@media (max-width: 1100px) {
    .page-wrapper {
        grid-template-columns: 1fr;
    }
}
"""
        }

        return css_map.get(layout_id, css_map["sidebar-nav"])

    def suggest_structure(self, content_type: str, goal: str) -> str:
        """
        根據內容類型建議報告結構

        Args:
            content_type: 內容類型 ID
            goal: 任務目標

        Returns:
            建議的報告結構 (Markdown 格式)
        """
        structures = {
            "tutorial": """# {title}

## 概述
[簡介這個教學的目標和預期成果]

## 前置需求
- [需求 1]
- [需求 2]

## 步驟 1: [標題]
[說明]

```code
[程式碼範例]
```

## 步驟 2: [標題]
[說明]

## 步驟 3: [標題]
[說明]

## 常見問題
### Q: [問題]
A: [解答]

## 總結
[總結學到的內容]

## 延伸閱讀
- [資源連結]
""",
            "comparison": """# {title}

## 概述
[比較的背景和目的]

## 比較項目

| 特徵 | 選項 A | 選項 B | 選項 C |
|------|--------|--------|--------|
| [特徵 1] | [值] | [值] | [值] |
| [特徵 2] | [值] | [值] | [值] |

## 詳細分析

### 選項 A
**優點:**
- [優點 1]

**缺點:**
- [缺點 1]

### 選項 B
...

## 使用情境建議
- 適合 [情境 A] 時使用 [選項 A]
- 適合 [情境 B] 時使用 [選項 B]

## 結論
[總結建議]
""",
            "report": """# {title}

## 摘要
[100-150 字的摘要]

## 背景
[研究背景和動機]

## 方法論
[研究方法說明]

## 主要發現

### 發現 1
[詳細說明]

### 發現 2
[詳細說明]

## 數據分析
[相關數據和圖表]

## 討論
[對發現的解讀]

## 結論與建議
[總結和未來建議]

## 參考資料
1. [來源 1]
2. [來源 2]
""",
            "reference": """# {title}

## 概述
[API/功能的簡介]

## 安裝/設置
```bash
[安裝指令]
```

## 快速開始
```code
[基本使用範例]
```

## API 參考

### function_name(param1, param2)
**描述:** [功能說明]

**參數:**
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| param1 | string | 是 | [說明] |
| param2 | number | 否 | [說明] |

**回傳值:**
[回傳值說明]

**範例:**
```code
[使用範例]
```

## 進階用法
[進階功能說明]

## 常見問題
[FAQ]
""",
            "list": """# {title}

## 簡介
[清單主題介紹]

## 1. [項目名稱]
**評分:** ⭐⭐⭐⭐⭐

[說明]

**特點:**
- [特點 1]
- [特點 2]

## 2. [項目名稱]
**評分:** ⭐⭐⭐⭐

[說明]

## 3. [項目名稱]
...

## 總結比較
| 排名 | 名稱 | 評分 | 適合 |
|------|------|------|------|
| 1 | [名稱] | ⭐⭐⭐⭐⭐ | [適用情境] |

## 結論
[總結建議]
""",
            "overview": """# {title}

## 什麼是 [主題]？
[基本定義和介紹]

## 為什麼重要？
[重要性說明]

## 核心概念

### 概念 1
[說明]

### 概念 2
[說明]

## 主要特點
- **[特點 1]:** [說明]
- **[特點 2]:** [說明]
- **[特點 3]:** [說明]

## 使用場景
1. [場景 1]
2. [場景 2]

## 入門指南
[如何開始的簡要說明]

## 延伸學習
- [資源 1]
- [資源 2]
"""
        }

        structure = structures.get(content_type, structures["report"])
        return structure.replace("{title}", goal)

    def enhance_html(self, html: str, layout_id: str, theme_id: str = "default") -> str:
        """
        強化 HTML 輸出，加入版面特定的結構

        Args:
            html: 原始 HTML 內容
            layout_id: 版面 ID
            theme_id: 主題 ID

        Returns:
            強化後的完整 HTML
        """
        css = self.get_layout_css(layout_id, theme_id)
        layout = self.LAYOUTS.get(layout_id, self.LAYOUTS["sidebar-nav"])

        # 根據版面調整 HTML 結構
        wrapper_class = layout.get("css_class", "layout-default")

        full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
{css}
    </style>
</head>
<body class="{wrapper_class}">
    <div class="container">
        <div class="content">
{html}
        </div>
    </div>
    <script>
        // 程式碼複製功能
        document.querySelectorAll('pre').forEach(pre => {{
            const btn = document.createElement('button');
            btn.className = 'copy-btn';
            btn.textContent = 'Copy';
            btn.onclick = () => {{
                navigator.clipboard.writeText(pre.textContent);
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = 'Copy', 2000);
            }};
            pre.style.position = 'relative';
            pre.appendChild(btn);
        }});

        // 平滑滾動
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', e => {{
                e.preventDefault();
                document.querySelector(anchor.getAttribute('href'))?.scrollIntoView({{
                    behavior: 'smooth'
                }});
            }});
        }});
    </script>
</body>
</html>"""

        return full_html


# 測試
if __name__ == "__main__":
    renderer = Renderer()

    # 測試內容分析
    test_content = """
# Python Asyncio 教學

## 步驟 1: 安裝

首先安裝 Python 3.7+

```python
import asyncio

async def hello():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(hello())
```

## 步驟 2: 基本概念

asyncio 是 Python 的異步 I/O 框架...

## 步驟 3: 進階用法

```python
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```
"""

    result = renderer.analyze_content(test_content, "Python asyncio 教學")
    print("分析結果:")
    print(f"  內容類型: {result['content_type']}")
    print(f"  推薦版面: {result['recommended_layout']}")
    print(f"  色彩主題: {result['color_theme']}")
    print(f"  原因: {result.get('reasoning', 'N/A')}")
