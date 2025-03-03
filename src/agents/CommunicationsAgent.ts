import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Communication {
    id: string;
    type: CommunicationType;
    channel: CommunicationChannel;
    sender: string;
    recipients: string[];
    subject?: string;
    content: string;
    attachments?: Attachment[];
    metadata: Record<string, any>;
    status: CommunicationStatus;
    priority: CommunicationPriority;
    timestamp: Date;
    scheduledFor?: Date;
    threadId?: string;
    replyTo?: string;
}

export interface Attachment {
    id: string;
    name: string;
    type: string;
    size: number;
    url?: string;
    content?: Buffer;
}

export enum CommunicationType {
    EMAIL = 'EMAIL',
    CHAT = 'CHAT',
    NOTIFICATION = 'NOTIFICATION',
    ANNOUNCEMENT = 'ANNOUNCEMENT'
}

export enum CommunicationChannel {
    GMAIL = 'GMAIL',
    DISCORD = 'DISCORD',
    SLACK = 'SLACK',
    TEAMS = 'TEAMS',
    SYSTEM = 'SYSTEM'
}

export enum CommunicationStatus {
    DRAFT = 'DRAFT',
    SCHEDULED = 'SCHEDULED',
    SENDING = 'SENDING',
    SENT = 'SENT',
    DELIVERED = 'DELIVERED',
    READ = 'READ',
    FAILED = 'FAILED'
}

export enum CommunicationPriority {
    LOW = 'LOW',
    NORMAL = 'NORMAL',
    HIGH = 'HIGH',
    URGENT = 'URGENT'
}

export class CommunicationsAgent extends BaseAgent {
    private communications: Map<string, Communication>;
    private messageBus: MessageBus;
    private channelHandlers: Map<CommunicationChannel, (comm: Communication) => Promise<void>>;

