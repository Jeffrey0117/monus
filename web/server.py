"""
Monus Web Server - FastAPI 後端
提供 API 讓前端呼叫執行任務
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

# 確保可以 import 本地模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from agent.planner import Planner
from agent.reasoner import Reasoner
from agent.evaluator import Evaluator
from agent.verifier import Verifier
from agent.memory import Memory
from agent.loop import AgentLoop
from agent.coder import Coder
from tools.sandbox import SandboxTool


# 全域任務管理
active_tasks: dict = {}
task_progress: dict = {}


class TaskRequest(BaseModel):
    """任務請求"""
    goal: str
    output_format: str = "web"  # pdf, slides, web, all
    theme: str = "default"
    model: str = "deepseek-chat"


class TaskStatus(BaseModel):
    """任務狀態"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int
    phase: str
    message: str
    outputs: Optional[dict] = None


class WebSocketUI:
    """WebSocket 版本的 UI，用於即時推送進度"""

    def __init__(self, websocket: WebSocket, task_id: str):
        self.websocket = websocket
        self.task_id = task_id
        self.current_phase = ""
        self.sources_count = 0
        self.iteration = 0
        self.max_iterations = 20

    async def _send(self, data: dict):
        """發送訊息到 WebSocket"""
        try:
            await self.websocket.send_json(data)
        except Exception:
            pass

    def start_run(self, run_id: str, goal: str):
        asyncio.create_task(self._send({
            "type": "start",
            "task_id": self.task_id,
            "run_id": run_id,
            "goal": goal
        }))

    def update_phase(self, phase: str):
        self.current_phase = phase
        asyncio.create_task(self._send({
            "type": "phase",
            "task_id": self.task_id,
            "phase": phase
        }))

    def update_step(self, step: str, status: str = "running"):
        asyncio.create_task(self._send({
            "type": "step",
            "task_id": self.task_id,
            "step": step,
            "status": status
        }))

    def update_iteration(self, iteration: int, max_iterations: int):
        self.iteration = iteration
        self.max_iterations = max_iterations
        progress = int((iteration / max_iterations) * 100)
        asyncio.create_task(self._send({
            "type": "progress",
            "task_id": self.task_id,
            "iteration": iteration,
            "max_iterations": max_iterations,
            "progress": progress
        }))

    def update_sources(self, count: int):
        self.sources_count = count
        asyncio.create_task(self._send({
            "type": "sources",
            "task_id": self.task_id,
            "count": count
        }))

    def show_action(self, tool: str, input_data: str):
        asyncio.create_task(self._send({
            "type": "action",
            "task_id": self.task_id,
            "tool": tool,
            "input": input_data[:100]
        }))

    def show_result(self, success: bool, message: str = ""):
        asyncio.create_task(self._send({
            "type": "result",
            "task_id": self.task_id,
            "success": success,
            "message": message
        }))

    def show_outputs(self, outputs: dict):
        asyncio.create_task(self._send({
            "type": "outputs",
            "task_id": self.task_id,
            "outputs": outputs
        }))

    def show_verification(self, verification: dict):
        asyncio.create_task(self._send({
            "type": "verification",
            "task_id": self.task_id,
            "verification": verification
        }))

    def show_final_result(self, success: bool, run_id: str, quality_score: float = None):
        asyncio.create_task(self._send({
            "type": "complete",
            "task_id": self.task_id,
            "success": success,
            "run_id": run_id,
            "quality_score": quality_score
        }))

    def show_suggestions(self, suggestions: list):
        asyncio.create_task(self._send({
            "type": "suggestions",
            "task_id": self.task_id,
            "suggestions": suggestions
        }))


# FastAPI 應用
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期"""
    print("[Monus] Web Server starting...")
    yield
    print("[Monus] Web Server shutting down...")


app = FastAPI(
    title="Monus API",
    description="Autonomous Research Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案
runs_path = Path(__file__).parent.parent / "runs"
if runs_path.exists():
    app.mount("/runs", StaticFiles(directory=str(runs_path)), name="runs")


@app.get("/")
async def root():
    """首頁 - 返回前端 HTML"""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
async def health():
    """健康檢查"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/runs")
