import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Integration {
    id: string;
    name: string;
    type: IntegrationType;
    provider: string;
    status: IntegrationStatus;
    config: IntegrationConfig;
    credentials: IntegrationCredentials;
    capabilities: string[];
    metadata: Record<string, any>;
    healthCheck: HealthCheckConfig;
    rateLimits?: RateLimitConfig;
    retryPolicy?: RetryPolicy;
    createdAt: Date;
    updatedAt: Date;
    lastHealthCheck?: Date;
}

export interface IntegrationConfig {
    apiVersion?: string;
    baseUrl?: string;
    endpoints: Record<string, EndpointConfig>;
    headers?: Record<string, string>;
    timeout?: number;
    parameters?: Record<string, any>;
}

export interface EndpointConfig {
    path: string;
    method: string;
    requiresAuth: boolean;
    parameters?: Record<string, any>;
    rateLimit?: RateLimitConfig;
    timeout?: number;
}

export interface IntegrationCredentials {
    type: CredentialType;
    data: Record<string, any>;
    expiresAt?: Date;
    refreshToken?: string;
    scopes?: string[];
}

export interface HealthCheckConfig {
    endpoint?: string;
    interval: number;
    timeout: number;
    successCodes: number[];
    failureThreshold: number;
    successThreshold: number;
}

export interface RateLimitConfig {
    requests: number;
    period: number;
    remaining?: number;
    resetAt?: Date;
}

export interface RetryPolicy {
    maxAttempts: number;
    backoffType: BackoffType;
    initialInterval: number;
    maxInterval: number;
    multiplier: number;
}

export enum IntegrationType {
    API = 'API',
    OAUTH = 'OAUTH',
    WEBHOOK = 'WEBHOOK',
    DATABASE = 'DATABASE',
    MESSAGE_QUEUE = 'MESSAGE_QUEUE',
    DISCORD = 'DISCORD'
}

export enum IntegrationStatus {
    CONFIGURED = 'CONFIGURED',
    CONNECTED = 'CONNECTED',
    DISCONNECTED = 'DISCONNECTED',
    ERROR = 'ERROR',
    RATE_LIMITED = 'RATE_LIMITED'
}

export enum CredentialType {
    API_KEY = 'API_KEY',
    OAUTH2 = 'OAUTH2',
    JWT = 'JWT',
    BASIC_AUTH = 'BASIC_AUTH',
    CUSTOM = 'CUSTOM'
}

export enum BackoffType {
    FIXED = 'FIXED',
    EXPONENTIAL = 'EXPONENTIAL',
    LINEAR = 'LINEAR'
}

export interface DiscordConfig extends IntegrationConfig {
    botToken: string;
    clientId: string;
    clientSecret: string;
    guildIds: string[];
    permissions: string[];
    endpoints: {
        messages: EndpointConfig;
        channels: EndpointConfig;
        guilds: EndpointConfig;
        threads: EndpointConfig;
        reactions: EndpointConfig;
    };
    eventHandlers: {
        messageCreate: boolean;
        messageUpdate: boolean;
        messageDelete: boolean;
        threadCreate: boolean;
        threadUpdate: boolean;
        reactionAdd: boolean;
        reactionRemove: boolean;
    };
}

export interface DiscordCredentials extends IntegrationCredentials {
    type: CredentialType.OAUTH2;
    data: {
        botToken: string;
        clientId: string;
        clientSecret: string;
        accessToken?: string;
        refreshToken?: string;
    };
    scopes: string[];
}

export class IntegrationAgent extends BaseAgent {
    private integrations: Map<string, Integration>;
    private messageBus: MessageBus;
    private healthCheckIntervals: Map<string, NodeJS.Timeout>;
    private rateLimiters: Map<string, RateLimitState>;

