"""
Sandbox Tool - 隔離執行環境
支援 Docker 容器或本地子進程執行
"""
import asyncio
import subprocess
import os
import json
import shutil
from pathlib import Path
from typing import Optional


class SandboxTool:
    """
    沙箱執行環境
    MVP 版本：使用本地子進程 + 工作目錄隔離
    進階版本：可切換為 Docker 容器
    """

    def __init__(self, workspace_dir: str = None, use_docker: bool = False):
        self.use_docker = use_docker
        self.container_id = None

        # 設定工作目錄
        if workspace_dir:
            self.workspace = Path(workspace_dir)
        else:
            self.workspace = Path(__file__).parent.parent / "sandbox_workspace"

        self.workspace.mkdir(parents=True, exist_ok=True)

    async def init_project(self, project_name: str, template: str = "vite-react") -> dict:
        """
        初始化專案

        Args:
            project_name: 專案名稱
            template: 專案模板 (vite-react, vite-vanilla, python, node)

        Returns:
            {success, path, files}
        """
        project_path = self.workspace / project_name

        # 清理舊專案
        if project_path.exists():
            shutil.rmtree(project_path)

        project_path.mkdir(parents=True)

        if template == "vite-react":
            return await self._init_vite_react(project_path)
        elif template == "vite-vanilla":
            return await self._init_vite_vanilla(project_path)
        elif template == "python":
            return await self._init_python(project_path)
        elif template == "node":
            return await self._init_node(project_path)
        elif template == "html":
            return await self._init_html(project_path)
        else:
            return {"success": False, "error": f"Unknown template: {template}"}

    async def _init_vite_react(self, project_path: Path) -> dict:
        """初始化 Vite + React 專案"""
        # 建立基本結構
        (project_path / "src").mkdir()
        (project_path / "public").mkdir()

        # package.json
        package_json = {
            "name": project_path.name,
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0"
            }
        }
        (project_path / "package.json").write_text(
            json.dumps(package_json, indent=2), encoding="utf-8"
        )

        # vite.config.js
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
        (project_path / "vite.config.js").write_text(vite_config, encoding="utf-8")

        # index.html
        index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Monus App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
        (project_path / "index.html").write_text(index_html, encoding="utf-8")

        # src/main.jsx
        main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        (project_path / "src" / "main.jsx").write_text(main_jsx, encoding="utf-8")

        # src/App.jsx
        app_jsx = """import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <h1>Monus App</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
      </div>
    </div>
  )
}

export default App
"""
        (project_path / "src" / "App.jsx").write_text(app_jsx, encoding="utf-8")

        # src/index.css
        index_css = """:root {
  font-family: Inter, system-ui, sans-serif;
  background: #242424;
  color: rgba(255, 255, 255, 0.87);
}

body {
  margin: 0;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.app {
  text-align: center;
}

button {
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  background-color: #1a1a1a;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}
"""
        (project_path / "src" / "index.css").write_text(index_css, encoding="utf-8")

        return {
            "success": True,
            "path": str(project_path),
            "files": self._list_files(project_path)
        }

    async def _init_html(self, project_path: Path) -> dict:
        """初始化純 HTML 專案"""
        # index.html
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monus App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="app">
        <h1>Hello Monus!</h1>
    </div>
    <script src="script.js"></script>
