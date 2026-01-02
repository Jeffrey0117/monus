"""
Browser Tool - Playwright 封裝
LLM 只能說要用哪個工具+參數，這裡負責處理 timeout、retry、反爬、DOM 問題
"""
import asyncio
import urllib.parse
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from readability import Document
import re
import random

# DuckDuckGo Search API
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False


class BrowserTool:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _ensure_browser(self):
        """確保瀏覽器已啟動"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            self._page = await self._context.new_page()
            # 隱藏自動化特徵
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        使用 DuckDuckGo Search API 搜尋（最穩定）
        返回 [{title, url, snippet}, ...]
        """
        # 優先使用 DuckDuckGo Search API
        if HAS_DDGS:
            try:
                results = []
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=max_results))
                    for r in search_results:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")[:200]
                        })
                if results:
                    return results
            except Exception as e:
                print(f"[Browser] DDGS error: {e}")

        # 備用：使用 Playwright 爬取
        await self._ensure_browser()
        return await self._search_bing(query, max_results)

    async def _search_bing(self, query: str, max_results: int = 10) -> list[dict]:
        """備用：使用 Bing 搜尋"""
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.bing.com/search?q={encoded_query}"

        try:
            await self._page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(1 + random.random())

            results = []
            items = await self._page.query_selector_all("li.b_algo")

            for item in items[:max_results]:
                try:
                    title_el = await item.query_selector("h2 a")
                    snippet_el = await item.query_selector("p, .b_caption p")

                    if title_el:
                        title = await title_el.inner_text()
                        url = await title_el.get_attribute("href")
                        snippet = ""
                        if snippet_el:
                            snippet = await snippet_el.inner_text()

                        if url and url.startswith("http"):
                            results.append({
                                "title": title.strip(),
                                "url": url,
                                "snippet": snippet.strip()[:200]
                            })
                except Exception:
                    continue

            return results

        except Exception as e:
            return [{"error": str(e)}]

    async def open(self, url: str, timeout: int = 30000) -> dict:
        """
        開啟指定網頁
        返回 {success, url, title, error?}
        """
        await self._ensure_browser()

        try:
            response = await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            title = await self._page.title()

            return {
                "success": True,
                "url": self._page.url,
                "title": title,
                "status": response.status if response else None
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

    async def extract(self, mode: str = "readability") -> dict:
        """
        提取當前頁面內容
        mode: "readability" | "full" | "text"
        返回 {title, content, url}
        """
        await self._ensure_browser()

        try:
            html = await self._page.content()
            url = self._page.url

            if mode == "readability":
                doc = Document(html)
                title = doc.title()
                content = doc.summary()
                # 清理 HTML 標籤
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
            elif mode == "text":
                title = await self._page.title()
                content = await self._page.inner_text("body")
            else:  # full
                title = await self._page.title()
                content = html

            return {
                "title": title,
                "content": content[:10000],
                "url": url
            }
        except Exception as e:
            return {
                "error": str(e),
                "url": self._page.url if self._page else None
            }

    async def screenshot(self, path: str) -> dict:
        """
        截圖當前頁面
        返回 {success, path, error?}
        """
        await self._ensure_browser()

        try:
            await self._page.screenshot(path=path, full_page=True)
            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    async def close(self):
        """關閉瀏覽器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        self._context = None
        self._page = None
