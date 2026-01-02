# Monus v4 - Node.js Edition 完整規格書

## 1. 專案概述

### 1.1 目標
將 Monus 從 Python 架構遷移到 Node.js/TypeScript，整合自有套件 `@modern-fs/core` 和 `@modern-ffi/core`，打造統一的全端 JavaScript 研究與程式碼生成代理系統。

### 1.2 核心價值
- **統一技術棧**: 前後端皆為 TypeScript
- **自有套件整合**: 使用 modern-fs 和 modern-ffi
- **更好的生態支援**: 原生支援 npm/Vite/React 專案生成
- **解決 Python 相容性問題**: 避免 Python 3.13 + Windows + Playwright 的 asyncio 問題

---

## 2. 系統架構

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        Monus v4 (Node.js)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Web UI    │  │    CLI      │  │   VS Code   │  Interfaces │
│  │  (Browser)  │  │  (Terminal) │  │  Extension  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Hono Server (HTTP/WS)                  │ │
│  │                    Port: 8088                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Planner   │  │   Coder     │  │  Reasoner   │   Agents    │
│  │  (分類+規劃) │  │  (程式生成)  │  │  (推理分析)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Evaluator  │  │  Verifier   │  │  Renderer   │             │
│  │  (評估品質)  │  │  (驗證結果)  │  │  (輸出渲染)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Browser    │  │   Sandbox   │  │    LLM      │    Tools    │
│  │ (Playwright)│  │(modern-fs)  │  │  (OpenAI)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 目錄結構

```
monus/
├── package.json              # 主專案配置 (workspace root)
├── pnpm-workspace.yaml       # pnpm workspace 配置
├── tsconfig.json             # TypeScript 根配置
├── .env                      # 環境變數 (API keys)
│
├── packages/
│   ├── core/                 # 核心邏輯
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── agents/
│   │       │   ├── index.ts
│   │       │   ├── planner.ts
│   │       │   ├── coder.ts
│   │       │   ├── reasoner.ts
│   │       │   ├── evaluator.ts
│   │       │   ├── verifier.ts
│   │       │   └── renderer.ts
│   │       ├── tools/
│   │       │   ├── index.ts
│   │       │   ├── browser.ts
│   │       │   ├── sandbox.ts
│   │       │   └── llm.ts
│   │       ├── loop/
│   │       │   ├── index.ts
│   │       │   ├── agent-loop.ts
│   │       │   └── memory.ts
│   │       └── types/
│   │           └── index.ts
│   │
│   ├── server/               # Web 伺服器
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── routes/
│   │       │   ├── api.ts
│   │       │   └── websocket.ts
│   │       └── middleware/
│   │           └── cors.ts
│   │
│   ├── web/                  # 前端 UI
│   │   ├── package.json
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── main.ts
│   │       ├── App.tsx
│   │       ├── components/
│   │       │   ├── InputSection.tsx
│   │       │   ├── ProgressSection.tsx
│   │       │   ├── HistoryPanel.tsx
│   │       │   └── ResultModal.tsx
│   │       ├── hooks/
│   │       │   └── useWebSocket.ts
│   │       └── styles/
│   │           └── global.css
│   │
│   └── cli/                  # CLI 工具 (可選)
│       ├── package.json
│       └── src/
│           └── index.ts
│
├── sandbox_workspace/        # 生成的專案目錄
├── runs/                     # 研究結果儲存
└── docs/                     # 文件
```

---

## 3. 技術規格

### 3.1 技術棧

| 層級 | 技術選擇 | 說明 |
|-----|---------|-----|
| Runtime | Node.js 20+ | LTS 版本，穩定性佳 |
| Language | TypeScript 5.x | 完整型別支援 |
| Package Manager | pnpm | Workspace 支援，效能佳 |
| Server | Hono | 輕量、快速、支援 Edge |
| WebSocket | Hono/ws | 內建 WebSocket 支援 |
| Browser | Playwright | 網頁爬蟲/截圖 |
| LLM Client | OpenAI SDK | DeepSeek 相容 |
| File System | @modern-fs/core | 自有套件 |
| FFI (未來) | @modern-ffi/core | 自有套件 |
| Frontend | React 18 + Vite | 現代前端架構 |
| Styling | Tailwind CSS | 快速開發 |

