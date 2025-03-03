import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface KnowledgeItem {
    id: string;
    title: string;
    content: string;
    type: KnowledgeType;
    format: ContentFormat;
    tags: string[];
    categories: string[];
    metadata: Record<string, any>;
    source?: string;
    author?: string;
    version: number;
    status: KnowledgeStatus;
    visibility: VisibilityLevel;
    relations: KnowledgeRelation[];
    embeddings?: number[];
    lastAccessed?: Date;
    accessCount: number;
    createdAt: Date;
    updatedAt: Date;
}

export interface KnowledgeRelation {
    type: RelationType;
    targetId: string;
    metadata: Record<string, any>;
}

export interface SearchQuery {
    query: string;
    filters?: {
        types?: KnowledgeType[];
        categories?: string[];
        tags?: string[];
        status?: KnowledgeStatus;
        visibility?: VisibilityLevel;
        dateRange?: {
            start: Date;
            end: Date;
        };
    };
    sort?: {
        field: string;
        order: 'asc' | 'desc';
    };
    limit?: number;
    offset?: number;
}

export interface SearchResult {
    item: KnowledgeItem;
    score: number;
    highlights: {
        field: string;
        snippet: string;
    }[];
}

export enum KnowledgeType {
    DOCUMENT = 'DOCUMENT',
    NOTE = 'NOTE',
    PROCEDURE = 'PROCEDURE',
    REFERENCE = 'REFERENCE',
    DECISION = 'DECISION',
    MEETING = 'MEETING'
}

export enum ContentFormat {
    TEXT = 'TEXT',
    MARKDOWN = 'MARKDOWN',
    HTML = 'HTML',
    JSON = 'JSON',
    BINARY = 'BINARY'
}

export enum KnowledgeStatus {
    DRAFT = 'DRAFT',
    PUBLISHED = 'PUBLISHED',
    ARCHIVED = 'ARCHIVED',
    DEPRECATED = 'DEPRECATED'
}

export enum VisibilityLevel {
    PRIVATE = 'PRIVATE',
    TEAM = 'TEAM',
    ORGANIZATION = 'ORGANIZATION',
    PUBLIC = 'PUBLIC'
}

export enum RelationType {
    REFERENCES = 'REFERENCES',
    RELATED_TO = 'RELATED_TO',
    DEPENDS_ON = 'DEPENDS_ON',
    SUPERSEDES = 'SUPERSEDES',
    DERIVED_FROM = 'DERIVED_FROM'
}

export class KnowledgeManagementAgent extends BaseAgent {
    private knowledgeBase: Map<string, KnowledgeItem>;
    private messageBus: MessageBus;
    private searchIndex: any; // Replace with actual search index type

