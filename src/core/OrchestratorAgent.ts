import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from './types/Agent';
import { MessageBus } from './MessageBus';

export interface AgentRegistry {
    [key: string]: {
        agentClass: new (config: AgentConfig) => BaseAgent;
        config: AgentConfig;
    };
}

export class OrchestratorAgent extends BaseAgent {
    private registry: AgentRegistry;
    private activeAgents: Map<string, BaseAgent>;
    private messageBus: MessageBus;
    private healthCheckInterval: NodeJS.Timeout | null;

    constructor() {
        const config: AgentConfig = {
            id: 'orchestrator',
            name: 'Core Orchestrator Agent',
            description: 'Manages and coordinates all other agents in the system',
            capabilities: [
                'agent_lifecycle_management',
                'health_monitoring',
                'task_delegation',
                'resource_management',
                'error_handling'
            ],
            dependencies: []
        };

        super(config);
        this.registry = {};
        this.activeAgents = new Map();
        this.messageBus = MessageBus.getInstance();
        this.healthCheckInterval = null;
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.startHealthCheck();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public registerAgentType(
        id: string,
        agentClass: new (config: AgentConfig) => BaseAgent,
        config: AgentConfig
    ): void {
        this.registry[id] = { agentClass, config };
    }

    public async startAgent(agentId: string): Promise<void> {
        if (!this.registry[agentId]) {
            throw new Error(`Agent type ${agentId} not registered`);
        }

        if (this.activeAgents.has(agentId)) {
            throw new Error(`Agent ${agentId} is already running`);
        }

        const { agentClass, config } = this.registry[agentId];
        const agent = new agentClass(config);

        try {
            await agent.initialize();
            this.activeAgents.set(agentId, agent);
            this.messageBus.registerAgent(agent);

            await this.broadcast({
                type: 'AGENT_STARTED',
                content: { agentId },
                priority: AgentPriority.HIGH
            });
        } catch (error) {
            console.error(`Failed to start agent ${agentId}:`, error);
            throw error;
        }
    }

    public async stopAgent(agentId: string): Promise<void> {
        const agent = this.activeAgents.get(agentId);
        if (!agent) {
            throw new Error(`Agent ${agentId} is not running`);
        }

        try {
            await agent.shutdown();
            this.messageBus.unregisterAgent(agentId);
            this.activeAgents.delete(agentId);

            await this.broadcast({
                type: 'AGENT_STOPPED',
                content: { agentId },
                priority: AgentPriority.HIGH
            });
        } catch (error) {
            console.error(`Failed to stop agent ${agentId}:`, error);
            throw error;
        }
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'START_AGENT':
                await this.startAgent(message.content.agentId);
                break;

            case 'STOP_AGENT':
                await this.stopAgent(message.content.agentId);
                break;

            case 'AGENT_ERROR':
                await this.handleAgentError(message.content);
                break;

            case 'GET_AGENT_STATUS':
                await this.sendAgentStatus(message);
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async handleAgentError(content: { agentId: string; error: Error }): Promise<void> {
        const { agentId, error } = content;
        console.error(`Error in agent ${agentId}:`, error);

        const agent = this.activeAgents.get(agentId);
        if (agent) {
            try {
                await agent.handleError(error);
            } catch (e) {
                console.error(`Failed to handle error in agent ${agentId}:`, e);
                await this.stopAgent(agentId);
                await this.startAgent(agentId);
            }
        }
    }

    private async sendAgentStatus(message: AgentMessage): Promise<void> {
        const statuses = Array.from(this.activeAgents.entries()).map(([id, agent]) => ({
            id,
            status: agent.getStatus(),
            metrics: agent.getMetrics()
        }));

        await this.messageBus.sendMessage({
            type: 'AGENT_STATUS_RESPONSE',
            content: { statuses },
            recipient: message.sender,
            correlationId: message.id
        });
    }

    private startHealthCheck(): void {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }

        this.healthCheckInterval = setInterval(async () => {
            for (const [agentId, agent] of this.activeAgents.entries()) {
                if (agent.getStatus() === AgentStatus.ERROR) {
                    console.warn(`Agent ${agentId} is in ERROR state, attempting restart`);
                    try {
                        await this.stopAgent(agentId);
                        await this.startAgent(agentId);
                    } catch (error) {
                        console.error(`Failed to restart agent ${agentId}:`, error);
                    }
                }
            }
        }, 60000); // Check every minute
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Orchestrator error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }

        for (const agentId of this.activeAgents.keys()) {
            await this.stopAgent(agentId);
        }

        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    private async broadcast(message: Partial<AgentMessage>): Promise<void> {
        await this.messageBus.broadcast({
            ...message,
            sender: this.config.id
        });
    }

    public getActiveAgents(): string[] {
        return Array.from(this.activeAgents.keys());
    }

    public getRegisteredAgentTypes(): string[] {
        return Object.keys(this.registry);
    }
} 