### 3.2 依賴套件

```json
{
  "dependencies": {
    "@modern-fs/core": "^1.0.0",
    "@modern-ffi/core": "^1.0.0",
    "hono": "^4.0.0",
    "openai": "^4.0.0",
    "playwright": "^1.40.0",
    "zod": "^3.22.0",
    "nanoid": "^5.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "tsx": "^4.0.0",
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0"
  }
}
```

---

## 4. 核心模組規格

### 4.1 Agents

#### 4.1.1 Planner Agent

```typescript
// packages/core/src/agents/planner.ts

interface TaskClassification {
  type: 'research' | 'code';
  template?: 'html' | 'vite-react' | 'vite-vue' | 'node' | 'python';
  confidence: number;
  reason: string;
}

interface PlanStep {
  id: string;
  title: string;
  tool: string;
  input: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

class Planner {
  constructor(options: { model: string; apiKey: string });

  // 分類任務類型
  classifyTask(goal: string): Promise<TaskClassification>;

  // 建立執行計畫
  createPlan(goal: string): Promise<PlanStep[]>;

  // 決定下一步
  decide(state: TaskState): Promise<Action | null>;

  // 生成報告
  generateReport(goal: string, sources: Source[], contents: string[]): Promise<string>;
}
```

#### 4.1.2 Coder Agent

```typescript
// packages/core/src/agents/coder.ts

interface ProjectPlan {
  projectName: string;
  description: string;
  files: Array<{ path: string; description: string }>;
  steps: Array<{ step: number; action: string; file: string }>;
}

class Coder {
  constructor(options: { model: string; apiKey: string });

  // 分析任務，生成專案計畫
  analyzeTask(goal: string, template: string): Promise<ProjectPlan>;

  // 生成檔案 (串流)
  generateFile(options: {
    goal: string;
    filePath: string;
    description: string;
    existingFiles?: Record<string, string>;
  }): AsyncGenerator<string>;

  // 修改檔案 (串流)
  modifyFile(options: {
    filePath: string;
    currentContent: string;
    request: string;
  }): AsyncGenerator<string>;

  // 修復錯誤 (串流)
  fixError(options: {
    filePath: string;
    content: string;
    error: string;
  }): AsyncGenerator<string>;
}
```

#### 4.1.3 Reasoner Agent

```typescript
// packages/core/src/agents/reasoner.ts

interface ReasoningResult {
  analysis: string;
  keyPoints: string[];
  suggestions: string[];
  confidence: number;
}

class Reasoner {
  constructor(options: { model: string; apiKey: string });

  // 分析內容
  analyze(content: string, context?: string): Promise<ReasoningResult>;

  // 摘要內容
  summarize(contents: string[]): Promise<string>;

  // 提取關鍵資訊
  extractKeyInfo(content: string, schema: z.ZodSchema): Promise<unknown>;
}
```

#### 4.1.4 Evaluator Agent

```typescript
// packages/core/src/agents/evaluator.ts

interface EvaluationResult {
  score: number;           // 0-100
  completeness: number;    // 完整度
  accuracy: number;        // 準確度
  relevance: number;       // 相關度
  issues: string[];
  suggestions: string[];
}

class Evaluator {
  constructor(options: { model: string; apiKey: string });

  // 評估報告品質
  evaluate(goal: string, report: string): Promise<EvaluationResult>;

  // 比較多個來源
  compareSources(sources: Source[]): Promise<ComparisonResult>;
}
```

#### 4.1.5 Verifier Agent

