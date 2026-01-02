/**
 * Coder Agent - Code generation
 */

import { LLMClient } from '../tools/llm.js';
import type { ProjectPlan, FileSpec, ProjectTemplate, LLMOptions, Message } from '../types/index.js';

export interface CoderOptions extends LLMOptions {}

export class Coder {
  private llm: LLMClient;
  private conversationHistory: Message[] = [];

  constructor(options: CoderOptions) {
    this.llm = new LLMClient(options);
  }

  /**
   * Analyze task and generate project plan
   */
  async analyzeTask(goal: string, template: ProjectTemplate = 'html'): Promise<ProjectPlan> {
    const templateHints: Record<ProjectTemplate, string> = {
      html: '使用純 HTML + CSS + JavaScript，不需要建置工具',
      'vite-react': '使用 Vite + React，現代化前端架構',
      'vite-vue': '使用 Vite + Vue 3，現代化前端架構',
      node: '使用 Node.js',
      python: '使用 Python，可搭配 Flask 或純腳本',
    };

    const prompt = `你是一個專業的程式碼架構師。
分析使用者需求，規劃專案結構。

回傳 JSON 格式：
{
    "projectName": "專案名稱（英文，用底線分隔）",
    "description": "專案描述",
    "files": [
        {"path": "檔案路徑", "description": "檔案說明"}
    ],
    "steps": [
        {"step": 1, "action": "create_file", "file": "檔案路徑", "description": "說明"}
    ]
}

注意：
1. 專案名稱用英文小寫加底線
2. 列出所有需要建立的檔案
3. 步驟要按順序，從基礎結構開始

使用者需求：${goal}

專案模板：${template}
模板說明：${templateHints[template]}

請分析並規劃專案結構。回傳 JSON。`;

    try {
      const plan = await this.llm.chatJSON<{
        projectName: string;
        description: string;
        files: Array<{ path: string; description: string }>;
        steps: Array<{ step: number; action: string; file: string; description: string }>;
      }>([{ role: 'user', content: prompt }]);

      return {
        projectName: plan.projectName || 'monus_project',
        description: plan.description,
        files: plan.files,
        steps: plan.steps,
      };
    } catch {
      // Fallback plan for HTML template
      return {
        projectName: 'monus_project',
        description: goal,
        files: [
          { path: 'index.html', description: '主頁面' },
          { path: 'style.css', description: '樣式' },
          { path: 'script.js', description: '腳本' },
        ],
        steps: [
          { step: 1, action: 'create_file', file: 'index.html', description: '建立主頁面' },
          { step: 2, action: 'create_file', file: 'style.css', description: '建立樣式' },
          { step: 3, action: 'create_file', file: 'script.js', description: '建立腳本' },
        ],
      };
    }
  }

  /**
   * Generate file content (streaming)
   */
  async *generateFile(options: {
    goal: string;
    filePath: string;
    description: string;
    existingFiles?: Record<string, string>;
    context?: string;
  }): AsyncGenerator<string> {
    const systemPrompt = `你是一個專業的程式碼開發者。
根據需求生成完整、可運行的程式碼。

規則：
1. 只輸出程式碼，不要解釋
2. 程式碼要完整可運行
3. 加入適當的註解
4. 使用現代化的最佳實踐
5. 不要使用 markdown code block，直接輸出程式碼內容`;

    // Build existing files context
    let filesContext = '';
    if (options.existingFiles && Object.keys(options.existingFiles).length > 0) {
      filesContext = '\n\n已存在的檔案：\n';
      for (const [path, content] of Object.entries(options.existingFiles)) {
        const preview = content.length > 500 ? content.slice(0, 500) + '...' : content;
        filesContext += `\n--- ${path} ---\n${preview}\n`;
      }
    }

    const userPrompt = `專案目標：${options.goal}

現在需要生成：${options.filePath}
檔案說明：${options.description}
${filesContext}
${options.context || ''}

請生成完整的 ${options.filePath} 檔案內容。直接輸出程式碼，不要 markdown。`;

    const messages: Message[] = [
      { role: 'system', content: systemPrompt },
      ...this.conversationHistory.slice(-4),
      { role: 'user', content: userPrompt },
    ];

    let fullResponse = '';

    for await (const chunk of this.llm.chatStream(messages)) {
      fullResponse += chunk;
      yield chunk;
    }

    // Record conversation history
    this.conversationHistory.push({ role: 'user', content: userPrompt });
    this.conversationHistory.push({ role: 'assistant', content: fullResponse });
  }

  /**
   * Modify existing file (streaming)
   */
  async *modifyFile(options: {
    goal: string;
    filePath: string;
    currentContent: string;
    request: string;
  }): AsyncGenerator<string> {
    const systemPrompt = `你是一個專業的程式碼開發者。
根據要求修改程式碼。

規則：
1. 只輸出修改後的完整程式碼
2. 不要解釋
3. 保持原有的風格和結構
4. 不要使用 markdown code block`;

    const userPrompt = `專案目標：${options.goal}

檔案：${options.filePath}

目前內容：
${options.currentContent}

修改要求：${options.request}

請輸出修改後的完整檔案內容。`;

    const messages: Message[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ];

    for await (const chunk of this.llm.chatStream(messages)) {
      yield chunk;
    }
  }

  /**
   * Fix error in code (streaming)
   */
  async *fixError(options: {
    filePath: string;
    content: string;
    error: string;
  }): AsyncGenerator<string> {
    const systemPrompt = `你是一個專業的程式碼除錯專家。
分析錯誤並修復程式碼。

規則：
1. 分析錯誤原因
2. 輸出修復後的完整程式碼
3. 不要使用 markdown code block`;

    const userPrompt = `檔案：${options.filePath}

目前內容：
${options.content}

錯誤訊息：
${options.error}

請修復錯誤，輸出完整的修復後程式碼。`;

    const messages: Message[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ];

    for await (const chunk of this.llm.chatStream(messages)) {
      yield chunk;
    }
  }

  /**
   * Chat for clarification
   */
  async *chat(message: string, context?: { project?: string; goal?: string }): AsyncGenerator<string> {
    const systemPrompt = `你是一個友善的程式開發助手。
幫助使用者澄清需求、解答問題。
回答要簡潔明確。`;

    let contextStr = '';
    if (context) {
      contextStr = `\n\n專案上下文：\n${JSON.stringify(context, null, 2)}`;
    }

    const messages: Message[] = [
      { role: 'system', content: systemPrompt + contextStr },
      ...this.conversationHistory.slice(-6),
      { role: 'user', content: message },
    ];

    let fullResponse = '';

    for await (const chunk of this.llm.chatStream(messages)) {
      fullResponse += chunk;
      yield chunk;
    }

    this.conversationHistory.push({ role: 'user', content: message });
    this.conversationHistory.push({ role: 'assistant', content: fullResponse });
  }

  /**
   * Clear conversation history
   */
  clearHistory(): void {
    this.conversationHistory = [];
  }
}
