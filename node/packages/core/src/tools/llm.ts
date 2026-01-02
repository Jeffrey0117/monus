/**
 * LLM Client - OpenAI/DeepSeek compatible
 */

import OpenAI from 'openai';
import type { Message, LLMOptions } from '../types/index.js';

export class LLMClient {
  private client: OpenAI;
  private model: string;
  private temperature: number;
  private maxTokens: number;

  constructor(options: LLMOptions) {
    this.model = options.model;
    this.temperature = options.temperature ?? 0.7;
    this.maxTokens = options.maxTokens ?? 4096;

    this.client = new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL ?? 'https://api.deepseek.com/v1',
    });
  }

  /**
   * Single chat completion
   */
  async chat(messages: Message[]): Promise<string> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
      temperature: this.temperature,
      max_tokens: this.maxTokens,
    });

    return response.choices[0]?.message?.content ?? '';
  }

  /**
   * Streaming chat completion
   */
  async *chatStream(messages: Message[]): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        yield content;
      }
    }
  }

  /**
   * Chat with JSON response parsing
   */
  async chatJSON<T>(messages: Message[]): Promise<T> {
    const response = await this.chat(messages);

    // Try to extract JSON from response
    let jsonStr = response;

    // Handle markdown code blocks
    if (response.includes('```json')) {
      jsonStr = response.split('```json')[1]?.split('```')[0] ?? response;
    } else if (response.includes('```')) {
      jsonStr = response.split('```')[1]?.split('```')[0] ?? response;
    }

    return JSON.parse(jsonStr.trim()) as T;
  }
}

/**
 * Create a DeepSeek client
 */
export function createDeepSeekClient(apiKey: string): LLMClient {
  return new LLMClient({
    model: 'deepseek-chat',
    apiKey,
    baseURL: 'https://api.deepseek.com/v1',
  });
}

/**
 * Create an OpenAI client
 */
export function createOpenAIClient(apiKey: string, model = 'gpt-4o'): LLMClient {
  return new LLMClient({
    model,
    apiKey,
    baseURL: 'https://api.openai.com/v1',
  });
}
