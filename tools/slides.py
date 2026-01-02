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
        try:
            # 分割投影片
            slides = markdown_content.split('\n---\n')
            slides = [s.strip() for s in slides if s.strip()]

            if not slides:
                # 如果沒有 --- 分隔，嘗試按標題分割
                slides = self._split_by_headers(markdown_content)

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

            # 組合完整 HTML
            full_html = self._build_html(slides_html, title, theme)

            # 寫入檔案
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(full_html, encoding='utf-8')

            return {
                "success": True,
                "path": output_path,
                "slides_count": len(slides)
            }

        except Exception as e:
            return {
                "success": False,
                "path": output_path,
                "error": str(e)
            }

    def _split_by_headers(self, content: str) -> list:
        """按 ## 標題分割投影片"""
        lines = content.split('\n')
        slides = []
        current_slide = []

        for line in lines:
            if line.startswith('## ') and current_slide:
                slides.append('\n'.join(current_slide))
                current_slide = [line]
            else:
                current_slide.append(line)

        if current_slide:
            slides.append('\n'.join(current_slide))

        return slides if slides else [content]

    def _build_html(self, slides_html: list, title: str, theme: str) -> str:
        """建構完整的 HTML 簡報"""
        slides_joined = '\n'.join(slides_html)
        total = len(slides_html)

        return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        {self._get_theme_css(theme)}
    </style>
</head>
<body>
    <div class="slides-container">
        {slides_joined}
    </div>

    <div class="controls">
        <button onclick="prevSlide()" title="上一張 (←)">◀</button>
        <span id="progress">1 / {total}</span>
        <button onclick="nextSlide()" title="下一張 (→)">▶</button>
        <button onclick="toggleFullscreen()" title="全螢幕 (F)">⛶</button>
    </div>

    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>

    <script>
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const total = slides.length;

        function showSlide(n) {{
            slides.forEach((s, i) => {{
                s.classList.toggle('active', i === n);
            }});
            document.getElementById('progress').textContent = `${{n + 1}} / ${{total}}`;
            document.getElementById('progressFill').style.width = `${{((n + 1) / total) * 100}}%`;
        }}

        function nextSlide() {{
            currentSlide = (currentSlide + 1) % total;
            showSlide(currentSlide);
        }}

        function prevSlide() {{
            currentSlide = (currentSlide - 1 + total) % total;
            showSlide(currentSlide);
        }}

        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else {{
                document.exitFullscreen();
            }}
        }}

        // 鍵盤控制
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {{
                e.preventDefault();
                nextSlide();
            }}
            if (e.key === 'ArrowLeft' || e.key === 'Backspace') {{
                e.preventDefault();
                prevSlide();
            }}
            if (e.key === 'f' || e.key === 'F') {{
                toggleFullscreen();
            }}
            if (e.key === 'Home') {{
                currentSlide = 0;
                showSlide(0);
            }}
            if (e.key === 'End') {{
                currentSlide = total - 1;
                showSlide(currentSlide);
            }}
        }});

        // 觸控支援
        let touchStartX = 0;
        document.addEventListener('touchstart', (e) => {{
            touchStartX = e.touches[0].clientX;
        }});
        document.addEventListener('touchend', (e) => {{
            const diff = touchStartX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 50) {{
                if (diff > 0) nextSlide();
                else prevSlide();
            }}
        }});

        // 初始化
        showSlide(0);
        hljs.highlightAll();
    </script>
