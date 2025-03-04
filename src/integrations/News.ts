import OpenAI from 'openai';
import { NewsArticle } from '../types';
import { encode } from 'gpt-3-encoder';
import { chunk } from 'lodash';
import { sleep } from '../utils/helpers';

export class NewsIntegration {
    private openai: OpenAI;
    private googleWorkspace: any;
    private maxTokensPerRequest = 4000;
    private retryDelay = 2000;
    private maxRetries = 3;

    constructor(apiKey: string, googleWorkspace: any) {
        this.openai = new OpenAI({ apiKey });
        this.googleWorkspace = googleWorkspace;
    }

    async getRelevantNews(): Promise<NewsArticle[]> {
        try {
            const docs = await this.googleWorkspace.listDocuments();
            return this.processBatchedDocs(this.optimizeDocuments(docs));
        } catch (error) {
            console.error('[News] Error:', error);
            return [];
        }
    }

    private optimizeDocuments(docs: any[]): any[] {
        return docs.map(doc => ({
            title: doc.title?.substring(0, 100),
            summary: doc.summary?.substring(0, 200)
        })).filter(doc => doc.title && doc.summary);
    }

    private async processBatchedDocs(docs: any[]) {
        const allTopics = [];
        const batches = this.createTokenSafeBatches(docs);

        for (const batch of batches) {
            try {
                const topics = await this.processWithRetry(() => this.extractTopicsFromDocs(batch));
                allTopics.push(...topics);
                await sleep(this.retryDelay);
            } catch {
                continue;
            }
        }

        return this.deduplicateTopics(allTopics);
    }

    private deduplicateTopics(topics: any[]): any[] {
        return [...new Set(topics)];
    }

    private createTokenSafeBatches(docs: any[]) {
        const batches = [];
        let currentBatch = [];
        let currentTokens = 0;

        for (const doc of docs) {
            const docTokens = encode(JSON.stringify(doc)).length;

            if (currentTokens + docTokens > this.maxTokensPerRequest) {
                batches.push(currentBatch);
                currentBatch = [doc];
                currentTokens = docTokens;
            } else {
                currentBatch.push(doc);
                currentTokens += docTokens;
            }
        }

        if (currentBatch.length) batches.push(currentBatch);
        return batches;
    }

    private async processWithRetry(operation: () => Promise<any>, retries = this.maxRetries): Promise<any> {
        try {
            return await operation();
        } catch (error: any) {
            if (error?.code === 'rate_limit_exceeded' && retries > 0) {
                await sleep(this.retryDelay * (this.maxRetries - retries + 1));
                return this.processWithRetry(operation, retries - 1);
            }
            throw error;
        }
    }

    private async extractTopicsFromDocs(docs: any[]) {
        const prompt = this.createExtractPrompt(docs);
        if (encode(prompt).length > this.maxTokensPerRequest) {
            throw new Error('Batch too large');
        }

        const response = await this.openai.chat.completions.create({
            model: 'gpt-4',
            messages: [{ role: 'user', content: prompt }],
            max_tokens: 1000,
            temperature: 0.5,
            presence_penalty: -0.5,
            frequency_penalty: 0.3
        });

        return this.parseTopicsResponse(response);
    }

    private createExtractPrompt(docs: any[]): string {
        return `Extract core business topics, companies, and trends. Format: ["topic1","topic2"]:
${docs.map(d => `${d.title}`).join('|')}`;
    }

    private parseTopicsResponse(response: any) {
        try {
            return JSON.parse(response.choices[0].message.content);
        } catch {
            return [];
        }
    }

    async testConnection(): Promise<boolean> {
        try {
            const response = await fetch('https://newsapi.org/v2/top-headlines?country=us&pageSize=1', {
                headers: { 'Authorization': `Bearer ${process.env.NEWS_API_KEY}` }
            });
            return (await response.json()).status === 'ok';
        } catch {
            return false;
        }
    }
} 