async def list_runs():
    """列出所有執行記錄"""
    runs_dir = Path(__file__).parent.parent / "runs"
    if not runs_dir.exists():
        return {"runs": []}

    runs = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True)[:20]:
        task_file = run_dir / "task.json"
        if task_file.exists():
            try:
                task = json.loads(task_file.read_text(encoding="utf-8"))

                # 檢查輸出檔案
                outputs = {}
                if (run_dir / "report.pdf").exists():
                    outputs["pdf"] = f"/runs/{run_dir.name}/report.pdf"
                if (run_dir / "slides.html").exists():
                    outputs["slides"] = f"/runs/{run_dir.name}/slides.html"
                if (run_dir / "index.html").exists():
                    outputs["web"] = f"/runs/{run_dir.name}/index.html"
                if (run_dir / "report.md").exists():
                    outputs["markdown"] = f"/runs/{run_dir.name}/report.md"

                runs.append({
                    "id": run_dir.name,
                    "goal": task.get("goal", "Unknown"),
                    "status": task.get("status", "unknown"),
                    "created_at": task.get("created_at", ""),
                    "outputs": outputs,
                    "steps_count": len(task.get("steps", []))
                })
            except Exception:
                pass

    return {"runs": runs}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """取得特定執行記錄"""
    run_dir = Path(__file__).parent.parent / "runs" / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    task_file = run_dir / "task.json"
    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task file not found")

    task = json.loads(task_file.read_text(encoding="utf-8"))

    # 讀取報告內容
    report_content = ""
    report_file = run_dir / "report.md"
    if report_file.exists():
        report_content = report_file.read_text(encoding="utf-8")

    # 檢查輸出檔案
    outputs = {}
    if (run_dir / "report.pdf").exists():
        outputs["pdf"] = f"/runs/{run_id}/report.pdf"
    if (run_dir / "slides.html").exists():
        outputs["slides"] = f"/runs/{run_id}/slides.html"
    if (run_dir / "index.html").exists():
        outputs["web"] = f"/runs/{run_id}/index.html"

    return {
        "id": run_id,
        "goal": task.get("goal", ""),
        "status": task.get("status", ""),
        "created_at": task.get("created_at", ""),
        "steps": task.get("steps", []),
        "outputs": outputs,
        "report": report_content
    }


@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """建立新任務（非同步執行）"""
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 記錄任務
    task_progress[task_id] = {
        "status": "pending",
        "goal": request.goal,
        "progress": 0,
        "phase": "initializing"
    }

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task created. Connect to WebSocket to start execution."
    }