</body>
</html>'''

    def _get_theme_css(self, theme: str) -> str:
        """取得主題 CSS"""
        themes = {
            "default": """
                :root {
                    --bg: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    --text: #eaeaea;
                    --accent: #e94560;
                    --code-bg: #0f0f1a;
                    --control-bg: rgba(0, 0, 0, 0.6);
                }
            """,
            "dark": """
                :root {
                    --bg: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
                    --text: #c9d1d9;
                    --accent: #58a6ff;
                    --code-bg: #0d1117;
                    --control-bg: rgba(22, 27, 34, 0.9);
                }
            """,
            "minimal": """
                :root {
                    --bg: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
                    --text: #1a1a1a;
                    --accent: #0066cc;
                    --code-bg: #f6f8fa;
                    --control-bg: rgba(255, 255, 255, 0.9);
                }
            """
        }

        base_css = themes.get(theme, themes["default"])

        return base_css + """
            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: "Microsoft JhengHei", "PingFang TC", "Noto Sans TC",
                             "Source Han Sans TC", system-ui, sans-serif;
                background: var(--bg);
                color: var(--text);
                overflow: hidden;
                min-height: 100vh;
            }

            .slides-container {
                width: 100vw;
                height: 100vh;
                position: relative;
            }

            .slide {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: none;
                align-items: center;
                justify-content: center;
                padding: 8% 10%;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .slide.active {
                display: flex;
                opacity: 1;
            }

            .content {
                max-width: 1400px;
                width: 100%;
                text-align: center;
            }

            h1 {
                font-size: clamp(2.5rem, 6vw, 4.5rem);
                margin-bottom: 1rem;
                color: var(--accent);
                font-weight: 700;
                line-height: 1.2;
            }

            h2 {
                font-size: clamp(2rem, 4vw, 3rem);
                margin-bottom: 0.8rem;
                font-weight: 600;
            }

            h3 {
                font-size: clamp(1.5rem, 3vw, 2rem);
                margin-bottom: 0.6rem;
                font-weight: 500;
            }

            p {
                font-size: clamp(1.2rem, 2.5vw, 1.8rem);
                line-height: 1.8;
                margin: 0.5em 0;
            }

            ul, ol {
                text-align: left;
                font-size: clamp(1.1rem, 2vw, 1.5rem);
                line-height: 2;
                margin: 1em auto;
                max-width: 900px;
                padding-left: 1.5em;
            }

            li {
                margin: 0.4em 0;
            }

            li::marker {
                color: var(--accent);
            }

            pre {
                background: var(--code-bg);
                border-radius: 12px;
                padding: 1.5em;
                text-align: left;
                overflow-x: auto;
                margin: 1.5em auto;
                max-width: 900px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            code {
                font-family: "Fira Code", "JetBrains Mono", "Consolas", monospace;
                font-size: clamp(0.9rem, 1.5vw, 1.2rem);
            }

            :not(pre) > code {
                background: var(--code-bg);
                padding: 3px 8px;
                border-radius: 4px;
            }

            table {
                border-collapse: collapse;
                margin: 1.5em auto;
                font-size: clamp(1rem, 1.5vw, 1.3rem);
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                overflow: hidden;
            }

            th, td {
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 0.8em 1.5em;
            }

            th {
                background: var(--accent);
                color: white;
                font-weight: 600;
            }

            blockquote {
                border-left: 4px solid var(--accent);
                margin: 1.5em auto;
                padding: 1em 1.5em;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 0 8px 8px 0;
                max-width: 800px;
                text-align: left;
                font-style: italic;
            }

            .controls {
                position: fixed;
                bottom: 30px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 15px;
                align-items: center;
                background: var(--control-bg);
                padding: 12px 24px;
                border-radius: 50px;
                backdrop-filter: blur(10px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                z-index: 1000;
            }

            .controls button {
                background: transparent;
                color: var(--text);
                border: 2px solid var(--accent);
                width: 44px;
                height: 44px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 1.2rem;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .controls button:hover {
                background: var(--accent);
                color: white;
                transform: scale(1.1);
            }

            #progress {
                color: var(--text);
                font-size: 1rem;
                font-weight: 500;
                min-width: 60px;
                text-align: center;
            }

            .progress-bar {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                z-index: 1001;
            }

            .progress-fill {
                height: 100%;
                background: var(--accent);
                width: 0;
                transition: width 0.3s ease;
            }

            /* 響應式調整 */
            @media (max-width: 768px) {
                .slide {
                    padding: 5%;
                }

                .controls {
                    bottom: 20px;
                    padding: 10px 16px;
                    gap: 10px;
                }

                .controls button {
                    width: 36px;
                    height: 36px;
                    font-size: 1rem;
                }
            }

            /* 列印樣式 */
            @media print {
                .controls, .progress-bar { display: none; }
                .slide {
                    display: flex !important;
                    page-break-after: always;
                    position: relative;
                    height: auto;
                    min-height: 100vh;
                }
            }
        """


# 同步包裝器
def generate_slides_sync(markdown_content: str, output_path: str,
                         title: str = "Presentation", theme: str = "default") -> dict:
    """同步版本的簡報生成"""
    import asyncio

    async def _run():
        tool = SlidesTool()
        return await tool.generate(markdown_content, output_path, title, theme)

    return asyncio.run(_run())