</body>
</html>
"""
        (project_path / "index.html").write_text(index_html, encoding="utf-8")

        # style.css
        style_css = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

#app {
    text-align: center;
}

h1 {
    font-size: 3rem;
    background: linear-gradient(90deg, #00d9ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
"""
        (project_path / "style.css").write_text(style_css, encoding="utf-8")

        # script.js
        script_js = """// Monus Generated App
console.log('Monus App Started!');

document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    // Your code here
});
"""
        (project_path / "script.js").write_text(script_js, encoding="utf-8")

        return {
            "success": True,
            "path": str(project_path),
            "files": self._list_files(project_path)
        }

    async def _init_vite_vanilla(self, project_path: Path) -> dict:
        """初始化 Vite Vanilla 專案"""
        # 類似 vite-react 但不用 React
        (project_path / "src").mkdir()

        package_json = {
            "name": project_path.name,
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build"
            },
            "devDependencies": {
                "vite": "^5.0.0"
            }
        }
        (project_path / "package.json").write_text(
            json.dumps(package_json, indent=2), encoding="utf-8"
        )

        return {
            "success": True,
            "path": str(project_path),
            "files": self._list_files(project_path)
        }

    async def _init_python(self, project_path: Path) -> dict:
        """初始化 Python 專案"""
        # main.py
        main_py = '''"""
Monus Generated Python App
"""

def main():
    print("Hello from Monus!")

if __name__ == "__main__":
    main()
'''
        (project_path / "main.py").write_text(main_py, encoding="utf-8")

        # requirements.txt
        (project_path / "requirements.txt").write_text("", encoding="utf-8")

        return {
            "success": True,
            "path": str(project_path),
            "files": self._list_files(project_path)
        }

    async def _init_node(self, project_path: Path) -> dict:
        """初始化 Node.js 專案"""
        package_json = {
            "name": project_path.name,
            "version": "1.0.0",
            "main": "index.js",
            "scripts": {
                "start": "node index.js"
            }
        }
        (project_path / "package.json").write_text(
            json.dumps(package_json, indent=2), encoding="utf-8"
        )

        index_js = """// Monus Generated Node.js App
console.log('Hello from Monus!');
"""
        (project_path / "index.js").write_text(index_js, encoding="utf-8")

        return {
            "success": True,
            "path": str(project_path),
            "files": self._list_files(project_path)
        }

    def _list_files(self, path: Path, prefix: str = "") -> list:
        """列出目錄下所有檔案"""
        files = []
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
            if item.name == 'node_modules':
                continue

            rel_path = f"{prefix}{item.name}"
            if item.is_dir():
                files.append({"path": rel_path, "type": "dir"})
                files.extend(self._list_files(item, f"{rel_path}/"))
            else:
                files.append({
                    "path": rel_path,
                    "type": "file",
                    "size": item.stat().st_size
                })
        return files

    async def write_file(self, project_name: str, file_path: str, content: str) -> dict:
        """
        寫入檔案

        Args:
            project_name: 專案名稱
            file_path: 相對路徑
            content: 檔案內容

        Returns:
            {success, path}
        """
        full_path = self.workspace / project_name / file_path

        # 確保目錄存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(full_path),
            "relative_path": file_path
        }

    async def read_file(self, project_name: str, file_path: str) -> dict:
        """
        讀取檔案

        Args:
            project_name: 專案名稱
            file_path: 相對路徑

        Returns:
            {success, content}
        """
        full_path = self.workspace / project_name / file_path

        if not full_path.exists():
            return {"success": False, "error": "File not found"}

        content = full_path.read_text(encoding="utf-8")

        return {
            "success": True,
            "content": content,
            "path": file_path
        }

    async def delete_file(self, project_name: str, file_path: str) -> dict:
        """刪除檔案"""
        full_path = self.workspace / project_name / file_path

        if full_path.exists():
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()

        return {"success": True, "path": file_path}

    async def list_files(self, project_name: str) -> dict:
        """列出專案檔案"""
        project_path = self.workspace / project_name

        if not project_path.exists():
            return {"success": False, "error": "Project not found"}

        return {
            "success": True,
            "files": self._list_files(project_path)
        }

    async def run_command(self, project_name: str, command: str, timeout: int = 60) -> dict:
        """
        執行命令

        Args:
            project_name: 專案名稱
            command: 要執行的命令
            timeout: 超時秒數

        Returns:
            {success, stdout, stderr, returncode}
        """
        project_path = self.workspace / project_name

        if not project_path.exists():
            return {"success": False, "error": "Project not found"}

        try:
            # 使用 subprocess 執行
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {"success": False, "error": "Command timeout"}

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": process.returncode
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_deps(self, project_name: str) -> dict:
        """安裝依賴"""
        project_path = self.workspace / project_name

        # 檢查是 Node 還是 Python 專案
        if (project_path / "package.json").exists():
            return await self.run_command(project_name, "npm install", timeout=120)
        elif (project_path / "requirements.txt").exists():
            return await self.run_command(project_name, "pip install -r requirements.txt", timeout=120)
        else:
            return {"success": True, "message": "No dependencies to install"}

    async def start_dev_server(self, project_name: str, port: int = 5173) -> dict:
        """啟動開發伺服器（背景執行）"""
        project_path = self.workspace / project_name

        if (project_path / "package.json").exists():
            # Node.js 專案
            command = f"npm run dev -- --port {port}"
        else:
            # 純 HTML 專案 - 使用 Python http.server
            command = f"python -m http.server {port}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            # 等待一下確保啟動
            await asyncio.sleep(2)

            return {
                "success": True,
                "port": port,
                "url": f"http://localhost:{port}",
                "pid": process.pid
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_project_path(self, project_name: str) -> Path:
        """取得專案完整路徑"""
        return self.workspace / project_name
