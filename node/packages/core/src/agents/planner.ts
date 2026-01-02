/**
 * Planner Agent - Task classification and planning
 */

import { LLMClient } from '../tools/llm.js';
import type {
  TaskClassification,
  PlanStep,
  ProjectTemplate,
  Message,
  LLMOptions,
} from '../types/index.js';
import { nanoid } from 'nanoid';

export interface PlannerOptions extends LLMOptions {}

export class Planner {
  private llm: LLMClient;

  constructor(options: PlannerOptions) {
    this.llm = new LLMClient(options);
  }

  /**
   * Classify task type: research or code
   */
  async classifyTask(goal: string): Promise<TaskClassification> {
    // Code-related keywords
    const codeKeywords = [
      '做一個',
      '寫一個',
      '開發',
      '實作',
      '建立',
      '創建',
      '遊戲',
      '網站',
      'app',
      '應用',
      '程式',
      '功能',
      'make',
      'build',
      'create',
      'develop',
      'implement',
      'game',
      'website',
      'application',
      'program',
    ];

    // Research-related keywords
    const researchKeywords = [
      '研究',
      '分析',
      '比較',
      '什麼是',
      '介紹',
      '說明',
      '教學',
      '原理',
      '報告',
      '彙整',
      '推薦',
      '整理',
      'research',
      'analyze',
      'compare',
      'explain',
      'tutorial',
      'overview',
      'how does',
      'what is',
    ];

    const goalLower = goal.toLowerCase();

    // Calculate match scores
    const codeScore = codeKeywords.filter((kw) => goalLower.includes(kw.toLowerCase())).length;
    const researchScore = researchKeywords.filter((kw) => goalLower.includes(kw.toLowerCase())).length;

    // Determine template
    let template: ProjectTemplate | undefined;
    if (codeScore > researchScore) {
      if (['react', '元件', 'component'].some((kw) => goalLower.includes(kw))) {
        template = 'vite-react';
      } else if (['vue'].some((kw) => goalLower.includes(kw))) {
        template = 'vite-vue';
      } else if (['python', '爬蟲', '腳本', 'script'].some((kw) => goalLower.includes(kw))) {
        template = 'python';
      } else if (['node', '後端', 'api', 'server'].some((kw) => goalLower.includes(kw))) {
        template = 'node';
      } else {
        template = 'html';
      }
    }

    // Use LLM if no keywords match
    if (codeScore === 0 && researchScore === 0) {
      return await this.llmClassifyTask(goal);
    }

    if (codeScore > researchScore) {
      return {
        type: 'code',
        template,
        confidence: Math.min(1.0, codeScore / 3),
        reason: `Detected code-related keywords (score: ${codeScore} vs ${researchScore})`,
      };
    } else {
      return {
        type: 'research',
        template: undefined,
        confidence: Math.min(1.0, researchScore / 3),
        reason: `Detected research-related keywords (score: ${researchScore} vs ${codeScore})`,
      };
    }
  }

  /**
   * LLM-based task classification
   */
  private async llmClassifyTask(goal: string): Promise<TaskClassification> {
    const prompt = `分析以下用戶需求，判斷是「研究型任務」還是「程式開發任務」。

用戶需求: ${goal}

判斷標準:
- 研究型(research): 需要搜尋資料、整理報告、比較分析、教學說明
- 程式開發(code): 需要寫程式碼、做應用、做遊戲、建網站

回覆 JSON 格式（不要 markdown）:
{"type": "research 或 code", "template": "html/vite-react/vite-vue/node/python 或 null", "reason": "判斷理由"}`;

    try {
      const result = await this.llm.chatJSON<{
        type: 'research' | 'code';
        template: ProjectTemplate | null;
        reason: string;
      }>([{ role: 'user', content: prompt }]);

      return {
        type: result.type,
        template: result.template ?? undefined,
        confidence: 0.7,
        reason: result.reason,
      };
    } catch {
      return {
        type: 'research',
        template: undefined,
        confidence: 0.5,
        reason: 'Default to research (LLM classification failed)',
      };
    }
  }