```typescript
// packages/core/src/agents/verifier.ts

interface VerificationResult {
  isComplete: boolean;
  checks: {
    minSources: boolean;
    minWordCount: boolean;
    hasConclusion: boolean;
    citationsValid: boolean;
  };
  missing: string[];
  score: number;
}

class Verifier {
  constructor(options: {
    minSources: number;
    minWordCount: number;
  });

  // 驗證報告
  verify(report: string, sources: Source[]): VerificationResult;

  // 驗證程式碼
  verifyCode(files: Record<string, string>): Promise<CodeVerificationResult>;
}
```

#### 4.1.6 Renderer Agent

```typescript
// packages/core/src/agents/renderer.ts

type OutputFormat = 'web' | 'pdf' | 'slides' | 'markdown';
type Theme = 'default' | 'dark' | 'pro' | 'ocean' | 'forest';

interface RenderResult {
  format: OutputFormat;
  path: string;
  url?: string;
}

class Renderer {
  constructor(options: { outputDir: string });

  // 渲染報告
  render(options: {
    content: string;
    format: OutputFormat;
    theme: Theme;
    runId: string;
  }): Promise<RenderResult>;

  // 選擇最佳佈局
  selectLayout(contentType: string, goal: string): LayoutConfig;
}
```

### 4.2 Tools

#### 4.2.1 Browser Tool (Playwright)

```typescript
// packages/core/src/tools/browser.ts

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

interface PageContent {
  url: string;
  title: string;
  content: string;
  links: string[];
}

class BrowserTool {
  private browser: Browser | null = null;

  // 初始化
  async init(): Promise<void>;

  // 關閉
  async close(): Promise<void>;

  // 搜尋
  async search(query: string): Promise<SearchResult[]>;

  // 開啟頁面
  async openPage(url: string): Promise<PageContent>;

  // 截圖
  async screenshot(url: string): Promise<Buffer>;

  // 提取內容
  async extractContent(url: string): Promise<string>;
}
```

#### 4.2.2 Sandbox Tool (modern-fs)

```typescript
// packages/core/src/tools/sandbox.ts

import { mkdirp, rimraf, copy, writeFile, readFile } from '@modern-fs/core';

type ProjectTemplate = 'html' | 'vite-react' | 'vite-vue' | 'node' | 'python';

interface ProjectInfo {
  name: string;
  path: string;
  files: FileInfo[];
}

interface FileInfo {
  path: string;
  type: 'file' | 'directory';
  size?: number;
}

class SandboxTool {
  private workspaceDir: string;

  constructor(workspaceDir?: string);

  // 初始化專案
  async initProject(name: string, template: ProjectTemplate): Promise<ProjectInfo>;

  // 寫入檔案
  async writeFile(projectName: string, filePath: string, content: string): Promise<void>;

  // 讀取檔案
  async readFile(projectName: string, filePath: string): Promise<string>;

  // 刪除檔案
  async deleteFile(projectName: string, filePath: string): Promise<void>;

  // 列出檔案
  async listFiles(projectName: string): Promise<FileInfo[]>;

  // 執行命令
  async runCommand(projectName: string, command: string): Promise<CommandResult>;

  // 安裝依賴
  async installDeps(projectName: string): Promise<void>;

  // 啟動開發伺服器
  async startDevServer(projectName: string, port: number): Promise<DevServerInfo>;

  // 清理專案
  async cleanup(projectName: string): Promise<void>;
}
```

#### 4.2.3 LLM Tool

```typescript
// packages/core/src/tools/llm.ts

import OpenAI from 'openai';

interface LLMOptions {
  model: string;
  apiKey: string;
  baseURL?: string;
  temperature?: number;
  maxTokens?: number;
}

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

class LLMClient {
  private client: OpenAI;
  private model: string;

  constructor(options: LLMOptions);

  // 單次對話
  async chat(messages: Message[]): Promise<string>;

  // 串流對話
  async *chatStream(messages: Message[]): AsyncGenerator<string>;

  // JSON 模式
  async chatJSON<T>(messages: Message[], schema: z.ZodSchema<T>): Promise<T>;
}
```