# 初始化 Sandbox（全域）
sandbox = SandboxTool()


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket 連接 - 智能判斷研究或寫程式"""
    await websocket.accept()

    try:
        # 等待任務參數
        data = await websocket.receive_json()
        goal = data.get("goal", "")
        output_format = data.get("output_format", "web")
        theme = data.get("theme", "default")
        model = data.get("model", "deepseek-chat")

        if not goal:
            await websocket.send_json({"type": "error", "message": "Goal is required"})
            return

        # 建立 WebSocket UI
        ws_ui = WebSocketUI(websocket, task_id)

        # 初始化 Planner 判斷任務類型
        planner = Planner(model=model)
        task_classification = planner.classify_task(goal)

        await websocket.send_json({
            "type": "classification",
            "task_type": task_classification["type"],
            "template": task_classification.get("template"),
            "confidence": task_classification.get("confidence", 0.5),
            "reason": task_classification.get("reason", "")
        })

        # 根據任務類型執行不同流程
        if task_classification["type"] == "code":
            # === 程式碼生成模式 ===
            await run_code_generation(
                websocket, task_id, goal,
                task_classification.get("template", "html"),
                theme
            )
        else:
            # === 研究模式 ===
            await run_research(
                websocket, ws_ui, task_id, goal,
                output_format, theme, model, planner
            )

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {task_id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "message": str(e)
            })
        except:
            pass
    finally:
        if task_id in active_tasks:
            del active_tasks[task_id]


async def run_research(websocket, ws_ui, task_id, goal, output_format, theme, model, planner):
    """執行研究任務"""
    memory = Memory(runs_dir="runs")
    reasoner = Reasoner(model=model)
    evaluator = Evaluator(model=model)
    verifier = Verifier(min_sources=5, min_word_count=800)

    agent = AgentLoop(
        memory=memory,
        planner=planner,
        reasoner=reasoner,
        evaluator=evaluator,
        verifier=verifier,
        max_iterations=20,
        ui=ws_ui
    )

    result = await agent.run(goal, output_format=output_format, theme=theme)

    await websocket.send_json({
        "type": "done",
        "task_id": task_id,
        "mode": "research",
        "result": {
            "success": result.get("success", False),
            "run_id": result.get("run_id", ""),
            "outputs": result.get("outputs", {})
        }
    })


async def run_code_generation(websocket, task_id, goal, template, theme):
    """執行程式碼生成任務"""
    coder = Coder()

    await websocket.send_json({"type": "phase", "phase": "planning"})
    await websocket.send_json({"type": "progress", "progress": 5})

    plan = coder.analyze_task(goal, template)
    project_name = plan.get("project_name", "monus_project")

    await websocket.send_json({"type": "progress", "progress": 10})
    await websocket.send_json({
        "type": "step",
        "step": f"Creating project: {project_name}",
        "status": "running"
    })

    init_result = await sandbox.init_project(project_name, template)

    await websocket.send_json({
        "type": "project_created",
        "project_name": project_name,
        "files": init_result.get("files", [])
    })

    files_to_create = plan.get("files", [])
    total_files = len(files_to_create)
    existing_files = {}

    await websocket.send_json({"type": "phase", "phase": "writing"})

    for i, file_info in enumerate(files_to_create):
        file_path = file_info.get("path", "")
        file_desc = file_info.get("description", "")

        if not file_path:
            continue

        await websocket.send_json({"type": "file_start", "file": file_path})

        progress = 10 + int(((i + 1) / total_files) * 80)
        await websocket.send_json({"type": "progress", "progress": progress})
        await websocket.send_json({
            "type": "step",
            "step": f"Generating {file_path}",
            "status": "running"
        })

        content = ""
        for chunk in coder.generate_file(
            goal=goal,
            file_path=file_path,
            file_description=file_desc,
            existing_files=existing_files
        ):
            content += chunk
            await websocket.send_json({
                "type": "file_chunk",
                "file": file_path,
                "chunk": chunk
            })

        await sandbox.write_file(project_name, file_path, content)
        existing_files[file_path] = content

        await websocket.send_json({
            "type": "file_complete",
            "file": file_path,
            "content": content
        })

        await websocket.send_json({
            "type": "step",
            "step": f"Generated {file_path}",
            "status": "done"
        })

    await websocket.send_json({"type": "progress", "progress": 100})
    await websocket.send_json({"type": "phase", "phase": "complete"})

    await websocket.send_json({
        "type": "done",
        "task_id": task_id,
        "mode": "code",
        "result": {
            "success": True,
            "project_name": project_name,
            "preview_url": f"/sandbox/{project_name}/index.html",
            "files": list(existing_files.keys())
        }
    })


# ==================== Code Generator (Legacy) ====================


@app.get("/code")
async def code_page():
    """Code Generator 頁面"""
    return FileResponse(Path(__file__).parent / "static" / "code.html")


@app.websocket("/ws/code")
async def code_websocket(websocket: WebSocket):
    """Code Generation WebSocket - 即時生成程式碼"""
    await websocket.accept()

    coder = Coder()
    project_name = None
    goal = ""
    template = "html"

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "start":
                # 開始新專案
                goal = data.get("goal", "")
                template = data.get("template", "html")

                if not goal:
                    await websocket.send_json({"type": "error", "message": "Goal is required"})
                    continue

                # 分析任務
                await websocket.send_json({
                    "type": "progress",
                    "percent": 5,
                    "message": "Analyzing task..."
                })

                plan = coder.analyze_task(goal, template)
                project_name = plan.get("project_name", "monus_project")

                # 初始化專案
                await websocket.send_json({
                    "type": "progress",
                    "percent": 10,
                    "message": "Creating project..."
                })

                init_result = await sandbox.init_project(project_name, template)

                await websocket.send_json({
                    "type": "project_created",
                    "project_name": project_name,
                    "files": init_result.get("files", [])
                })

                # 生成每個檔案
                files_to_create = plan.get("files", [])
                total_files = len(files_to_create)
                existing_files = {}

                for i, file_info in enumerate(files_to_create):
                    file_path = file_info.get("path", "")
                    file_desc = file_info.get("description", "")

                    if not file_path:
                        continue

                    # 通知開始生成
                    await websocket.send_json({
                        "type": "file_start",
                        "file": file_path
                    })

                    progress = 10 + int((i / total_files) * 80)
                    await websocket.send_json({
                        "type": "progress",
                        "percent": progress,
                        "message": f"Generating {file_path}..."
                    })

                    # 串流生成檔案
                    content = ""
                    for chunk in coder.generate_file(
                        goal=goal,
                        file_path=file_path,
                        file_description=file_desc,
                        existing_files=existing_files
                    ):
                        content += chunk
                        await websocket.send_json({
                            "type": "file_chunk",
                            "file": file_path,
                            "chunk": chunk
                        })

                    # 儲存檔案
                    await sandbox.write_file(project_name, file_path, content)
                    existing_files[file_path] = content

                    await websocket.send_json({
                        "type": "file_complete",
                        "file": file_path,
                        "content": content
                    })

                # 完成
                await websocket.send_json({
                    "type": "progress",
                    "percent": 100,
                    "message": "Complete!"
                })

                await websocket.send_json({
                    "type": "complete",
                    "project_name": project_name
                })

                # 預覽 URL
                await websocket.send_json({
                    "type": "preview_ready",
                    "url": f"/sandbox/{project_name}/index.html"
                })

            elif msg_type == "chat":
                # 對話 / 修改請求
                message = data.get("message", "")

                if not message:
                    continue

                # 判斷是修改檔案還是一般對話
                if project_name and any(kw in message for kw in ["改", "加", "修", "刪", "換", "update", "add", "modify", "change"]):
                    # 修改現有檔案
                    # 找出要修改的檔案（簡單邏輯：找最相關的）
                    files_result = await sandbox.list_files(project_name)
                    files = files_result.get("files", [])

                    # 預設修改主要檔案
                    target_file = None
                    for f in files:
                        if f.get("type") == "file":
                            path = f.get("path", "")
                            if "script" in path or "app" in path or path.endswith(".js") or path.endswith(".jsx"):
                                target_file = path
                                break
                            if path == "index.html":
                                target_file = path

                    if target_file:
                        read_result = await sandbox.read_file(project_name, target_file)
                        current_content = read_result.get("content", "")

                        await websocket.send_json({
                            "type": "file_start",
                            "file": target_file
                        })

                        # 修改檔案
                        new_content = ""
                        for chunk in coder.modify_file(
                            goal=goal,
                            file_path=target_file,
                            current_content=current_content,
                            modification_request=message
                        ):
                            new_content += chunk
                            await websocket.send_json({
                                "type": "file_chunk",
                                "file": target_file,
                                "chunk": chunk
                            })

                        await sandbox.write_file(project_name, target_file, new_content)

                        await websocket.send_json({
                            "type": "file_complete",
                            "file": target_file,
                            "content": new_content
                        })

                        await websocket.send_json({
                            "type": "chat",
                            "message": f"Done! Updated `{target_file}`"
                        })
                    else:
                        await websocket.send_json({
                            "type": "chat",
                            "message": "No file to modify. Try being more specific."
                        })

                else:
                    # 一般對話
                    response = ""
                    for chunk in coder.chat(message, {"project": project_name, "goal": goal}):
                        response += chunk

                    await websocket.send_json({
                        "type": "chat",
                        "message": response
                    })

            elif msg_type == "save":
                # 儲存檔案（從編輯器手動儲存）
                file_path = data.get("file", "")
                content = data.get("content", "")

                if project_name and file_path:
                    await sandbox.write_file(project_name, file_path, content)
                    await websocket.send_json({
                        "type": "terminal",
                        "output": f"Saved: {file_path}"
                    })

    except WebSocketDisconnect:
        print("[Code] WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


# Sandbox 靜態檔案（預覽用）
sandbox_path = Path(__file__).parent.parent / "sandbox_workspace"
sandbox_path.mkdir(parents=True, exist_ok=True)
app.mount("/sandbox", StaticFiles(directory=str(sandbox_path), html=True), name="sandbox")


# 靜態前端檔案
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
