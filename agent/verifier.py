"""
Verifier - 驗證規則
沒有 verifier = 玩具 agent
有 verifier = 可用系統
"""
from typing import Callable
from collections import Counter
from urllib.parse import urlparse


class Verifier:
    def __init__(self, min_sources: int = 5, min_word_count: int = 800):
        self.min_sources = min_sources
        self.min_word_count = min_word_count
        self.rules: list[Callable] = []
        self._setup_default_rules()

    def _setup_default_rules(self):
        """設定預設驗證規則"""
        self.rules = [
            self._has_min_sources,
            self._sources_have_url_and_title,
            self._report_exists,
            self._report_has_sections,
            self._not_all_from_same_domain,
            self._has_min_word_count
        ]

    def verify(self, task_state: dict, report_content: str = "") -> dict:
        """
        執行所有驗證規則
        返回 {passed: bool, results: [{rule, passed, message}]}
        """
        results = []

        for rule in self.rules:
            try:
                passed, message = rule(task_state, report_content)
                results.append({
                    "rule": rule.__name__,
                    "passed": passed,
                    "message": message
                })
            except Exception as e:
                results.append({
                    "rule": rule.__name__,
                    "passed": False,
                    "message": f"Error: {str(e)}"
                })

        all_passed = all(r["passed"] for r in results)

        return {
            "passed": all_passed,
            "results": results
        }

    def _has_min_sources(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查是否有足夠的來源"""
        sources = task.get("memory", {}).get("sources_collected", [])
        count = len(sources)
        passed = count >= self.min_sources
        return passed, f"Sources: {count}/{self.min_sources}"

    def _sources_have_url_and_title(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查所有來源是否都有 URL 和標題"""
        sources = task.get("memory", {}).get("sources_collected", [])

        if not sources:
            return False, "No sources found"

        invalid = []
        for i, src in enumerate(sources):
            if not src.get("url") or not src.get("title"):
                invalid.append(i + 1)

        if invalid:
            return False, f"Sources missing url/title: {invalid}"
        return True, "All sources have url and title"

    def _report_exists(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查報告是否存在"""
        if report and len(report.strip()) > 0:
            return True, "Report exists"
        return False, "Report is empty or missing"

    def _report_has_sections(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查報告是否有必要的章節"""
        required_sections = ["##", "摘要", "來源"]

        if not report:
            return False, "No report content"

        missing = []
        for section in required_sections:
            if section not in report:
                missing.append(section)

        if missing:
            return False, f"Missing sections: {missing}"
        return True, "All required sections present"

    def _not_all_from_same_domain(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查來源是否來自不同網域"""
        sources = task.get("memory", {}).get("sources_collected", [])

        if len(sources) < 2:
            return True, "Not enough sources to check diversity"

        domains = []
        for src in sources:
            url = src.get("url", "")
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
                domains.append(domain)
            except Exception:
                pass

        domain_counts = Counter(domains)
        unique_domains = len(domain_counts)

        if unique_domains < 2:
            return False, f"All sources from same domain: {list(domain_counts.keys())}"

        # 檢查是否有單一網域佔比過高
        total = len(domains)
        for domain, count in domain_counts.items():
            if count / total > 0.7:
                return False, f"Domain '{domain}' represents {count}/{total} sources"

        return True, f"Sources from {unique_domains} different domains"

    def _has_min_word_count(self, task: dict, report: str) -> tuple[bool, str]:
        """檢查報告字數"""
        if not report:
            return False, "No report content"

        # 計算中英文混合字數
        word_count = len(report)

        if word_count >= self.min_word_count:
            return True, f"Word count: {word_count}/{self.min_word_count}"
        return False, f"Word count too low: {word_count}/{self.min_word_count}"

    def get_failed_rules(self, task_state: dict, report_content: str = "") -> list[str]:
        """取得失敗的規則列表"""
        result = self.verify(task_state, report_content)
        return [r["rule"] for r in result["results"] if not r["passed"]]