### 4.3 Agent Loop

```typescript
// packages/core/src/loop/agent-loop.ts

interface AgentLoopOptions {
  planner: Planner;
  coder: Coder;
  reasoner: Reasoner;
  evaluator: Evaluator;
  verifier: Verifier;
  renderer: Renderer;
  browser: BrowserTool;
  sandbox: SandboxTool;
  maxIterations: number;
}

interface RunResult {
  success: boolean;
  runId: string;
  mode: 'research' | 'code';
  outputs: Record<string, string>;
  error?: string;
}

type EventType =
  | 'start'
  | 'classification'
  | 'phase'
  | 'progress'
  | 'step'
  | 'action'
  | 'file_start'
  | 'file_chunk'
  | 'file_complete'
  | 'complete'
  | 'error';

interface AgentEvent {
  type: EventType;
  data: unknown;
}

class AgentLoop {
  constructor(options: AgentLoopOptions);

  // 執行任務 (事件驅動)
  async *run(goal: string, options: RunOptions): AsyncGenerator<AgentEvent, RunResult>;

  // 研究模式
  private async *runResearch(goal: string): AsyncGenerator<AgentEvent>;

  // 程式碼生成模式
  private async *runCodeGeneration(goal: string, template: string): AsyncGenerator<AgentEvent>;
}
```

### 4.4 Memory

```typescript
// packages/core/src/loop/memory.ts

interface Source {
  url: string;
  title: string;
  content: string;
  timestamp: Date;
}

interface RunRecord {
  id: string;
  goal: string;
  mode: 'research' | 'code';
  status: 'running' | 'completed' | 'failed';
  sources: Source[];
  outputs: Record<string, string>;
  createdAt: Date;
  completedAt?: Date;
}

class Memory {
  private runsDir: string;

  constructor(runsDir: string);

  // 建立新執行記錄
  createRun(goal: string, mode: 'research' | 'code'): RunRecord;

  // 更新執行記錄
  updateRun(id: string, updates: Partial<RunRecord>): void;

  // 加入來源
  addSource(runId: string, source: Source): void;

  // 儲存輸出
  saveOutput(runId: string, filename: string, content: string): Promise<string>;

  // 讀取執行記錄
  getRun(id: string): RunRecord | null;

  // 列出所有執行記錄
  listRuns(limit?: number): RunRecord[];
}
```

---

## 5. Server API 規格

### 5.1 HTTP API

#### GET /api/health
```json
{ "status": "ok", "version": "4.0.0" }
```

#### GET /api/runs
列出執行記錄
```json
{
  "runs": [
    {
      "id": "20250102_143000",
      "goal": "Python asyncio 教學",
      "mode": "research",
      "status": "completed",
      "outputs": {
        "web": "/runs/20250102_143000/index.html",
        "pdf": "/runs/20250102_143000/report.pdf"
      },
      "createdAt": "2025-01-02T14:30:00Z"
    }
  ]
}
```

#### GET /api/runs/:id
取得特定執行記錄詳情

#### POST /api/tasks
建立新任務
```json
// Request
{
  "goal": "做一個貪吃蛇遊戲",
  "outputFormat": "web",
  "theme": "default"
}

// Response
{
  "taskId": "1735812345678",
  "status": "pending"
}
```

### 5.2 WebSocket API

#### 連接: ws://localhost:8088/ws/:taskId

#### Client → Server 訊息
```typescript
// 啟動任務
{
  type: 'start',
  goal: string,
  outputFormat: 'web' | 'pdf' | 'slides' | 'all',
  theme: string
}

// 對話 (Code 模式)
{
  type: 'chat',
  message: string
}

// 儲存檔案
{
  type: 'save',
  file: string,
  content: string
}
```

