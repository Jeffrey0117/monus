/**
 * Monus Core Types
 */

// Task Classification
export type TaskType = 'research' | 'code';

export type ProjectTemplate = 'html' | 'vite-react' | 'vite-vue' | 'node' | 'python';

export interface TaskClassification {
  type: TaskType;
  template?: ProjectTemplate;
  confidence: number;
  reason: string;
}

// Plan & Steps
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface PlanStep {
  id: string;
  title: string;
  tool: string;
  input: string;
  status: StepStatus;
}

// Project
export interface ProjectPlan {
  projectName: string;
  description: string;
  files: FileSpec[];
  steps: ProjectStep[];
}

export interface FileSpec {
  path: string;
  description: string;
}

export interface ProjectStep {
  step: number;
  action: string;
  file: string;
  description: string;
}

// Sources
export interface Source {
  url: string;
  title: string;
  content: string;
  timestamp: Date;
}

// Search Results
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

// Page Content
export interface PageContent {
  url: string;
  title: string;
  content: string;
  links: string[];
}

// File Info
export interface FileInfo {
  path: string;
  type: 'file' | 'directory';
  size?: number;
}

// Run Record
export type RunStatus = 'running' | 'completed' | 'failed';

export interface RunRecord {
  id: string;
  goal: string;
  mode: TaskType;
  status: RunStatus;
  sources: Source[];
  outputs: Record<string, string>;
  createdAt: Date;
  completedAt?: Date;
}

// Agent Events
export type AgentEventType =
  | 'start'
  | 'classification'
  | 'phase'
  | 'progress'
  | 'step'
  | 'action'
  | 'sources'
  | 'file_start'
  | 'file_chunk'
  | 'file_complete'
  | 'complete'
  | 'error';

export interface AgentEvent {
  type: AgentEventType;
  data: unknown;
}

// Run Result
export interface RunResult {
  success: boolean;
  runId: string;
  mode: TaskType;
  outputs: Record<string, string>;
  error?: string;
}

// LLM
export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMOptions {
  model: string;
  apiKey: string;
  baseURL?: string;
  temperature?: number;
  maxTokens?: number;
}

// Output
export type OutputFormat = 'web' | 'pdf' | 'slides' | 'markdown';
export type Theme = 'default' | 'dark' | 'pro' | 'ocean' | 'forest';

export interface RenderOptions {
  content: string;
  format: OutputFormat;
  theme: Theme;
  runId: string;
}

export interface RenderResult {
  format: OutputFormat;
  path: string;
  url?: string;
}

// Evaluation
export interface EvaluationResult {
  score: number;
  completeness: number;
  accuracy: number;
  relevance: number;
  issues: string[];
  suggestions: string[];
}

// Verification
export interface VerificationResult {
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
