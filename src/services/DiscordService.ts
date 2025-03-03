import { Client, GatewayIntentBits, Message, ThreadChannel, TextChannel, NewsChannel, ThreadAutoArchiveDuration, CategoryChannel, ChannelType, PermissionFlagsBits, Role, GuildMember, Collection, Guild } from 'discord.js';
import { MessageBus } from '../core/MessageBus';
import { AgentMessage, AgentPriority } from '../core/types/Agent';
import { discordConfig } from '../config/discord.config';

interface ServerStats {
    messageCount: number;
    activeUsers: Set<string>;
    commandUsage: Map<string, number>;
    responseRatings: Map<string, number>;
    threadActivity: Map<string, {
        messageCount: number;
        lastActive: Date;
        participants: Set<string>;
    }>;
}

interface ChannelActivity {
    messageCount: number;
    uniqueUsers: Set<string>;
    lastMessage: Date;
    trending: boolean;
}

export class DiscordService {
    private static instance: DiscordService;
    private client: Client;
    private messageBus: MessageBus;
    private isReady: boolean = false;
    private serverStats: Map<string, ServerStats> = new Map();
    private channelActivity: Map<string, ChannelActivity> = new Map();
    private healthCheckInterval: NodeJS.Timeout | null = null;
    private readonly ALERT_THRESHOLD = 10; // Messages per minute for trending
    private readonly HEALTH_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes
    private loggingChannel: TextChannel | null = null;
    private activeResearchTasks: Map<string, {
        taskId: string;
        topic: string;
        threadId: string;
        userId: string;
        channelId: string;
        stage: string;
        progress: number;
        estimatedTimeRemaining: number;
        details: string;
    }> = new Map();

