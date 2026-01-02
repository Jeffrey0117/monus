"""
File System Tool - 檔案操作封裝
負責所有產物落地
"""
import os
import json
from pathlib import Path
from typing import Any, Optional


class FileTool:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)

    def write(self, path: str, content: str) -> dict:
        """
        寫入檔案
        返回 {success, path, error?}
        """
        try:
            full_path = self.base_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(full_path)
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def read(self, path: str) -> dict:
        """
        讀取檔案
        返回 {success, content, error?}
        """
        try:
            full_path = self.base_dir / path
            content = full_path.read_text(encoding="utf-8")
            return {
                "success": True,
                "content": content,
                "path": str(full_path)
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def exists(self, path: str) -> bool:
        """檢查檔案是否存在"""
        return (self.base_dir / path).exists()

    def write_json(self, path: str, data: Any) -> dict:
        """
        寫入 JSON 檔案
        返回 {success, path, error?}
        """
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return self.write(path, content)
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def read_json(self, path: str) -> dict:
        """
        讀取 JSON 檔案
        返回 {success, data, error?}
        """
        try:
            result = self.read(path)
            if not result["success"]:
                return result
            data = json.loads(result["content"])
            return {
                "success": True,
                "data": data,
                "path": result["path"]
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "path": path,
                "error": f"JSON parse error: {str(e)}"
            }

    def list_dir(self, path: str = ".") -> dict:
        """
        列出目錄內容
        返回 {success, files, dirs, error?}
        """
        try:
            full_path = self.base_dir / path
            files = []
            dirs = []

            for item in full_path.iterdir():
                if item.is_file():
                    files.append(item.name)
                elif item.is_dir():
                    dirs.append(item.name)

            return {
                "success": True,
                "files": files,
                "dirs": dirs,
                "path": str(full_path)
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }

    def append(self, path: str, content: str) -> dict:
        """
        追加內容到檔案
        返回 {success, path, error?}
        """
        try:
            full_path = self.base_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(full_path)
            }
        except Exception as e:
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }
