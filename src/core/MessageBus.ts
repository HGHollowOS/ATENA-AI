import { EventEmitter } from 'events';
import { AgentMessage, AgentPriority, BaseAgent } from './types/Agent';

export class MessageBus extends EventEmitter {
    private static instance: MessageBus;
    private agents: Map<string, BaseAgent>;
    private messageQueue: AgentMessage[];
    private processingQueue: boolean;

    private constructor() {
        super();
        this.agents = new Map();
        this.messageQueue = [];
        this.processingQueue = false;
    }

    public static getInstance(): MessageBus {
        if (!MessageBus.instance) {
            MessageBus.instance = new MessageBus();
        }
        return MessageBus.instance;
    }

    public registerAgent(agent: BaseAgent): void {
        if (this.agents.has(agent.getId())) {
            throw new Error(`Agent with ID ${agent.getId()} is already registered`);
        }

        this.agents.set(agent.getId(), agent);
        agent.on('message', (message: AgentMessage) => this.routeMessage(message));
    }

    public unregisterAgent(agentId: string): void {
        const agent = this.agents.get(agentId);
        if (agent) {
            agent.removeAllListeners('message');
            this.agents.delete(agentId);
        }
    }

    public async broadcast(message: Partial<AgentMessage>): Promise<void> {
        const fullMessage: AgentMessage = this.createFullMessage(message);
        for (const agent of this.agents.values()) {
            if (agent.getId() !== fullMessage.sender) {
                await this.queueMessage({ ...fullMessage, recipient: agent.getId() });
            }
        }
    }

    public async sendMessage(message: Partial<AgentMessage>): Promise<void> {
        const fullMessage = this.createFullMessage(message);
        await this.queueMessage(fullMessage);
    }

    private async queueMessage(message: AgentMessage): Promise<void> {
        this.messageQueue.push(message);
        this.emit('messageQueued', message);

        if (!this.processingQueue) {
            await this.processQueue();
        }
    }

    private async processQueue(): Promise<void> {
        this.processingQueue = true;

        while (this.messageQueue.length > 0) {
            const messages = this.messageQueue
                .sort((a, b) => b.priority - a.priority)
                .slice(0, 10);

            this.messageQueue = this.messageQueue.slice(10);

            await Promise.all(messages.map(msg => this.routeMessage(msg)));
        }

        this.processingQueue = false;
    }

    private async routeMessage(message: AgentMessage): Promise<void> {
        const recipient = this.agents.get(message.recipient);

        if (!recipient) {
            console.error(`No agent found for recipient: ${message.recipient}`);
            return;
        }

        try {
            await recipient.processMessage(message);
            this.emit('messageDelivered', message);
        } catch (error) {
            console.error(`Error delivering message to ${message.recipient}:`, error);
            this.emit('messageError', { message, error });
        }
    }

    private createFullMessage(partial: Partial<AgentMessage>): AgentMessage {
        return {
            id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type: partial.type || 'UNKNOWN',
            priority: partial.priority || AgentPriority.MEDIUM,
            sender: partial.sender || 'system',
            recipient: partial.recipient || 'orchestrator',
            content: partial.content,
            timestamp: new Date(),
            correlationId: partial.correlationId,
            requiresResponse: partial.requiresResponse
        };
    }

    public getRegisteredAgents(): string[] {
        return Array.from(this.agents.keys());
    }

    public getQueueLength(): number {
        return this.messageQueue.length;
    }

    public isProcessing(): boolean {
        return this.processingQueue;
    }
} 