import OpenAI from 'openai';
import { NewsArticle } from '../types';

export class NewsIntegration {
    private openai: OpenAI;
    private googleWorkspace: any; // Will be properly typed when passed

    constructor(apiKey: string, googleWorkspace: any) {
        this.openai = new OpenAI({ apiKey });
        this.googleWorkspace = googleWorkspace;
    }

    async getRelevantNews(): Promise<NewsArticle[]> {
        try {
            // Get documents from Google Drive
            const documents = await this.googleWorkspace.listDocuments();

            // Extract key topics and entities from documents
            const topics = await this.extractTopicsFromDocs(documents);

            // Fetch news using NewsAPI
            const response = await fetch(`https://newsapi.org/v2/everything?q=${encodeURIComponent(topics.join(' OR '))}&sortBy=publishedAt&language=en`, {
                headers: {
                    'Authorization': `Bearer ${process.env.NEWS_API_KEY}`
                }
            });

            const newsData = await response.json();

            // Filter and rank articles based on relevance to our context
            const relevantArticles = await this.rankArticlesByRelevance(
                newsData.articles,
                topics
            );

            return relevantArticles.map(article => ({
                id: Math.random().toString(36).substring(7),
                title: article.title,
                description: article.description,
                url: article.url,
                publishedAt: new Date(article.publishedAt),
                relevanceScore: article.relevanceScore,
                relatedTopics: article.relatedTopics
            }));
        } catch (error) {
            console.error('Error fetching news:', error);
            return [];
        }
    }

    private async extractTopicsFromDocs(documents: any[]): Promise<string[]> {
        const documentContents = documents.map(doc => doc.content).join('\n');

        const completion = await this.openai.chat.completions.create({
            model: "gpt-4",
            messages: [
                {
                    role: "system",
                    content: "Extract key topics, companies, technologies, and industry terms from the following text. Return them as a JSON array of strings."
                },
                {
                    role: "user",
                    content: documentContents
                }
            ]
        });

        return JSON.parse(completion.choices[0].message?.content || '[]');
    }

    private async rankArticlesByRelevance(
        articles: any[],
        topics: string[]
    ): Promise<NewsArticle[]> {
        const completion = await this.openai.chat.completions.create({
            model: "gpt-4",
            messages: [
                {
                    role: "system",
                    content: "Analyze these news articles and rank them by relevance to our topics. Return a JSON array with relevance scores and related topics."
                },
                {
                    role: "user",
                    content: JSON.stringify({ articles, topics })
                }
            ]
        });

        return JSON.parse(completion.choices[0].message?.content || '[]');
    }

    async testConnection(): Promise<boolean> {
        try {
            const response = await fetch('https://newsapi.org/v2/top-headlines?country=us&pageSize=1', {
                headers: {
                    'Authorization': `Bearer ${process.env.NEWS_API_KEY}`
                }
            });
            const data = await response.json();
            return data.status === 'ok';
        } catch (error) {
            console.error('News API connection test failed:', error);
            return false;
        }
    }
} 