  /**
   * Create initial research plan
   */
  async createPlan(goal: string): Promise<PlanStep[]> {
    const prompt = `你是一個研究助理 AI。用戶給你一個研究目標，你需要規劃執行步驟。

目標: ${goal}

可用的工具:
- browser.search: 搜尋網路資料（輸入搜尋關鍵字）
- browser.open: 開啟特定網頁（輸入 URL）
- browser.extract: 提取當前頁面內容
- fs.write: 寫入檔案
- code.run: 執行命令

請規劃 3-5 個步驟來完成這個研究任務。
每個步驟格式:
- title: 步驟標題
- tool: 使用的工具
- input: 工具輸入

回覆純 JSON 格式（不要 markdown）:
[
  {"title": "步驟1標題", "tool": "browser.search", "input": "搜尋關鍵字"},
  ...
]`;

    try {
      const steps = await this.llm.chatJSON<Array<{ title: string; tool: string; input: string }>>([
        { role: 'user', content: prompt },
      ]);

      return steps.map((step, index) => ({
        id: nanoid(8),
        title: step.title,
        tool: step.tool,
        input: step.input,
        status: 'pending' as const,
      }));
    } catch {
      // Fallback plan
      return [
        {
          id: nanoid(8),
          title: '搜尋相關資料',
          tool: 'browser.search',
          input: goal,
          status: 'pending',
        },
        {
          id: nanoid(8),
          title: '分析搜尋結果',
          tool: 'browser.extract',
          input: 'Extract main content',
          status: 'pending',
        },
        {
          id: nanoid(8),
          title: '生成報告',
          tool: 'generate_report',
          input: goal,
          status: 'pending',
        },
      ];
    }
  }

  /**
   * Analyze content type for report
   */
  async analyzeContentType(
    goal: string,
    contents: string[]
  ): Promise<'tutorial' | 'comparison' | 'report' | 'reference' | 'list' | 'overview'> {
    const preview = contents.slice(0, 3).join('\n').slice(0, 2000);

    const prompt = `分析以下研究目標和內容，判斷最適合的報告類型。

目標: ${goal}

內容預覽:
${preview}

可選類型:
- tutorial: 教學文章（有步驟、程式碼範例）
- comparison: 比較分析（對比多個選項）
- report: 研究報告（深度分析、學術風格）
- reference: 參考文件（API、技術規格）
- list: 列表彙整（推薦清單、排名）
- overview: 概述介紹（入門、基礎介紹）

只回覆類型 ID，不要其他文字。`;

    try {
      const result = await this.llm.chat([{ role: 'user', content: prompt }]);
      const type = result.toLowerCase().trim();

      const validTypes = ['tutorial', 'comparison', 'report', 'reference', 'list', 'overview'];
      if (validTypes.includes(type)) {
        return type as any;
      }
    } catch {
      // Fallback
    }

    // Keyword-based fallback
    const goalLower = goal.toLowerCase();

    if (['教學', '教程', 'how to', '步驟', 'tutorial'].some((k) => goalLower.includes(k))) {
      return 'tutorial';
    } else if (['比較', '對比', 'vs', '差異'].some((k) => goalLower.includes(k))) {
      return 'comparison';
    } else if (['api', '參考', 'reference', '文件'].some((k) => goalLower.includes(k))) {
      return 'reference';
    } else if (['推薦', '列表', 'top', '最佳'].some((k) => goalLower.includes(k))) {
      return 'list';
    } else if (['什麼是', '介紹', '概述', '入門'].some((k) => goalLower.includes(k))) {
      return 'overview';
    }

    return 'report';
  }

  /**
   * Generate research report
   */
  async generateReport(
    goal: string,
    sources: Array<{ title: string; url: string }>,
    contents: string[],
    contentType?: string
  ): Promise<string> {
    // Auto-detect content type if not provided
    if (!contentType) {
      contentType = await this.analyzeContentType(goal, contents);
    }

    const sourcesText = sources.map((s) => `- ${s.title}: ${s.url}`).join('\n');
    const contentsText = contents.slice(0, 5).join('\n\n---\n\n').slice(0, 8000);

    const prompt = `目標: ${goal}
內容類型: ${contentType}

收集的來源:
${sourcesText}

內容摘要:
${contentsText}

請根據以上資料撰寫一份${this.getTypeDescription(contentType)}。

撰寫要求:
1. 使用繁體中文
2. 報告需超過 1000 字
3. 內容要有深度，不要泛泛而談
4. 適當使用 Markdown 格式（標題、列表、程式碼區塊、表格等）
5. 如果是教學類，要有清晰的步驟和程式碼範例
6. 如果是比較類，要有表格對比
7. 引用來源時標註出處`;

    return await this.llm.chat([{ role: 'user', content: prompt }]);
  }

  private getTypeDescription(contentType: string): string {
    const descriptions: Record<string, string> = {
      tutorial: '實用教學文章',
      comparison: '深度比較分析報告',
      report: '研究報告',
      reference: '技術參考文件',
      list: '精選列表',
      overview: '概述介紹文章',
    };

    return descriptions[contentType] ?? '研究報告';
  }
}
