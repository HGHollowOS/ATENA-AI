import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Context {
    id: string;
    userId: string;
    type: ContextType;
    scope: ContextScope;
    data: ContextData;
    priority: ContextPriority;
    confidence: number;
    validFrom: Date;
    validUntil?: Date;
    source: ContextSource;
    relations: ContextRelation[];
    metadata: Record<string, any>;
    createdAt: Date;
    updatedAt: Date;
}

export interface ContextData {
    location?: LocationContext;
    time?: TimeContext;
    activity?: ActivityContext;
    environment?: EnvironmentContext;
    cognitive?: CognitiveContext;
    social?: SocialContext;
    device?: DeviceContext;
    application?: ApplicationContext;
    custom?: Record<string, any>;
}

export interface LocationContext {
    type: string;
    coordinates?: {
        latitude: number;
        longitude: number;
    };
    address?: string;
    venue?: string;
    timezone?: string;
}

export interface TimeContext {
    timestamp: Date;
    localTime: string;
    timezone: string;
    workHours: boolean;
    timeOfDay: string;
    dayType: string;
}

export interface ActivityContext {
    type: string;
    status: string;
    duration?: number;
    intensity?: number;
    related?: string[];
}

export interface EnvironmentContext {
    type: string;
    noise?: number;
    light?: number;
    temperature?: number;
    weather?: string;
    conditions?: string[];
}

export interface CognitiveContext {
    attention: number;
    stress: number;
    fatigue: number;
    mood?: string;
    focus?: string;
}

export interface SocialContext {
    presence: string[];
    interaction?: string;
    group?: string;
    role?: string;
}

export interface DeviceContext {
    type: string;
    platform: string;
    status: string;
    battery?: number;
    network?: string;
}

export interface ApplicationContext {
    name: string;
    state: string;
    screen?: string;
    action?: string;
    data?: Record<string, any>;
}

export interface ContextRelation {
    type: RelationType;
    targetId: string;
    strength: number;
    metadata: Record<string, any>;
}

export interface ContextQuery {
    types?: ContextType[];
    scopes?: ContextScope[];
    timeRange?: {
        start: Date;
        end: Date;
    };
    priority?: ContextPriority;
    minConfidence?: number;
    source?: ContextSource;
}

export enum ContextType {
    LOCATION = 'LOCATION',
    TIME = 'TIME',
    ACTIVITY = 'ACTIVITY',
    ENVIRONMENT = 'ENVIRONMENT',
    COGNITIVE = 'COGNITIVE',
    SOCIAL = 'SOCIAL',
    DEVICE = 'DEVICE',
    APPLICATION = 'APPLICATION',
    SYSTEM = 'SYSTEM'
}

export enum ContextScope {
    PERSONAL = 'PERSONAL',
    WORK = 'WORK',
    SOCIAL = 'SOCIAL',
    SYSTEM = 'SYSTEM'
}

export enum ContextPriority {
    LOW = 'LOW',
    MEDIUM = 'MEDIUM',
    HIGH = 'HIGH',
    CRITICAL = 'CRITICAL'
}

export enum ContextSource {
    SENSOR = 'SENSOR',
    USER = 'USER',
    SYSTEM = 'SYSTEM',
    INFERENCE = 'INFERENCE',
    EXTERNAL = 'EXTERNAL'
}

export enum RelationType {
    RELATED = 'RELATED',
    DEPENDS_ON = 'DEPENDS_ON',
    INFLUENCES = 'INFLUENCES',
    CONFLICTS = 'CONFLICTS'
}

export class ContextAwarenessAgent extends BaseAgent {
    private contexts: Map<string, Context>;
    private messageBus: MessageBus;
    private updateInterval: NodeJS.Timeout | null;
    private inferenceQueue: Set<string>;

