import { EventEmitter } from 'events';

export enum AgentStatus {
    IDLE = 'IDLE',
    BUSY = 'BUSY',
    ERROR = 'ERROR',
    INITIALIZING = 'INITIALIZING',
    TERMINATED = 'TERMINATED'
}

export enum AgentPriority {
    LOW = 0,
    MEDIUM = 1,
    HIGH = 2,
    CRITICAL = 3
}

export interface AgentMessage {
    id: string;
    type: string;
    priority: AgentPriority;
    sender: string;
    recipient: string;
    content: any;
    timestamp: Date;
    correlationId?: string;
    requiresResponse?: boolean;
}

export interface AgentConfig {
    id: string;
    name: string;
    description: string;
    capabilities: string[];
    dependencies: string[];
    apiKeys?: Record<string, string>;
}

export interface AgentState {
    status: AgentStatus;
    currentTask?: string;
    lastActive: Date;
    errorCount: number;
    metrics: Record<string, number>;
}

export interface AgentContext {
    userId: string;
    preferences: Map<string, any>;
    permissions: Set<string>;
    activeProcesses: Set<string>;
}

export abstract class BaseAgent extends EventEmitter {
    protected config: AgentConfig;
    protected state: AgentState;
    protected context: AgentContext;

    constructor(config: AgentConfig) {
        super();
        this.config = config;
        this.state = {
            status: AgentStatus.INITIALIZING,
            lastActive: new Date(),
            errorCount: 0,
            metrics: {}
        };
        this.context = {
            userId: '',
            preferences: new Map(),
            permissions: new Set(),
            activeProcesses: new Set()
        };
    }

    abstract initialize(): Promise<void>;
    abstract processMessage(message: AgentMessage): Promise<void>;
    abstract handleError(error: Error): Promise<void>;
    abstract shutdown(): Promise<void>;

    public async sendMessage(message: Partial<AgentMessage>): Promise<void> {
        const fullMessage: AgentMessage = {
            id: this.generateId(),
            type: message.type || 'UNKNOWN',
            priority: message.priority || AgentPriority.MEDIUM,
            sender: this.config.id,
            recipient: message.recipient || 'orchestrator',
            content: message.content,
            timestamp: new Date(),
            correlationId: message.correlationId,
            requiresResponse: message.requiresResponse
        };

        this.emit('message', fullMessage);
    }

    public async updateState(newState: Partial<AgentState>): Promise<void> {
        this.state = { ...this.state, ...newState };
        this.emit('stateChange', this.state);
    }

    public async updateContext(newContext: Partial<AgentContext>): Promise<void> {
        this.context = { ...this.context, ...newContext };
        this.emit('contextChange', this.context);
    }

    protected generateId(): string {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public getStatus(): AgentStatus {
        return this.state.status;
    }

    public getMetrics(): Record<string, number> {
        return this.state.metrics;
    }

    public getId(): string {
        return this.config.id;
    }

    public getCapabilities(): string[] {
        return this.config.capabilities;
    }
} 