    private constructor() {
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent,
                GatewayIntentBits.GuildMessageReactions
            ]
        });
        this.messageBus = MessageBus.getInstance();
        this.setupEventHandlers();
    }

    public static getInstance(): DiscordService {
        if (!DiscordService.instance) {
            DiscordService.instance = new DiscordService();
        }
        return DiscordService.instance;
    }

    public async initialize(): Promise<void> {
        try {
            await this.client.login(discordConfig.botToken);
            console.log('Discord bot initialized successfully');
            this.isReady = true;
        } catch (error) {
            console.error('Failed to initialize Discord bot:', error);
            throw error;
        }
    }

    private setupEventHandlers(): void {
        this.client.on('ready', () => {
            console.log(`Logged in as ${this.client.user?.tag}`);
        });

        this.client.on('messageCreate', async (message: Message) => {
            if (message.author.bot) return;

            // Update activity metrics
            this.updateActivityMetrics(message);

            // Check for trending topics
            await this.checkForTrendingTopics(message);

            // Process feedback and commands
            if (message.content.startsWith('!feedback')) {
                await this.handleFeedback(message);
            }

            // Log command usage
            if (message.content.startsWith('!')) {
                this.logCommandUsage(message.content.split(' ')[0]);
            }

            // Broadcast message to the message bus
            await this.messageBus.broadcast({
                type: 'DISCORD_MESSAGE_RECEIVED',
                content: {
                    messageId: message.id,
                    channelId: message.channelId,
                    guildId: message.guildId,
                    content: message.content,
                    author: {
                        id: message.author.id,
                        username: message.author.username
                    },
                    timestamp: message.createdTimestamp,
                    attachments: Array.from(message.attachments.values()),
                    mentions: {
                        users: Array.from(message.mentions.users.values()),
                        roles: Array.from(message.mentions.roles.values())
                    }
                },
                priority: AgentPriority.HIGH,
                sender: 'discord_service'
            });
        });

        this.client.on('threadCreate', async (thread: ThreadChannel) => {
            await this.messageBus.broadcast({
                type: 'DISCORD_THREAD_CREATED',
                content: {
                    threadId: thread.id,
                    channelId: thread.parentId,
                    guildId: thread.guildId,
                    name: thread.name,
                    createdTimestamp: thread.createdTimestamp
                },
                priority: AgentPriority.MEDIUM,
                sender: 'discord_service'
            });
        });

        // Start health monitoring
        this.startHealthMonitoring();
    }

    private async updateActivityMetrics(message: Message): Promise<void> {
        const guildId = message.guildId!;
        const channelId = message.channelId;

        // Update server stats
        if (!this.serverStats.has(guildId)) {
            this.serverStats.set(guildId, {
                messageCount: 0,
                activeUsers: new Set(),
                commandUsage: new Map(),
                responseRatings: new Map(),
                threadActivity: new Map()
            });
        }

        const stats = this.serverStats.get(guildId)!;
        stats.messageCount++;
        stats.activeUsers.add(message.author.id);

        // Update channel activity
        if (!this.channelActivity.has(channelId)) {
            this.channelActivity.set(channelId, {
                messageCount: 0,
                uniqueUsers: new Set(),
                lastMessage: new Date(),
                trending: false
            });
        }

        const activity = this.channelActivity.get(channelId)!;
        activity.messageCount++;
        activity.uniqueUsers.add(message.author.id);
        activity.lastMessage = new Date();
    }

    private async checkForTrendingTopics(message: Message): Promise<void> {
        const activity = this.channelActivity.get(message.channelId);
        if (!activity) return;

        const messagesLastMinute = activity.messageCount;
        if (messagesLastMinute > this.ALERT_THRESHOLD && !activity.trending) {
            activity.trending = true;
            await this.messageBus.broadcast({
                type: 'DISCORD_TRENDING_TOPIC',
                content: {
                    channelId: message.channelId,
                    guildId: message.guildId,
                    messageCount: messagesLastMinute,
                    uniqueUsers: activity.uniqueUsers.size
                },
                priority: AgentPriority.HIGH,
                sender: 'discord_service'
            });
        }
    }

    private startHealthMonitoring(): void {
        this.healthCheckInterval = setInterval(() => {
            this.performHealthCheck();
        }, this.HEALTH_CHECK_INTERVAL);
    }

    private async performHealthCheck(): Promise<void> {
        const metrics = {
            totalServers: this.client.guilds.cache.size,
            totalUsers: this.client.users.cache.size,
            messageLatency: this.client.ws.ping,
            activeConnections: this.client.ws.shards.size
        };

        await this.messageBus.broadcast({
            type: 'DISCORD_HEALTH_CHECK',
            content: metrics,
            priority: AgentPriority.MEDIUM,
            sender: 'discord_service'
        });
    }

    public async sendMessage(channelId: string, content: string): Promise<void> {
        if (!this.isReady) {
            throw new Error('Discord service not initialized');
        }

        try {
            const channel = await this.client.channels.fetch(channelId);
            if (channel instanceof TextChannel || channel instanceof NewsChannel) {
                await channel.send(content);
            } else {
                throw new Error('Channel type not supported for sending messages');
            }
        } catch (error) {
            console.error('Failed to send Discord message:', error);
            throw error;
        }
    }

    public async createThread(channelId: string, name: string, message: string): Promise<string> {
        if (!this.isReady) {
            throw new Error('Discord service not initialized');
        }

        try {
            const channel = await this.client.channels.fetch(channelId);
            if (channel instanceof TextChannel || channel instanceof NewsChannel) {
                // First send the message
                const sentMessage = await channel.send(message);

                // Then create a thread from the message
                const thread = await sentMessage.startThread({
                    name: name,
                    autoArchiveDuration: ThreadAutoArchiveDuration.OneDay
                });

                return thread.id;
            } else {
                throw new Error('Channel type not supported for creating threads');
            }
        } catch (error) {
            console.error('Failed to create Discord thread:', error);
            throw error;
        }
    }

    public async addReaction(channelId: string, messageId: string, emoji: string): Promise<void> {
        if (!this.isReady) {
            throw new Error('Discord service not initialized');
        }

        try {
            const channel = await this.client.channels.fetch(channelId);
            if (!channel?.isTextBased()) {
                throw new Error('Channel is not text-based');
            }

            const message = await channel.messages.fetch(messageId);
            await message.react(emoji);
        } catch (error) {
            console.error('Failed to add reaction:', error);
            throw error;
        }
    }

    public async getChannel(channelId: string) {
        if (!this.isReady) {
            throw new Error('Discord service not initialized');
        }

        try {
            return await this.client.channels.fetch(channelId);
        } catch (error) {
            console.error('Failed to fetch channel:', error);
            throw error;
        }
    }

    public async getGuild(guildId: string) {
        if (!this.isReady) {
            throw new Error('Discord service not initialized');
        }

        try {
            return await this.client.guilds.fetch(guildId);
        } catch (error) {
            console.error('Failed to fetch guild:', error);
            throw error;
        }
    }

    // Server Management Methods
    public async createCategory(guildId: string, name: string): Promise<CategoryChannel> {
        const guild = await this.client.guilds.fetch(guildId);
        return await guild.channels.create({
            name,
            type: ChannelType.GuildCategory
        });
    }

    public async createChannel(guildId: string, name: string, options: {
        type: ChannelType.GuildText | ChannelType.GuildNews;
        category?: string;
        topic?: string;
        nsfw?: boolean;
    }): Promise<TextChannel | NewsChannel> {
        const guild = await this.client.guilds.fetch(guildId);

        let parentId: string | null = null;
        if (options.category) {
            const category = guild.channels.cache.find(
                c => c.type === ChannelType.GuildCategory && c.name === options.category
            );
            if (category) {
                parentId = category.id;
            }
        }

        const channel = await guild.channels.create({
            name,
            type: options.type,
            topic: options.topic,
            nsfw: options.nsfw || false,
            parent: parentId || undefined
        });

        if (channel instanceof TextChannel || channel instanceof NewsChannel) {
            return channel;
        }
        throw new Error('Failed to create text or news channel');
    }

    public async restructureChannels(guildId: string, structure: {
        category: string;
        channels: Array<{
            name: string;
            type: ChannelType.GuildText | ChannelType.GuildNews;
            topic?: string;
        }>;
    }[]): Promise<void> {
        const guild = await this.client.guilds.fetch(guildId);

        for (const categoryData of structure) {
            const category = await this.createCategory(guildId, categoryData.category);

            for (const channelData of categoryData.channels) {
                await this.createChannel(guildId, channelData.name, {
                    type: channelData.type,
                    category: categoryData.category,
                    topic: channelData.topic
                });
            }
        }
    }

    public async mentionUsers(channelId: string, userIds: string[], message: string): Promise<void> {
        const mentions = userIds.map(id => `<@${id}>`).join(' ');
        await this.sendMessage(channelId, `${mentions} ${message}`);
    }

    public async createRoleAndAssign(guildId: string, roleName: string, userIds: string[]): Promise<void> {
        const guild = await this.client.guilds.fetch(guildId);

        let role = guild.roles.cache.find(r => r.name === roleName);
        if (!role) {
            role = await guild.roles.create({
                name: roleName,
                reason: 'Auto-created by ATENA AI'
            });
        }

        for (const userId of userIds) {
            const member = await guild.members.fetch(userId);
            await member.roles.add(role);
        }
    }

    // Analytics and Reporting Methods
    public async generateServerStats(guildId: string): Promise<ServerStats> {
        return this.serverStats.get(guildId) || {
            messageCount: 0,
            activeUsers: new Set(),
            commandUsage: new Map(),
            responseRatings: new Map(),
            threadActivity: new Map()
        };
    }

    public async summarizeThread(threadId: string): Promise<{
        summary: string;
        decisionPoints: string[];
        participants: string[];
    }> {
        const thread = await this.client.channels.fetch(threadId) as ThreadChannel;
        const messages = await thread.messages.fetch();

        // Process messages and generate summary
        // This is a placeholder - actual implementation would use NLP
        return {
            summary: "Thread summary placeholder",
            decisionPoints: ["Decision point placeholder"],
            participants: Array.from(messages.map(m => m.author.username))
        };
    }

    private async handleFeedback(message: Message): Promise<void> {
        const [_, rating, ...feedback] = message.content.split(' ');
        const numericRating = parseInt(rating);

        if (isNaN(numericRating) || numericRating < 1 || numericRating > 5) {
            await message.reply('Please provide a rating between 1 and 5!');
            return;
        }

        await this.messageBus.broadcast({
            type: 'DISCORD_FEEDBACK_RECEIVED',
            content: {
                rating: numericRating,
                feedback: feedback.join(' '),
                userId: message.author.id,
                channelId: message.channelId,
                timestamp: message.createdTimestamp
            },
            priority: AgentPriority.HIGH,
            sender: 'discord_service'
        });
    }

    private logCommandUsage(command: string): void {
        for (const stats of this.serverStats.values()) {
            const count = stats.commandUsage.get(command) || 0;
            stats.commandUsage.set(command, count + 1);
        }
    }

    public setClient(client: Client): void {
        this.client = client;
    }

    public setLoggingChannel(channel: TextChannel): void {
        this.loggingChannel = channel;
    }

    public async logToChannel(message: string): Promise<void> {
        try {
            if (this.loggingChannel) {
                const timestamp = new Date().toISOString();
                await this.loggingChannel.send(`\`${timestamp}\` ${message}`);
            }
            // Always log to console as well
            console.log(`[ATENA LOG] ${message}`);
        } catch (error) {
            console.error('Error logging to channel:', error);
        }
    }

    public async stop(): Promise<void> {
        if (this.client) {
            this.client.destroy();
        }
    }

    public getClient(): Client {
        return this.client;
    }

    public async startResearch(topic: string, message: Message): Promise<void> {
        try {
            // Create a research thread
            const thread = await this.createThread(
                message.channelId,
                `Research: ${topic}`,
                `Starting research on: ${topic}\nPlease wait while I gather information...`
            );

            // Create a unique task ID
            const taskId = `research-${Date.now()}`;

            // Initialize research task
            await this.messageBus.broadcast({
                type: 'RESEARCH_REQUESTED',
                content: {
                    taskId,
                    topic,
                    threadId: thread,
                    userId: message.author.id,
                    channelId: message.channelId
                },
                priority: AgentPriority.HIGH,
                sender: 'discord_service'
            });

            // Send initial progress message
            await this.showProgress(message.channelId, taskId);
        } catch (error) {
            console.error('Error starting research:', error);
            await message.reply('Failed to start research task. Please try again.');
        }
    }

    private createProgressBar(progress: number): string {
        const barLength = 20;
        const filledLength = Math.round(progress * barLength);
        const emptyLength = barLength - filledLength;
        return '█'.repeat(filledLength) + '░'.repeat(emptyLength) + ` ${Math.round(progress * 100)}%`;
    }

    public async showProgress(channelId: string, taskId?: string): Promise<void> {
        try {
            const channel = await this.getChannel(channelId);
            if (!channel || !(channel instanceof TextChannel)) {
                throw new Error('Channel not found or is not a text channel');
            }

            const activeTasks = Array.from(this.activeResearchTasks.values())
                .filter(task => !taskId || task.taskId === taskId)
                .filter(task => task.channelId === channelId);

            if (activeTasks.length === 0) {
                await channel.send({
                    embeds: [{
                        title: '📊 Task Progress',
                        description: taskId
                            ? 'No active task found with that ID.'
                            : 'No active tasks in this channel.',
                        color: 0x95a5a6
                    }]
                });
                return;
            }

            const progressUpdates = activeTasks.map(task => {
                const progressBar = this.createProgressBar(task.progress);
                return {
                    name: `Task: ${task.taskId}`,
                    value: `**Stage**: ${task.stage}\n${progressBar}\n${task.details}\nTime remaining: ${Math.ceil(task.estimatedTimeRemaining / 60)} minutes`
                };
            });

            await channel.send({
                embeds: [{
                    title: '📊 Active Research Tasks',
                    fields: progressUpdates,
                    color: 0x3498db,
                    timestamp: new Date().toISOString()
                }]
            });
        } catch (error) {
            console.error('Error showing progress:', error);
            throw error;
        }
    }

    public async toggleQuietMode(userId: string, channelId: string, enabled: boolean): Promise<void> {
        try {
            const channel = await this.getChannel(channelId);
            if (!channel || !(channel instanceof TextChannel)) {
                throw new Error('Channel not found or is not a text channel');
            }

            // Update quiet mode status
            await this.messageBus.broadcast({
                type: 'QUIET_MODE_TOGGLED',
                content: {
                    userId,
                    channelId,
                    enabled
                },
                priority: AgentPriority.MEDIUM,
                sender: 'discord_service'
            });

            // Send confirmation message
            await channel.send({
                embeds: [{
                    title: enabled ? '🤫 Quiet Mode Enabled' : '🔊 Quiet Mode Disabled',
                    description: `I'll ${enabled ? 'only respond when directly addressed' : 'resume normal monitoring'} for <@${userId}>.`,
                    color: enabled ? 0x95a5a6 : 0x2ecc71
                }]
            });
        } catch (error) {
            console.error('Error toggling quiet mode:', error);
            throw error;
        }
    }
} 