    constructor() {
        const config: AgentConfig = {
            id: 'communications',
            name: 'Communications Agent',
            description: 'Manages all communication channels and message handling',
            capabilities: [
                'email_management',
                'chat_integration',
                'notification_handling',
                'message_scheduling',
                'template_management',
                'communication_analytics'
            ],
            dependencies: []
        };

        super(config);
        this.communications = new Map();
        this.messageBus = MessageBus.getInstance();
        this.channelHandlers = new Map();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.setupChannelHandlers();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    private setupChannelHandlers(): void {
        this.channelHandlers.set(CommunicationChannel.GMAIL, this.handleEmailCommunication.bind(this));
        this.channelHandlers.set(CommunicationChannel.DISCORD, this.handleDiscordCommunication.bind(this));
        this.channelHandlers.set(CommunicationChannel.SLACK, this.handleSlackCommunication.bind(this));
        this.channelHandlers.set(CommunicationChannel.TEAMS, this.handleTeamsCommunication.bind(this));
        this.channelHandlers.set(CommunicationChannel.SYSTEM, this.handleSystemCommunication.bind(this));
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'SEND_COMMUNICATION':
                await this.sendCommunication(message.content);
                break;

            case 'SCHEDULE_COMMUNICATION':
                await this.scheduleCommunication(message.content);
                break;

            case 'CANCEL_COMMUNICATION':
                await this.cancelCommunication(message.content.communicationId);
                break;

            case 'GET_COMMUNICATION':
                await this.sendCommunicationDetails(message);
                break;

            case 'LIST_COMMUNICATIONS':
                await this.sendCommunicationsList(message);
                break;

            case 'UPDATE_COMMUNICATION':
                await this.updateCommunication(
                    message.content.communicationId,
                    message.content.updates
                );
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async sendCommunication(commData: Partial<Communication>): Promise<void> {
        const communication = await this.createCommunication(commData);

        try {
            const handler = this.channelHandlers.get(communication.channel);
            if (!handler) {
                throw new Error(`No handler found for channel: ${communication.channel}`);
            }

            await this.updateCommunicationStatus(
                communication.id,
                CommunicationStatus.SENDING
            );

            await handler(communication);

            await this.updateCommunicationStatus(
                communication.id,
                CommunicationStatus.SENT
            );

            await this.messageBus.broadcast({
                type: 'COMMUNICATION_SENT',
                content: { communication },
                priority: AgentPriority.MEDIUM,
                sender: this.config.id
            });
        } catch (error) {
            await this.updateCommunicationStatus(
                communication.id,
                CommunicationStatus.FAILED
            );
            throw error;
        }
    }

    private async scheduleCommunication(commData: Partial<Communication>): Promise<void> {
        if (!commData.scheduledFor) {
            throw new Error('scheduledFor is required for scheduling communication');
        }

        const communication = await this.createCommunication({
            ...commData,
            status: CommunicationStatus.SCHEDULED
        });

        const delay = (communication.scheduledFor as Date).getTime() - Date.now();
        if (delay > 0) {
            setTimeout(() => {
                this.sendCommunication(communication)
                    .catch(error => console.error('Failed to send scheduled communication:', error));
            }, delay);
        } else {
            await this.sendCommunication(communication);
        }
    }

    private async createCommunication(commData: Partial<Communication>): Promise<Communication> {
        const commId = this.generateCommunicationId();
        const now = new Date();

        const communication: Communication = {
            id: commId,
            type: commData.type || CommunicationType.EMAIL,
            channel: commData.channel || CommunicationChannel.SYSTEM,
            sender: commData.sender || 'system',
            recipients: commData.recipients || [],
            content: commData.content || '',
            metadata: commData.metadata || {},
            status: CommunicationStatus.DRAFT,
            priority: commData.priority || CommunicationPriority.NORMAL,
            timestamp: now,
            ...commData
        };

        this.communications.set(commId, communication);
        return communication;
    }

    private async updateCommunication(
        commId: string,
        updates: Partial<Communication>
    ): Promise<void> {
        const communication = this.communications.get(commId);
        if (!communication) {
            throw new Error(`Communication ${commId} not found`);
        }

        const updatedComm = {
            ...communication,
            ...updates,
            timestamp: new Date()
        };

        this.communications.set(commId, updatedComm);

        await this.messageBus.broadcast({
            type: 'COMMUNICATION_UPDATED',
            content: { communication: updatedComm },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateCommunicationStatus(
        commId: string,
        status: CommunicationStatus
    ): Promise<void> {
        await this.updateCommunication(commId, { status });
    }

    private async cancelCommunication(commId: string): Promise<void> {
        const communication = this.communications.get(commId);
        if (!communication) {
            throw new Error(`Communication ${commId} not found`);
        }

        if (communication.status === CommunicationStatus.SCHEDULED) {
            await this.updateCommunicationStatus(commId, CommunicationStatus.DRAFT);
        }
    }

    private async sendCommunicationDetails(message: AgentMessage): Promise<void> {
        const commId = message.content.communicationId;
        const communication = this.communications.get(commId);

        await this.messageBus.sendMessage({
            type: 'COMMUNICATION_DETAILS_RESPONSE',
            content: { communication },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendCommunicationsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let communications = Array.from(this.communications.values());

        // Apply filters
        if (filters.type) {
            communications = communications.filter(comm => comm.type === filters.type);
        }
        if (filters.channel) {
            communications = communications.filter(comm => comm.channel === filters.channel);
        }
        if (filters.status) {
            communications = communications.filter(comm => comm.status === filters.status);
        }
        if (filters.sender) {
            communications = communications.filter(comm => comm.sender === filters.sender);
        }

        await this.messageBus.sendMessage({
            type: 'COMMUNICATIONS_LIST_RESPONSE',
            content: { communications },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateCommunicationId(): string {
        return `comm-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    // Channel-specific handlers
    private async handleEmailCommunication(comm: Communication): Promise<void> {
        // TODO: Implement email sending logic using Gmail API
        console.log('Sending email:', comm);
    }

    private async handleDiscordCommunication(comm: Communication): Promise<void> {
        // TODO: Implement Discord message sending logic
        console.log('Sending Discord message:', comm);
    }

    private async handleSlackCommunication(comm: Communication): Promise<void> {
        // TODO: Implement Slack message sending logic
        console.log('Sending Slack message:', comm);
    }

    private async handleTeamsCommunication(comm: Communication): Promise<void> {
        // TODO: Implement Teams message sending logic
        console.log('Sending Teams message:', comm);
    }

    private async handleSystemCommunication(comm: Communication): Promise<void> {
        // Handle system notifications
        await this.messageBus.broadcast({
            type: 'SYSTEM_NOTIFICATION',
            content: comm,
            priority: comm.priority === CommunicationPriority.URGENT
                ? AgentPriority.HIGH
                : AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Communications Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getCommunicationCount(): number {
        return this.communications.size;
    }

    public getCommunicationsByType(type: CommunicationType): Communication[] {
        return Array.from(this.communications.values())
            .filter(comm => comm.type === type);
    }

    public getCommunicationsByStatus(status: CommunicationStatus): Communication[] {
        return Array.from(this.communications.values())
            .filter(comm => comm.status === status);
    }
} 