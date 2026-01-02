"""
Code Tool - Shell/Python/Git 執行封裝
負責整理、轉換、後處理
"""
import subprocess
import sys
from typing import Optional


class CodeTool:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def run(self, cmd: str, cwd: str = ".") -> dict:
        """
        執行 shell 命令
        返回 {success, stdout, stderr, returncode, error?}
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {self.timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }

    def run_python(self, code: str, cwd: str = ".") -> dict:
        """
        執行 Python 程式碼
        返回 {success, stdout, stderr, error?}
        """
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Python execution timed out after {self.timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def git(self, args: str, cwd: str = ".") -> dict:
        """
        執行 git 命令
        返回 {success, stdout, stderr, error?}
        """
        return self.run(f"git {args}", cwd=cwd)