#### Server → Client 訊息
```typescript
// 任務分類
{
  type: 'classification',
  taskType: 'research' | 'code',
  template?: string,
  confidence: number,
  reason: string
}

// 階段更新
{
  type: 'phase',
  phase: 'planning' | 'searching' | 'analyzing' | 'writing' | 'rendering'
}

// 進度更新
{
  type: 'progress',
  progress: number  // 0-100
}

// 步驟更新
{
  type: 'step',
  step: string,
  status: 'running' | 'done' | 'error'
}

// 檔案生成開始
{
  type: 'file_start',
  file: string
}

// 檔案內容串流
{
  type: 'file_chunk',
  file: string,
  chunk: string
}

// 檔案生成完成
{
  type: 'file_complete',
  file: string,
  content: string
}

// 任務完成
{
  type: 'done',
  mode: 'research' | 'code',
  result: {
    success: boolean,
    runId?: string,
    projectName?: string,
    outputs?: Record<string, string>
  }
}

// 錯誤
{
  type: 'error',
  message: string
}
```

---

## 6. 前端 UI 規格

### 6.1 元件結構

```
App
├── Header
│   ├── Logo
│   └── NavLinks
├── Main
│   ├── InputSection
│   │   ├── GoalTextarea
│   │   ├── TaskTypeHint
│   │   ├── OptionsPanel
│   │   │   ├── FormatSelect
│   │   │   └── ThemeSelect
│   │   ├── SubmitButton
│   │   └── AgentBadges
│   ├── ProgressSection
│   │   ├── ProgressBar
│   │   ├── PhaseIndicator
│   │   └── LogArea
│   └── HistoryPanel
│       └── HistoryList
└── ResultModal
    ├── ModalHeader
    ├── ModalTabs
    └── ModalContent
        ├── PreviewFrame (iframe)
        └── MarkdownContent
```

### 6.2 狀態管理

```typescript
interface AppState {
  // 任務狀態
  currentTaskId: string | null;
  currentMode: 'research' | 'code' | null;
  isRunning: boolean;

  // 進度
  progress: number;
  phase: string;
  logs: LogEntry[];

  // 結果
  result: RunResult | null;

  // 歷史
  history: RunRecord[];

  // WebSocket
  ws: WebSocket | null;
}

interface LogEntry {
  type: 'info' | 'action' | 'success' | 'error';
  message: string;
  timestamp: Date;
}
```

### 6.3 WebSocket Hook

```typescript
// packages/web/src/hooks/useWebSocket.ts

function useWebSocket(taskId: string) {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [messages, setMessages] = useState<AgentEvent[]>([]);

  const connect = useCallback(() => { ... });
  const send = useCallback((data: object) => { ... });
  const disconnect = useCallback(() => { ... });

  return { status, messages, connect, send, disconnect };
}
```

---

## 7. 專案模板規格

### 7.1 HTML 模板

```
project_name/
├── index.html
├── style.css
└── script.js
```

### 7.2 Vite + React 模板

```
project_name/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── public/
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── App.css
    └── vite-env.d.ts
```

### 7.3 Vite + Vue 模板

```
project_name/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.ts
    ├── App.vue
    └── vite-env.d.ts
```

### 7.4 Node.js 模板

```
project_name/
├── package.json
├── tsconfig.json
└── src/
    └── index.ts
```

---

## 8. 開發計畫

### Phase 1: 核心基礎 (Week 1)
- [ ] 建立 pnpm workspace 結構
- [ ] 設定 TypeScript 配置
- [ ] 實作 LLM Client
- [ ] 實作 Sandbox Tool (整合 modern-fs)

### Phase 2: Agents (Week 2)
- [ ] 實作 Planner Agent
- [ ] 實作 Coder Agent
- [ ] 實作 Reasoner Agent
- [ ] 實作 Evaluator + Verifier

### Phase 3: Server + Loop (Week 3)
- [ ] 實作 Hono Server
- [ ] 實作 WebSocket 處理
- [ ] 實作 Agent Loop
- [ ] 實作 Memory 管理