    constructor() {
        const config: AgentConfig = {
            id: 'integration',
            name: 'Integration Agent',
            description: 'Manages external service integrations and API connections',
            capabilities: [
                'integration_management',
                'api_orchestration',
                'credential_management',
                'health_monitoring',
                'rate_limiting',
                'error_handling'
            ],
            dependencies: []
        };

        super(config);
        this.integrations = new Map();
        this.messageBus = MessageBus.getInstance();
        this.healthCheckIntervals = new Map();
        this.rateLimiters = new Map();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.startHealthChecks();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'CREATE_INTEGRATION':
                await this.createIntegration(message.content);
                break;

            case 'UPDATE_INTEGRATION':
                await this.updateIntegration(
                    message.content.integrationId,
                    message.content.updates
                );
                break;

            case 'DELETE_INTEGRATION':
                await this.deleteIntegration(message.content.integrationId);
                break;

            case 'EXECUTE_REQUEST':
                await this.executeRequest(
                    message.content.integrationId,
                    message.content.endpoint,
                    message.content.parameters
                );
                break;

            case 'REFRESH_CREDENTIALS':
                await this.refreshCredentials(message.content.integrationId);
                break;

            case 'GET_INTEGRATION':
                await this.sendIntegrationDetails(message);
                break;

            case 'LIST_INTEGRATIONS':
                await this.sendIntegrationsList(message);
                break;

            case 'INITIALIZE_DISCORD':
                const integration = this.integrations.get(message.content.integrationId);
                if (integration) {
                    await this.initializeDiscordIntegration(integration);
                }
                break;

            case 'DISCORD_SEND_MESSAGE':
                await this.executeRequest(
                    message.content.integrationId,
                    'messages',
                    {
                        channelId: message.content.channelId,
                        content: message.content.message,
                        embeds: message.content.embeds,
                        components: message.content.components
                    }
                );
                break;

            case 'DISCORD_CREATE_THREAD':
                await this.executeRequest(
                    message.content.integrationId,
                    'threads',
                    {
                        channelId: message.content.channelId,
                        name: message.content.threadName,
                        message: message.content.message
                    }
                );
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createIntegration(integrationData: Partial<Integration>): Promise<void> {
        const integrationId = this.generateIntegrationId();
        const now = new Date();

        const integration: Integration = {
            id: integrationId,
            name: integrationData.name || '',
            type: integrationData.type || IntegrationType.API,
            provider: integrationData.provider || '',
            status: IntegrationStatus.CONFIGURED,
            config: integrationData.config || {
                endpoints: {}
            },
            credentials: integrationData.credentials || {
                type: CredentialType.API_KEY,
                data: {}
            },
            capabilities: integrationData.capabilities || [],
            metadata: integrationData.metadata || {},
            healthCheck: integrationData.healthCheck || {
                interval: 300000, // 5 minutes
                timeout: 5000,
                successCodes: [200],
                failureThreshold: 3,
                successThreshold: 1
            },
            createdAt: now,
            updatedAt: now,
            ...integrationData
        };

        this.integrations.set(integrationId, integration);
        this.setupHealthCheck(integration);

        await this.messageBus.broadcast({
            type: 'INTEGRATION_CREATED',
            content: { integration },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateIntegration(
        integrationId: string,
        updates: Partial<Integration>
    ): Promise<void> {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            throw new Error(`Integration ${integrationId} not found`);
        }

        const updatedIntegration: Integration = {
            ...integration,
            ...updates,
            updatedAt: new Date()
        };

        this.integrations.set(integrationId, updatedIntegration);
        this.setupHealthCheck(updatedIntegration);

        await this.messageBus.broadcast({
            type: 'INTEGRATION_UPDATED',
            content: { integration: updatedIntegration },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async deleteIntegration(integrationId: string): Promise<void> {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            throw new Error(`Integration ${integrationId} not found`);
        }

        this.clearHealthCheck(integrationId);
        this.integrations.delete(integrationId);

        await this.messageBus.broadcast({
            type: 'INTEGRATION_DELETED',
            content: { integrationId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async executeRequest(
        integrationId: string,
        endpointName: string,
        parameters: Record<string, any>
    ): Promise<any> {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            throw new Error(`Integration ${integrationId} not found`);
        }

        const endpoint = integration.config.endpoints[endpointName];
        if (!endpoint) {
            throw new Error(`Endpoint ${endpointName} not found in integration ${integrationId}`);
        }

        // Check rate limits
        if (endpoint.rateLimit) {
            await this.checkRateLimit(integrationId, endpointName);
        }

        try {
            // Execute request logic here
            const response = await this.makeRequest(integration, endpoint, parameters);

            // Update rate limit state
            if (endpoint.rateLimit) {
                this.updateRateLimitState(integrationId, endpointName, response.headers);
            }

            return response.data;
        } catch (error) {
            if (this.isRateLimitError(error)) {
                integration.status = IntegrationStatus.RATE_LIMITED;
                await this.updateIntegration(integrationId, { status: IntegrationStatus.RATE_LIMITED });
            }
            throw error;
        }
    }

    private async makeRequest(
        integration: Integration,
        endpoint: EndpointConfig,
        parameters: Record<string, any>
    ): Promise<any> {
        // Implement request logic
        return { data: {}, headers: {} };
    }

    private async refreshCredentials(integrationId: string): Promise<void> {
        const integration = this.integrations.get(integrationId);
        if (!integration) {
            throw new Error(`Integration ${integrationId} not found`);
        }

        if (integration.credentials.type !== CredentialType.OAUTH2) {
            throw new Error('Only OAuth2 credentials can be refreshed');
        }

        try {
            // Implement credential refresh logic
            const newCredentials = await this.refreshOAuthCredentials(integration);

            await this.updateIntegration(integrationId, {
                credentials: newCredentials,
                status: IntegrationStatus.CONNECTED
            });
        } catch (error) {
            await this.updateIntegration(integrationId, {
                status: IntegrationStatus.ERROR
            });
            throw error;
        }
    }

    private async refreshOAuthCredentials(
        integration: Integration
    ): Promise<IntegrationCredentials> {
        // Implement OAuth refresh logic
        return integration.credentials;
    }

    private async checkRateLimit(
        integrationId: string,
        endpointName: string
    ): Promise<void> {
        const key = `${integrationId}:${endpointName}`;
        const state = this.rateLimiters.get(key);

        if (state && state.resetAt && state.remaining !== undefined) {
            if (state.resetAt > new Date() && state.remaining <= 0) {
                throw new Error('Rate limit exceeded');
            }
        }
    }

    private updateRateLimitState(
        integrationId: string,
        endpointName: string,
        headers: Record<string, any>
    ): void {
        // Implement rate limit state update logic based on response headers
        const key = `${integrationId}:${endpointName}`;
        this.rateLimiters.set(key, {
            remaining: parseInt(headers['x-ratelimit-remaining'] || '0'),
            resetAt: new Date(parseInt(headers['x-ratelimit-reset'] || '0') * 1000)
        });
    }

    private isRateLimitError(error: any): boolean {
        return error.status === 429;
    }

    private setupHealthCheck(integration: Integration): void {
        this.clearHealthCheck(integration.id);

        const interval = setInterval(async () => {
            try {
                await this.performHealthCheck(integration);
            } catch (error) {
                console.error(`Health check failed for integration ${integration.id}:`, error);
            }
        }, integration.healthCheck.interval);

        this.healthCheckIntervals.set(integration.id, interval);
    }

    private clearHealthCheck(integrationId: string): void {
        const interval = this.healthCheckIntervals.get(integrationId);
        if (interval) {
            clearInterval(interval);
            this.healthCheckIntervals.delete(integrationId);
        }
    }

    private async performHealthCheck(integration: Integration): Promise<void> {
        try {
            if (integration.healthCheck.endpoint) {
                await this.executeRequest(
                    integration.id,
                    integration.healthCheck.endpoint,
                    {}
                );
            }

            await this.updateIntegration(integration.id, {
                status: IntegrationStatus.CONNECTED,
                lastHealthCheck: new Date()
            });
        } catch (error) {
            await this.updateIntegration(integration.id, {
                status: IntegrationStatus.ERROR,
                lastHealthCheck: new Date()
            });
        }
    }

    private startHealthChecks(): void {
        for (const integration of this.integrations.values()) {
            this.setupHealthCheck(integration);
        }
    }

    private async sendIntegrationDetails(message: AgentMessage): Promise<void> {
        const integrationId = message.content.integrationId;
        const integration = this.integrations.get(integrationId);

        await this.messageBus.sendMessage({
            type: 'INTEGRATION_DETAILS_RESPONSE',
            content: { integration },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendIntegrationsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let integrations = Array.from(this.integrations.values());

        // Apply filters
        if (filters.type) {
            integrations = integrations.filter(
                integration => integration.type === filters.type
            );
        }
        if (filters.provider) {
            integrations = integrations.filter(
                integration => integration.provider === filters.provider
            );
        }
        if (filters.status) {
            integrations = integrations.filter(
                integration => integration.status === filters.status
            );
        }

        await this.messageBus.sendMessage({
            type: 'INTEGRATIONS_LIST_RESPONSE',
            content: { integrations },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateIntegrationId(): string {
        return `integration-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Integration Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        // Clear all health check intervals
        for (const interval of this.healthCheckIntervals.values()) {
            clearInterval(interval);
        }
        this.healthCheckIntervals.clear();

        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getIntegrationCount(): number {
        return this.integrations.size;
    }

    public getIntegrationsByType(type: IntegrationType): Integration[] {
        return Array.from(this.integrations.values())
            .filter(integration => integration.type === type);
    }

    public getIntegrationsByStatus(status: IntegrationStatus): Integration[] {
        return Array.from(this.integrations.values())
            .filter(integration => integration.status === status);
    }

    private async initializeDiscordIntegration(integration: Integration): Promise<void> {
        if (integration.type !== IntegrationType.DISCORD) {
            throw new Error('Invalid integration type for Discord initialization');
        }

        const discordConfig = integration.config as DiscordConfig;

        // Validate required Discord configuration
        if (!discordConfig.botToken || !discordConfig.clientId || !discordConfig.clientSecret) {
            throw new Error('Missing required Discord configuration');
        }

        // Set up Discord-specific endpoints
        const baseUrl = 'https://discord.com/api/v10';
        discordConfig.endpoints = {
            messages: {
                path: '/channels/{channelId}/messages',
                method: 'POST',
                requiresAuth: true
            },
            channels: {
                path: '/channels/{channelId}',
                method: 'GET',
                requiresAuth: true
            },
            guilds: {
                path: '/guilds/{guildId}',
                method: 'GET',
                requiresAuth: true
            },
            threads: {
                path: '/channels/{channelId}/threads',
                method: 'POST',
                requiresAuth: true
            },
            reactions: {
                path: '/channels/{channelId}/messages/{messageId}/reactions/{emoji}/@me',
                method: 'PUT',
                requiresAuth: true
            }
        };

        // Set up event handlers
        discordConfig.eventHandlers = {
            messageCreate: true,
            messageUpdate: true,
            messageDelete: true,
            threadCreate: true,
            threadUpdate: true,
            reactionAdd: true,
            reactionRemove: true
        };

        // Update the integration with Discord configuration
        await this.updateIntegration(integration.id, {
            config: discordConfig,
            status: IntegrationStatus.CONFIGURED
        });

        // Broadcast Discord integration ready event
        await this.messageBus.broadcast({
            type: 'DISCORD_INTEGRATION_READY',
            content: { integrationId: integration.id },
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });
    }
}

interface RateLimitState {
    remaining: number;
    resetAt: Date;
} 