    constructor() {
        const config: AgentConfig = {
            id: 'knowledge_management',
            name: 'Knowledge Management Agent',
            description: 'Manages knowledge base and information retrieval',
            capabilities: [
                'knowledge_storage',
                'information_retrieval',
                'semantic_search',
                'content_organization',
                'version_tracking',
                'access_control'
            ],
            dependencies: []
        };

        super(config);
        this.knowledgeBase = new Map();
        this.messageBus = MessageBus.getInstance();
        this.initializeSearchIndex();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    private initializeSearchIndex(): void {
        // Initialize search index (e.g., using elasticsearch, meilisearch, etc.)
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'CREATE_KNOWLEDGE_ITEM':
                await this.createKnowledgeItem(message.content);
                break;

            case 'UPDATE_KNOWLEDGE_ITEM':
                await this.updateKnowledgeItem(
                    message.content.itemId,
                    message.content.updates
                );
                break;

            case 'DELETE_KNOWLEDGE_ITEM':
                await this.deleteKnowledgeItem(message.content.itemId);
                break;

            case 'SEARCH_KNOWLEDGE':
                await this.searchKnowledge(message);
                break;

            case 'GET_KNOWLEDGE_ITEM':
                await this.sendKnowledgeItemDetails(message);
                break;

            case 'LIST_KNOWLEDGE_ITEMS':
                await this.sendKnowledgeItemsList(message);
                break;

            case 'ADD_RELATION':
                await this.addRelation(
                    message.content.sourceId,
                    message.content.relation
                );
                break;

            case 'GENERATE_EMBEDDINGS':
                await this.generateEmbeddings(message.content.itemId);
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createKnowledgeItem(itemData: Partial<KnowledgeItem>): Promise<void> {
        const itemId = this.generateKnowledgeItemId();
        const now = new Date();

        const item: KnowledgeItem = {
            id: itemId,
            title: itemData.title || '',
            content: itemData.content || '',
            type: itemData.type || KnowledgeType.DOCUMENT,
            format: itemData.format || ContentFormat.TEXT,
            tags: itemData.tags || [],
            categories: itemData.categories || [],
            metadata: itemData.metadata || {},
            version: 1,
            status: KnowledgeStatus.DRAFT,
            visibility: itemData.visibility || VisibilityLevel.PRIVATE,
            relations: [],
            accessCount: 0,
            createdAt: now,
            updatedAt: now,
            ...itemData
        };

        this.knowledgeBase.set(itemId, item);
        await this.indexKnowledgeItem(item);

        await this.messageBus.broadcast({
            type: 'KNOWLEDGE_ITEM_CREATED',
            content: { item },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });

        // Generate embeddings if content is available
        if (item.content) {
            await this.generateEmbeddings(itemId);
        }
    }

    private async updateKnowledgeItem(
        itemId: string,
        updates: Partial<KnowledgeItem>
    ): Promise<void> {
        const item = this.knowledgeBase.get(itemId);
        if (!item) {
            throw new Error(`Knowledge item ${itemId} not found`);
        }

        const updatedItem: KnowledgeItem = {
            ...item,
            ...updates,
            version: item.version + 1,
            updatedAt: new Date()
        };

        this.knowledgeBase.set(itemId, updatedItem);
        await this.indexKnowledgeItem(updatedItem);

        await this.messageBus.broadcast({
            type: 'KNOWLEDGE_ITEM_UPDATED',
            content: { item: updatedItem },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });

        // Regenerate embeddings if content was updated
        if (updates.content) {
            await this.generateEmbeddings(itemId);
        }
    }

    private async deleteKnowledgeItem(itemId: string): Promise<void> {
        const item = this.knowledgeBase.get(itemId);
        if (!item) {
            throw new Error(`Knowledge item ${itemId} not found`);
        }

        this.knowledgeBase.delete(itemId);
        await this.removeFromIndex(itemId);

        await this.messageBus.broadcast({
            type: 'KNOWLEDGE_ITEM_DELETED',
            content: { itemId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async addRelation(
        sourceId: string,
        relation: KnowledgeRelation
    ): Promise<void> {
        const sourceItem = this.knowledgeBase.get(sourceId);
        if (!sourceItem) {
            throw new Error(`Knowledge item ${sourceId} not found`);
        }

        const targetItem = this.knowledgeBase.get(relation.targetId);
        if (!targetItem) {
            throw new Error(`Target item ${relation.targetId} not found`);
        }

        sourceItem.relations.push(relation);
        await this.updateKnowledgeItem(sourceId, { relations: sourceItem.relations });
    }

    private async generateEmbeddings(itemId: string): Promise<void> {
        const item = this.knowledgeBase.get(itemId);
        if (!item) {
            throw new Error(`Knowledge item ${itemId} not found`);
        }

        try {
            // Generate embeddings using an embedding model (e.g., OpenAI, Hugging Face)
            const embeddings = await this.computeEmbeddings(item.content);

            await this.updateKnowledgeItem(itemId, { embeddings });
        } catch (error) {
            console.error(`Failed to generate embeddings for item ${itemId}:`, error);
        }
    }

    private async computeEmbeddings(content: string): Promise<number[]> {
        // Implement embedding computation logic
        return [];
    }

    private async searchKnowledge(message: AgentMessage): Promise<void> {
        const query: SearchQuery = message.content.query;
        let results: SearchResult[] = [];

        try {
            if (query.query) {
                // Perform semantic search if embeddings are available
                const queryEmbeddings = await this.computeEmbeddings(query.query);
                results = await this.semanticSearch(queryEmbeddings, query);
            } else {
                // Perform regular search
                results = await this.regularSearch(query);
            }

            await this.messageBus.sendMessage({
                type: 'SEARCH_RESULTS',
                content: { results },
                recipient: message.sender,
                correlationId: message.id,
                priority: AgentPriority.MEDIUM,
                sender: this.config.id
            });
        } catch (error) {
            console.error('Search failed:', error);
            throw error;
        }
    }

    private async semanticSearch(
        queryEmbeddings: number[],
        query: SearchQuery
    ): Promise<SearchResult[]> {
        // Implement semantic search logic
        return [];
    }

    private async regularSearch(query: SearchQuery): Promise<SearchResult[]> {
        // Implement regular search logic
        return [];
    }

    private async indexKnowledgeItem(item: KnowledgeItem): Promise<void> {
        // Implement search index update logic
    }

    private async removeFromIndex(itemId: string): Promise<void> {
        // Implement search index removal logic
    }

    private async sendKnowledgeItemDetails(message: AgentMessage): Promise<void> {
        const itemId = message.content.itemId;
        const item = this.knowledgeBase.get(itemId);

        if (item) {
            // Update access statistics
            await this.updateKnowledgeItem(itemId, {
                lastAccessed: new Date(),
                accessCount: item.accessCount + 1
            });
        }

        await this.messageBus.sendMessage({
            type: 'KNOWLEDGE_ITEM_DETAILS_RESPONSE',
            content: { item },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendKnowledgeItemsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let items = Array.from(this.knowledgeBase.values());

        // Apply filters
        if (filters.type) {
            items = items.filter(item => item.type === filters.type);
        }
        if (filters.status) {
            items = items.filter(item => item.status === filters.status);
        }
        if (filters.visibility) {
            items = items.filter(item => item.visibility === filters.visibility);
        }
        if (filters.tags) {
            items = items.filter(item =>
                filters.tags.some((tag: string) => item.tags.includes(tag))
            );
        }
        if (filters.categories) {
            items = items.filter(item =>
                filters.categories.some((category: string) =>
                    item.categories.includes(category)
                )
            );
        }

        await this.messageBus.sendMessage({
            type: 'KNOWLEDGE_ITEMS_LIST_RESPONSE',
            content: { items },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateKnowledgeItemId(): string {
        return `knowledge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Knowledge Management Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getKnowledgeItemCount(): number {
        return this.knowledgeBase.size;
    }

    public getKnowledgeItemsByType(type: KnowledgeType): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .filter(item => item.type === type);
    }

    public getKnowledgeItemsByStatus(status: KnowledgeStatus): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .filter(item => item.status === status);
    }

    public getKnowledgeItemsByTag(tag: string): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .filter(item => item.tags.includes(tag));
    }

    public getKnowledgeItemsByCategory(category: string): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .filter(item => item.categories.includes(category));
    }

    public getMostAccessedItems(limit: number = 10): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .sort((a, b) => b.accessCount - a.accessCount)
            .slice(0, limit);
    }

    public getRecentlyUpdatedItems(limit: number = 10): KnowledgeItem[] {
        return Array.from(this.knowledgeBase.values())
            .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
            .slice(0, limit);
    }
} 