### Phase 4: Browser + Renderer (Week 4)
- [ ] 實作 Browser Tool (Playwright)
- [ ] 實作 Renderer Agent
- [ ] PDF 生成整合
- [ ] Slides 生成整合

### Phase 5: Frontend (Week 5)
- [ ] 建立 Vite + React 專案
- [ ] 實作 UI 元件
- [ ] WebSocket 整合
- [ ] 測試與優化

### Phase 6: 整合測試 (Week 6)
- [ ] 端對端測試
- [ ] 效能優化
- [ ] 文件撰寫
- [ ] 發布準備

---

## 9. 測試策略

### 9.1 單元測試

```typescript
// 使用 Vitest
import { describe, it, expect } from 'vitest';
import { Planner } from '../src/agents/planner';

describe('Planner', () => {
  it('should classify code tasks correctly', async () => {
    const planner = new Planner({ model: 'test', apiKey: 'test' });
    const result = await planner.classifyTask('做一個貪吃蛇遊戲');
    expect(result.type).toBe('code');
  });

  it('should classify research tasks correctly', async () => {
    const planner = new Planner({ model: 'test', apiKey: 'test' });
    const result = await planner.classifyTask('Python asyncio 教學');
    expect(result.type).toBe('research');
  });
});
```

### 9.2 整合測試

```typescript
describe('AgentLoop', () => {
  it('should complete a research task', async () => {
    const loop = createAgentLoop();
    const events: AgentEvent[] = [];

    for await (const event of loop.run('什麼是 GraphQL')) {
      events.push(event);
    }

    expect(events.some(e => e.type === 'complete')).toBe(true);
  });
});
```

---

## 10. 部署規格

### 10.1 環境變數

```bash
# .env
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx  # 可選
PORT=8088
NODE_ENV=production
```

### 10.2 Docker

```dockerfile
FROM node:20-alpine

WORKDIR /app

# 安裝 pnpm
RUN npm install -g pnpm

# 複製依賴配置
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/*/package.json ./packages/

# 安裝依賴
RUN pnpm install --frozen-lockfile

# 複製原始碼
COPY . .

# 建置
RUN pnpm build

# 安裝 Playwright
RUN pnpm exec playwright install chromium

EXPOSE 8088

CMD ["pnpm", "start"]
```

### 10.3 npm scripts

```json
{
  "scripts": {
    "dev": "pnpm -r --parallel dev",
    "build": "pnpm -r build",
    "start": "node packages/server/dist/index.js",
    "test": "vitest",
    "lint": "eslint packages/*/src/**/*.ts"
  }
}
```

---

## 11. 未來擴展

### 11.1 modern-ffi 整合
- 呼叫原生編譯器 (gcc, rustc)
- 系統 API 整合
- 效能關鍵路徑優化

### 11.2 更多 Agents
- Code Review Agent
- Test Generator Agent
- Documentation Agent

### 11.3 更多模板
- Next.js
- Nuxt.js
- Electron
- React Native

### 11.4 多 LLM 支援
- Claude
- GPT-4
- Gemini
- 本地 LLM (Ollama)

---

## 附錄 A: 從 Python 遷移對照表

| Python | Node.js/TypeScript |
|--------|-------------------|
| FastAPI | Hono |
| asyncio | async/await (native) |
| Playwright (Python) | Playwright (Node.js) |
| pathlib | @modern-fs/core |
| subprocess | child_process / execa |
| OpenAI Python SDK | OpenAI Node SDK |
| Pydantic | Zod |
| uvicorn | Node.js native |

---

## 附錄 B: 效能目標

| 指標 | 目標 |
|-----|------|
| 冷啟動時間 | < 2 秒 |
| WebSocket 連接時間 | < 100ms |
| 任務分類延遲 | < 500ms |
| 檔案寫入 (modern-fs) | < 10ms |
| 記憶體使用 | < 200MB (idle) |

---

*文件版本: 1.0.0*
*最後更新: 2025-01-02*