    constructor() {
        const config: AgentConfig = {
            id: 'context_awareness',
            name: 'Context Awareness Agent',
            description: 'Maintains and updates system understanding of user context',
            capabilities: [
                'context_tracking',
                'context_inference',
                'context_fusion',
                'anomaly_detection',
                'pattern_recognition',
                'context_prediction'
            ],
            dependencies: []
        };

        super(config);
        this.contexts = new Map();
        this.messageBus = MessageBus.getInstance();
        this.updateInterval = null;
        this.inferenceQueue = new Set();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.startContextUpdates();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'UPDATE_CONTEXT':
                await this.updateContext(message.content);
                break;

            case 'GET_CONTEXT':
                await this.sendContextDetails(message);
                break;

            case 'QUERY_CONTEXT':
                await this.queryContext(message);
                break;

            case 'INFER_CONTEXT':
                await this.inferContext(message.content.contextId);
                break;

            case 'DELETE_CONTEXT':
                await this.deleteContext(message.content.contextId);
                break;

            case 'PREDICT_CONTEXT':
                await this.predictContext(message);
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    public async updateContext(contextData: Partial<Context>): Promise<void> {
        const contextId = contextData.id || this.generateContextId();
        const now = new Date();
        const existingContext = this.contexts.get(contextId);

        const context: Context = {
            id: contextId,
            userId: contextData.userId || '',
            type: contextData.type || ContextType.SYSTEM,
            scope: contextData.scope || ContextScope.SYSTEM,
            data: contextData.data || {},
            priority: contextData.priority || ContextPriority.MEDIUM,
            confidence: contextData.confidence || 1.0,
            validFrom: contextData.validFrom || now,
            source: contextData.source || ContextSource.SYSTEM,
            relations: contextData.relations || [],
            metadata: contextData.metadata || {},
            createdAt: existingContext?.createdAt || now,
            updatedAt: now,
            ...contextData
        };

        this.contexts.set(contextId, context);

        await this.messageBus.broadcast({
            type: 'CONTEXT_UPDATED',
            content: { context },
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });

        // Queue for inference if needed
        if (this.shouldInferContext(context)) {
            this.inferenceQueue.add(contextId);
        }
    }

    private async deleteContext(contextId: string): Promise<void> {
        const context = this.contexts.get(contextId);
        if (!context) {
            throw new Error(`Context ${contextId} not found`);
        }

        this.contexts.delete(contextId);
        this.inferenceQueue.delete(contextId);

        await this.messageBus.broadcast({
            type: 'CONTEXT_DELETED',
            content: { contextId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async inferContext(contextId: string): Promise<void> {
        const context = this.contexts.get(contextId);
        if (!context) {
            throw new Error(`Context ${contextId} not found`);
        }

        try {
            const inferredData = await this.performContextInference(context);

            await this.updateContext({
                ...context,
                data: {
                    ...context.data,
                    ...inferredData
                },
                source: ContextSource.INFERENCE,
                confidence: this.calculateConfidence(context, inferredData)
            });
        } catch (error) {
            console.error(`Failed to infer context for ${contextId}:`, error);
        }
    }

    private async performContextInference(context: Context): Promise<Partial<ContextData>> {
        // Implement context inference logic
        return {};
    }

    private calculateConfidence(
        context: Context,
        inferredData: Partial<ContextData>
    ): number {
        // Implement confidence calculation logic
        return 0.8;
    }

    private shouldInferContext(context: Context): boolean {
        return (
            context.source !== ContextSource.INFERENCE &&
            context.confidence < 0.9
        );
    }

    private async queryContext(message: AgentMessage): Promise<void> {
        const query: ContextQuery = message.content.query;
        let results = Array.from(this.contexts.values());

        // Apply filters
        if (query.types) {
            results = results.filter(context =>
                query.types?.includes(context.type)
            );
        }
        if (query.scopes) {
            results = results.filter(context =>
                query.scopes?.includes(context.scope)
            );
        }
        if (query.timeRange) {
            const { start, end } = query.timeRange;
            if (start && end) {
                results = results.filter(context =>
                    context.validFrom >= start &&
                    (!context.validUntil || context.validUntil <= end)
                );
            }
        }
        if (query.priority) {
            results = results.filter(context =>
                context.priority === query.priority
            );
        }
        const minConfidence = query.minConfidence;
        if (minConfidence !== undefined && minConfidence !== null && typeof minConfidence === 'number') {
            results = results.filter(context =>
                context.confidence >= minConfidence
            );
        }
        if (query.source) {
            results = results.filter(context =>
                context.source === query.source
            );
        }

        await this.messageBus.sendMessage({
            type: 'CONTEXT_QUERY_RESPONSE',
            content: { results },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });
    }

    private async sendContextDetails(message: AgentMessage): Promise<void> {
        const contextId = message.content.contextId;
        const context = this.contexts.get(contextId);

        await this.messageBus.sendMessage({
            type: 'CONTEXT_DETAILS_RESPONSE',
            content: { context },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });
    }

    private async predictContext(message: AgentMessage): Promise<void> {
        const { contextId, timeframe } = message.content;
        const context = this.contexts.get(contextId);

        if (!context) {
            throw new Error(`Context ${contextId} not found`);
        }

        try {
            const prediction = await this.generateContextPrediction(context, timeframe);

            await this.messageBus.sendMessage({
                type: 'CONTEXT_PREDICTION_RESPONSE',
                content: { prediction },
                recipient: message.sender,
                correlationId: message.id,
                priority: AgentPriority.MEDIUM,
                sender: this.config.id
            });
        } catch (error) {
            console.error(`Failed to predict context for ${contextId}:`, error);
            throw error;
        }
    }

    private async generateContextPrediction(
        context: Context,
        timeframe: number
    ): Promise<Partial<Context>> {
        // Implement context prediction logic
        return {};
    }

    private startContextUpdates(): void {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(async () => {
            // Process inference queue
            for (const contextId of this.inferenceQueue) {
                await this.inferContext(contextId);
                this.inferenceQueue.delete(contextId);
            }

            // Update time-based contexts
            await this.updateTimeBasedContexts();

            // Check for expired contexts
            await this.cleanupExpiredContexts();
        }, 60000); // Run every minute
    }

    private async updateTimeBasedContexts(): Promise<void> {
        const now = new Date();

        // Update time context
        await this.updateContext({
            type: ContextType.TIME,
            scope: ContextScope.SYSTEM,
            data: {
                time: {
                    timestamp: now,
                    localTime: now.toLocaleTimeString(),
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    workHours: this.isWorkHours(now),
                    timeOfDay: this.getTimeOfDay(now),
                    dayType: this.getDayType(now)
                }
            },
            source: ContextSource.SYSTEM,
            confidence: 1.0
        });
    }

    private async cleanupExpiredContexts(): Promise<void> {
        const now = new Date();
        const expiredContexts = Array.from(this.contexts.values())
            .filter(context =>
                context.validUntil && context.validUntil < now
            );

        for (const context of expiredContexts) {
            await this.deleteContext(context.id);
        }
    }

    private isWorkHours(date: Date): boolean {
        const hours = date.getHours();
        const day = date.getDay();
        return day >= 1 && day <= 5 && hours >= 9 && hours < 17;
    }

    private getTimeOfDay(date: Date): string {
        const hours = date.getHours();
        if (hours < 6) return 'night';
        if (hours < 12) return 'morning';
        if (hours < 17) return 'afternoon';
        if (hours < 22) return 'evening';
        return 'night';
    }

    private getDayType(date: Date): string {
        const day = date.getDay();
        return day === 0 || day === 6 ? 'weekend' : 'workday';
    }

    private generateContextId(): string {
        return `context-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Context Awareness Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getContextCount(): number {
        return this.contexts.size;
    }

    public getContextsByType(type: ContextType): Context[] {
        return Array.from(this.contexts.values())
            .filter(context => context.type === type);
    }

    public getContextsByScope(scope: ContextScope): Context[] {
        return Array.from(this.contexts.values())
            .filter(context => context.scope === scope);
    }

    public getActiveContexts(): Context[] {
        const now = new Date();
        return Array.from(this.contexts.values())
            .filter(context =>
                !context.validUntil || context.validUntil > now
            );
    }

    public getHighPriorityContexts(): Context[] {
        return Array.from(this.contexts.values())
            .filter(context =>
                context.priority === ContextPriority.HIGH ||
                context.priority === ContextPriority.CRITICAL
            );
    }

    public getUserContexts(userId: string): Context[] {
        return Array.from(this.contexts.values())
            .filter(context => context.userId === userId);
    }
} 