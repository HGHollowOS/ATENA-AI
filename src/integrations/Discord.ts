import { Client, GatewayIntentBits, Message, TextChannel, ChannelType } from 'discord.js';
import { Assistant } from '../core/Assistant';
import { Task, Priority, TaskCategory } from '../types';
import { CommandHandler } from '../services/CommandHandler';
import { DiscordService } from '../services/DiscordService';
import { ResearchAgent } from '../agents/ResearchAgent';
import { GoogleWorkspaceIntegration } from './GoogleWorkspace';
import { config } from '../config/config';

interface ProgressUpdate {
    taskId: string;
    stage: string;
    progress: number;
    estimatedTimeRemaining: number;
    details: string;
    channelId: string;
}

interface ConversationContext {
    lastMessages: Message[];
    activeTopics: Set<string>;
    lastBotInteraction: Date;
    quietModeUsers: Set<string>;
}

export class DiscordIntegration {
    private client: Client;
    private assistant: Assistant;
    private channels: Map<string, TextChannel>;
    private commandHandler: CommandHandler;
    private readonly prefix = '!atena';
    private customCommands: Map<string, (message: Message) => Promise<void>>;
    private discordService: DiscordService;
    private loggingChannel: TextChannel | null = null;
    private readonly ADMIN_USERNAME = 'howdyhakuna';

    // New properties for enhanced behavior
    private conversationContext: Map<string, ConversationContext> = new Map();
    private activeResearchTasks: Map<string, string> = new Map(); // Maps message ID to research ID
    private readonly CONTEXT_WINDOW_SIZE = 10; // Number of messages to keep for context
    private readonly INTERACTION_COOLDOWN = 5 * 60 * 1000; // 5 minutes between unprompted interactions

    private researchAgent: ResearchAgent;
    private googleWorkspace: GoogleWorkspaceIntegration;

    constructor(token: string, assistant: Assistant, googleWorkspace: GoogleWorkspaceIntegration) {
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent,
                GatewayIntentBits.GuildMessageReactions,
                GatewayIntentBits.DirectMessages,
                GatewayIntentBits.GuildMembers
            ]
        });
        this.assistant = assistant;
        this.channels = new Map();
        this.commandHandler = CommandHandler.getInstance();
        this.customCommands = new Map();
        this.discordService = DiscordService.getInstance();
        this.discordService.setClient(this.client);
        this.googleWorkspace = googleWorkspace;

        // Initialize the research agent with OpenAI API key
        this.researchAgent = new ResearchAgent(
            process.env.OPENAI_API_KEY || '',
            this.assistant,
            this.googleWorkspace
        );

        this.setupEventHandlers();
        this.start(token).catch(console.error);
    }

    private setupEventHandlers(): void {
        this.client.on('ready', async () => {
            console.log(`Logged in as ${this.client.user?.tag}`);
            await this.setupLoggingChannel();
        });

        this.client.on('messageCreate', async (message: Message) => {
            if (message.author.bot) return;

            // Update conversation context
            await this.updateConversationContext(message);

            // Handle explicit commands
            if (message.content.startsWith(this.prefix)) {
                await this.handleExplicitCommand(message);
                return;
            }

            // Check if user is in quiet mode
            const context = this.getChannelContext(message.channelId);
            if (context.quietModeUsers.has(message.author.id)) {
                return;
            }

            // Monitor conversation and intervene only when appropriate
            await this.monitorAndRespond(message);
        });

        this.client.on('error', async (error) => {
            console.error('Discord client error:', error);
            await this.logToChannel(`Discord client error: ${error}`);
        });
    }

    private async updateConversationContext(message: Message): Promise<void> {
        const channelId = message.channelId;
        let context = this.conversationContext.get(channelId);

        if (!context) {
            context = {
                lastMessages: [],
                activeTopics: new Set(),
                lastBotInteraction: new Date(0),
                quietModeUsers: new Set()
            };
            this.conversationContext.set(channelId, context);
        }

        // Update message history
        context.lastMessages.push(message);
        if (context.lastMessages.length > this.CONTEXT_WINDOW_SIZE) {
            context.lastMessages.shift();
        }

        // Extract and update active topics
        const newTopics = await this.extractTopics(message.content);
        newTopics.forEach(topic => context.activeTopics.add(topic));
    }

    private async monitorAndRespond(message: Message): Promise<void> {
        const context = this.getChannelContext(message.channelId);

        // Check if enough time has passed since last interaction
        const timeSinceLastInteraction = Date.now() - context.lastBotInteraction.getTime();
        if (timeSinceLastInteraction < this.INTERACTION_COOLDOWN) {
            return;
        }

        // Analyze if intervention is needed
        const shouldIntervene = await this.shouldIntervene(message, context);
        if (shouldIntervene) {
            await this.respondToContext(message, context);
            context.lastBotInteraction = new Date();
        }
    }

    private async shouldIntervene(message: Message, context: ConversationContext): Promise<boolean> {
        // Check for explicit help requests
        if (message.content.toLowerCase().includes('help') ||
            message.content.toLowerCase().includes('anyone know') ||
            message.content.toLowerCase().includes('how to')) {
            return true;
        }

        // Check for research-related keywords
        if (message.content.toLowerCase().includes('research') ||
            message.content.toLowerCase().includes('analyze') ||
            message.content.toLowerCase().includes('investigate')) {
            return true;
        }

        // Don't intervene in active discussions unless explicitly requested
        const recentMessages = context.lastMessages.slice(-3);
        if (recentMessages.length >= 3 &&
            new Set(recentMessages.map(m => m.author.id)).size > 1) {
            return false;
        }

        return false;
    }

    private async respondToContext(message: Message, context: ConversationContext): Promise<void> {
        try {
            // Analyze the conversation context
            const recentMessages = context.lastMessages.slice(-3);
            const messageContent = message.content.toLowerCase();

            // Handle research requests
            if (messageContent.includes('research') || messageContent.includes('analyze')) {
                const researchId = `research-${Date.now()}`;
                this.activeResearchTasks.set(message.id, researchId);

                await message.reply({
                    embeds: [{
                        title: '🔍 Research Request Acknowledged',
                        description: 'I\'ll help you research this topic. I\'ll keep you updated on my progress.',
                        color: 0x3498db
                    }]
                });

                // Start the research process
                try {
                    const thread = await this.researchAgent.startResearch(message, researchId);
                    console.log(`Created research thread: ${thread.id} for research ID: ${researchId}`);
                } catch (error) {
                    console.error('Error starting research:', error);
                    await message.reply(`Error starting research: ${error instanceof Error ? error.message : String(error)}`);
                }
                return;
            }

            // Handle help requests
            if (messageContent.includes('help') || messageContent.includes('how to')) {
                const topic = messageContent.replace(/help|how to/g, '').trim();
                await message.reply({
                    embeds: [{
                        title: '💡 Help Request',
                        description: `I noticed you're asking about ${topic}. Would you like me to:\n\n1. Provide a quick explanation\n2. Do detailed research\n3. Share relevant documentation\n\nReact with the corresponding number to choose.`,
                        color: 0x2ecc71
                    }]
                });
                return;
            }

            // Handle status inquiries
            if (messageContent.includes('status') || messageContent.includes('progress')) {
                const activeResearchIds = Array.from(this.activeResearchTasks.values());

                if (activeResearchIds.length > 0) {
                    const statusMessages = [];

                    for (const researchId of activeResearchIds) {
                        const status = this.researchAgent.getResearchStatus(researchId);
                        if (status) {
                            const progressPercent = Math.round(status.progress * 100);
                            statusMessages.push(`**${status.stage}** (${progressPercent}%)\n${status.details}`);
                        }
                    }

                    if (statusMessages.length > 0) {
                        await message.reply({
                            embeds: [{
                                title: '📊 Current Research Progress',
                                description: statusMessages.join('\n\n'),
                                color: 0x3498db
                            }]
                        });
                    } else {
                        await message.reply('No active research tasks with status information available.');
                    }
                } else {
                    await message.reply('No active research tasks.');
                }
                return;
            }
        } catch (error) {
            console.error('Error responding to context:', error);
            await this.logToChannel(`Error responding to context: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    private async startResearchTask(taskId: string, message: Message): Promise<void> {
        try {
            const thread = await message.startThread({
                name: `Research: ${message.content.slice(15, 50)}...`.trim(),
                autoArchiveDuration: 60
            });

            const sendUpdate = async (update: string) => {
                await thread.send({
                    embeds: [{
                        description: update,
                        color: 0x3498db
                    }]
                });
            };

            await sendUpdate('🔍 Initializing research process...');

            // Context Collection Phase
            await sendUpdate('📥 Collecting conversation context...');
            const messages = await message.channel.messages.fetch({ limit: 50 });
            const conversationHistory = Array.from(messages.values())
                .reverse()
                .map(m => ({
                    author: m.author.username,
                    content: m.content,
                    timestamp: m.createdAt
                }));

            // Participant Analysis
            await sendUpdate('👥 Analyzing conversation participants...');
            const participants = new Set(conversationHistory.map(m => m.author));
            await sendUpdate(`Found ${participants.size} participants in the conversation`);

            // Timeline Analysis
            await sendUpdate('📊 Analyzing conversation timeline...');
            const timespan = this.formatTimeSpan(
                conversationHistory[0].timestamp,
                conversationHistory[conversationHistory.length - 1].timestamp
            );
            await sendUpdate(`Conversation spans ${timespan}`);

            // Topic Extraction
            await sendUpdate('🔎 Extracting key topics and themes...');
            const topics = await this.extractTopics(
                conversationHistory.map(m => m.content).join(' ')
            );
            await sendUpdate(`📌 Identified ${topics.length} key topics:\n• ${topics.slice(0, 3).join('\n• ')}`);

            // Content Analysis
            await sendUpdate('📝 Performing detailed content analysis...');
            const contentStats = this.analyzeContent(conversationHistory);
            await sendUpdate(
                '📊 Content Overview:\n' +
                `• Average message length: ${contentStats.avgLength} characters\n` +
                `• Questions asked: ${contentStats.questions}\n` +
                `• Code blocks: ${contentStats.codeBlocks}\n` +
                `• Links shared: ${contentStats.links}`
            );

            // Sentiment Analysis
            await sendUpdate('🎭 Analyzing conversation sentiment...');
            const sentiment = await this.assistant.analyzeSentiment(conversationHistory);
            await sendUpdate(`Conversation tone: ${sentiment.overall}`);

            // Pattern Recognition
            await sendUpdate('🧩 Identifying conversation patterns...');
            const patterns = this.findConversationPatterns(conversationHistory);
            await sendUpdate(
                '🔄 Conversation Flow:\n' +
                patterns.map(p => `• ${p}`).join('\n')
            );

            // AI Summary Generation
            await sendUpdate('🧠 Generating comprehensive analysis...');
            const summary = await this.assistant.generateResearchSummary({
                topics,
                conversationHistory,
                requestedTopic: message.content.replace('!atena research', '').trim(),
                sentiment,
                patterns
            });

            // Recommendations
            await sendUpdate('💡 Generating insights and recommendations...');
            const recommendations = await this.assistant.generateRecommendations({
                topics,
                patterns,
                sentiment
            });

            // Final Report
            const finalReport = await thread.send({
                embeds: [{
                    title: '📑 Research Results',
                    description: summary.slice(0, 2048),
                    fields: [
                        {
                            name: '🎯 Main Topics',
                            value: topics.slice(0, 5).join('\n'),
                            inline: true
                        },
                        {
                            name: '📈 Conversation Stats',
                            value: [
                                `• ${conversationHistory.length} messages`,
                                `• ${participants.size} participants`,
                                `• ${timespan} duration`,
                                `• ${contentStats.codeBlocks} code examples`
                            ].join('\n'),
                            inline: true
                        },
                        {
                            name: '💡 Key Insights',
                            value: recommendations.slice(0, 3).join('\n'),
                            inline: false
                        }
                    ],
                    color: 0x00ff00,
                    footer: {
                        text: 'React with 📊 for detailed stats, 📝 for raw data, or 📈 for trends'
                    }
                }]
            });

            // Add reaction options for different views
            await finalReport.react('📊');
            await finalReport.react('📝');
            await finalReport.react('📈');

        } catch (error) {
            console.error('Error in research task:', error);
            if (error instanceof Error) {
                await message.reply({
                    content: `❌ Error during research: ${error.message}. Please try again.`,
                    allowedMentions: { repliedUser: true }
                });
            }
        }
    }

    private analyzeContent(history: Array<{ content: string }>): {
        avgLength: number;
        questions: number;
        codeBlocks: number;
        links: number;
    } {
        const stats = {
            avgLength: 0,
            questions: 0,
            codeBlocks: 0,
            links: 0
        };

        history.forEach(msg => {
            stats.avgLength += msg.content.length;
            stats.questions += (msg.content.match(/\?/g) || []).length;
            stats.codeBlocks += (msg.content.match(/```/g) || []).length / 2;
            stats.links += (msg.content.match(/https?:\/\/[^\s]+/g) || []).length;
        });

        stats.avgLength = Math.round(stats.avgLength / history.length);
        return stats;
    }

    private findConversationPatterns(history: Array<{ content: string; author: string }>): string[] {
        const patterns: string[] = [];

        // Find question-answer pairs
        let questionCount = 0;
        history.forEach((msg, i) => {
            if (msg.content.includes('?') && history[i + 1]) {
                questionCount++;
            }
        });
        if (questionCount > 0) {
            patterns.push(`${questionCount} question-answer exchanges`);
        }

        // Find code discussion patterns
        const codeDiscussions = history.filter(m => m.content.includes('```')).length;
        if (codeDiscussions > 0) {
            patterns.push(`${codeDiscussions} code-related discussions`);
        }

        // Find topic shifts
        let topicShifts = 0;
        let currentTopic = '';
        history.forEach(msg => {
            const newTopic = this.extractMainTopic(msg.content);
            if (newTopic && newTopic !== currentTopic) {
                topicShifts++;
                currentTopic = newTopic;
            }
        });
        if (topicShifts > 0) {
            patterns.push(`${topicShifts} topic transitions`);
        }

        return patterns;
    }

    private extractMainTopic(content: string): string {
        // Simple topic extraction based on keyword frequency
        const words = content.toLowerCase().split(/\W+/);
        const wordFreq: Record<string, number> = {};
        words.forEach(word => {
            if (word.length > 4) { // Only consider words longer than 4 characters
                wordFreq[word] = (wordFreq[word] || 0) + 1;
            }
        });
        return Object.entries(wordFreq)
            .sort(([, a], [, b]) => b - a)[0]?.[0] || '';
    }

    private async extractTopics(content: string): Promise<string[]> {
        try {
            // Remove common words and punctuation
            const cleanContent = content.toLowerCase()
                .replace(/[^\w\s]/g, '')
                .replace(/\s+/g, ' ')
                .trim();

            // Split into words
            const words = cleanContent.split(' ');

            // Extract potential topics (words or phrases that might be significant)
            const topics = new Set<string>();

            // Look for technical terms, product names, or concepts
            const technicalTerms = words.filter(word =>
                word.length > 3 && // Ignore short words
                !['the', 'and', 'for', 'that', 'this', 'with', 'from'].includes(word) // Ignore common words
            );

            // Look for phrases (2-3 words together that might form a concept)
            for (let i = 0; i < words.length - 1; i++) {
                const phrase = words.slice(i, i + 2).join(' ');
                if (phrase.length > 10) { // Only consider meaningful phrases
                    topics.add(phrase);
                }
            }

            // Add individual technical terms
            technicalTerms.forEach(term => topics.add(term));

            // Convert Set to Array and return
            return Array.from(topics);
        } catch (error) {
            console.error('Error extracting topics:', error);
            return [];
        }
    }

    private async setupLoggingChannel(): Promise<void> {
        try {
            // Try to find existing logging channel
            const guild = this.client.guilds.cache.first();
            if (!guild) return;

            let channel = guild.channels.cache.find(ch => ch.name === 'atena-logs');

            if (!channel) {
                // Create the logging channel if it doesn't exist
                channel = await guild.channels.create({
                    name: 'atena-logs',
                    type: ChannelType.GuildText,
                    topic: 'ATENA AI System Logs and Updates'
                });
                await this.discordService.logToChannel('Logging channel created and initialized.');
            }

            this.loggingChannel = channel as TextChannel;
            this.discordService.setLoggingChannel(this.loggingChannel);
            await this.discordService.logToChannel('ATENA AI System initialized and connected.');
        } catch (error) {
            console.error('Error setting up logging channel:', error);
        }
    }

    public async logToChannel(message: string): Promise<void> {
        await this.discordService.logToChannel(message);
    }

    public async start(token: string): Promise<void> {
        try {
            await this.client.login(token);
        } catch (error) {
            console.error('Failed to start Discord integration:', error);
            throw error;
        }
    }

    public async stop(): Promise<void> {
        this.client.destroy();
    }

    private async handleExplicitCommand(message: Message): Promise<void> {
        try {
            const content = message.content.slice(this.prefix.length).trim();
            const args = content.split(' ');
            const command = args.shift()?.toLowerCase();

            // Log the command
            console.log(`Received command: ${command} with args: ${args.join(' ')}`);

            // Check for custom commands first
            if (command && this.customCommands.has(command)) {
                const handler = this.customCommands.get(command);
                if (handler) {
                    await handler(message);
                    return;
                }
            }

            switch (command) {
                case 'help':
                    await this.sendHelpMessage(message, args[0]);
                    break;
                case 'research':
                    await this.handleResearchCommand(message, args);
                    break;
                case 'status':
                    if (args[0] === 'research') {
                        await this.handleResearchStatusCommand(message);
                    } else {
                        await this.handleStatusCommand(message);
                    }
                    break;
                case 'task':
                    const taskAction = args[0]?.toLowerCase();
                    switch (taskAction) {
                        case 'create':
                            const taskDetails = args.slice(1).join(' ');
                            await this.createTask({
                                title: taskDetails,
                                description: '',
                                priority: Priority.MEDIUM,
                                category: TaskCategory.WORK
                            }, message.channel as TextChannel);
                            break;
                        case 'list':
                            await this.assistant.listTasks(message.channel as TextChannel);
                            break;
                        case 'update':
                            const taskId = args[1];
                            const status = args[2];
                            await this.assistant.updateTaskStatus(taskId, status, message.channel as TextChannel);
                            break;
                        default:
                            await message.reply('Invalid task command. Use `create`, `list`, or `update`.');
                    }
                    break;

                case 'meeting':
                    const meetingAction = args[0]?.toLowerCase();
                    switch (meetingAction) {
                        case 'schedule':
                            const meetingDetails = args.slice(1).join(' ');
                            // Parse meeting details and schedule
                            await this.scheduleMeeting({
                                title: meetingDetails,
                                description: '',
                                startTime: new Date(),
                                endTime: new Date(Date.now() + 3600000),
                                attendees: []
                            }, message.channel as TextChannel);
                            break;
                        case 'list':
                            await this.assistant.listMeetings(message.channel as TextChannel);
                            break;
                        default:
                            await message.reply('Invalid meeting command. Use `schedule` or `list`.');
                    }
                    break;

                case 'remind':
                    const reminderText = args.join(' ');
                    await this.sendReminder({
                        message: reminderText,
                        mentionUser: message.author.id
                    }, message.channel as TextChannel);
                    break;

                case 'quiet':
                    const isEnabled = !this.getChannelContext(message.channelId).quietModeUsers.has(message.author.id);
                    await this.toggleQuietMode(message.author.id, message.channelId, isEnabled);
                    break;

                case 'shutdown':
                    if (message.author.username === this.ADMIN_USERNAME) {
                        await this.logToChannel(`🔄 Shutdown command received from admin ${message.author.username}`);
                        await message.reply('Initiating shutdown sequence...');
                        await this.gracefulShutdown();
                    } else {
                        await message.reply('⛔ You do not have permission to use this command.');
                        await this.logToChannel(`❌ Unauthorized shutdown attempt from ${message.author.username}`);
                    }
                    break;

                case 'ping':
                    const latency = Math.round(this.client.ws.ping);
                    await message.reply(`Pong! Latency is ${latency}ms.`);
                    break;

                case 'test-services':
                    await this.testAllServices(message);
                    break;

                default:
                    await message.reply(`Unknown command: ${command}. Type \`${this.prefix} help\` for a list of commands.`);
            }
        } catch (error) {
            console.error('Error handling command:', error);
            await message.reply('An error occurred while processing your command.');
        }
    }

    /**
     * Handle the research command
     */
    private async handleResearchCommand(message: Message, args: string[]): Promise<void> {
        if (args.length === 0) {
            await message.reply('Please specify what you want me to research. For example: `!atena research this conversation`');
            return;
        }

        try {
            // Generate a unique ID for this research task
            const researchId = `research-${Date.now()}`;

            // Store the research task ID with the message ID
            this.activeResearchTasks.set(message.id, researchId);

            // Initial response to acknowledge the request
            await message.reply({
                embeds: [{
                    title: '🔍 Starting Research',
                    description: 'I\'m starting a comprehensive research task based on your request. This may take a few minutes to complete.',
                    color: 0x3498db
                }]
            });

            // Start the research process
            const thread = await this.researchAgent.startResearch(message, researchId);

            // Log the thread creation
            console.log(`Created research thread: ${thread.id} for research ID: ${researchId}`);

        } catch (error) {
            console.error('Error handling research command:', error);
            await message.reply({
                embeds: [{
                    title: '❌ Research Error',
                    description: `An error occurred while starting the research: ${error instanceof Error ? error.message : String(error)}`,
                    color: 0xff0000
                }]
            });
        }
    }

    /**
     * Handle the research status command
     */
    private async handleResearchStatusCommand(message: Message): Promise<void> {
        // Check if there's an active research task for this message
        const researchId = this.activeResearchTasks.get(message.reference?.messageId || '');

        // If no specific research task is referenced, show all active research tasks
        if (!researchId) {
            const activeResearchIds = Array.from(this.activeResearchTasks.values());

            if (activeResearchIds.length === 0) {
                await message.reply('No active research tasks found. Please start a research task first with `!atena research <topic>`');
                return;
            }

            const statusMessages = [];
            for (const id of activeResearchIds) {
                const status = this.researchAgent.getResearchStatus(id);
                if (status) {
                    const progressPercent = Math.round(status.progress * 100);
                    statusMessages.push(`**Research ID**: ${id}\n**Stage**: ${status.stage} (${progressPercent}%)\n**Details**: ${status.details}`);
                }
            }

            if (statusMessages.length > 0) {
                await message.reply({
                    embeds: [{
                        title: '📊 Active Research Tasks',
                        description: statusMessages.join('\n\n'),
                        color: 0x3498db
                    }]
                });
            } else {
                await message.reply('No active research tasks with status information available.');
            }
            return;
        }

        // Get the status of the specific research task
        const status = this.researchAgent.getResearchStatus(researchId);

        if (!status) {
            await message.reply('Research task not found or completed.');
            return;
        }

        // Calculate elapsed time
        const elapsedMs = Date.now() - status.startTime.getTime();
        const elapsedMinutes = Math.floor(elapsedMs / 60000);
        const elapsedSeconds = Math.floor((elapsedMs % 60000) / 1000);

        // Calculate estimated time remaining
        const remainingMs = Math.max(0, status.estimatedCompletion.getTime() - Date.now());
        const remainingMinutes = Math.floor(remainingMs / 60000);
        const remainingSeconds = Math.floor((remainingMs % 60000) / 1000);

        // Send status update
        await message.reply({
            embeds: [{
                title: `🔍 Research Status: ${status.stage}`,
                description: status.details,
                fields: [
                    {
                        name: 'Progress',
                        value: `${Math.round(status.progress * 100)}%`
                    },
                    {
                        name: 'Elapsed Time',
                        value: `${elapsedMinutes}m ${elapsedSeconds}s`
                    },
                    {
                        name: 'Estimated Time Remaining',
                        value: status.progress >= 1 ? 'Complete' : `~${remainingMinutes}m ${remainingSeconds}s`
                    }
                ],
                color: status.progress >= 1 ? 0x00ff00 : 0x3498db
            }]
        });
    }

    /**
     * Handle the status command
     */
    private async handleStatusCommand(message: Message): Promise<void> {
        await message.reply({
            embeds: [{
                title: 'System Status',
                description: 'All systems operational',
                color: 0x00ff00,
                fields: [
                    {
                        name: 'Bot Status',
                        value: '✅ Online'
                    },
                    {
                        name: 'Latency',
                        value: `${Math.round(this.client.ws.ping)}ms`
                    },
                    {
                        name: 'Uptime',
                        value: `${Math.round(this.client.uptime! / 1000 / 60)} minutes`
                    }
                ],
                timestamp: new Date().toISOString()
            }]
        });
    }

    private async sendHelpMessage(message: Message, specificCommand?: string): Promise<void> {
        try {
            if (specificCommand) {
                // Provide detailed help for a specific command
                switch (specificCommand.toLowerCase()) {
                    case 'research':
                        await message.reply({
                            embeds: [{
                                title: '🔍 Research Command Help',
                                description: 'The research command allows you to request comprehensive research on a topic.',
                                fields: [
                                    {
                                        name: 'Usage',
                                        value: '`!atena research <topic>`'
                                    },
                                    {
                                        name: 'Example',
                                        value: '`!atena research the impact of AI on software development`'
                                    },
                                    {
                                        name: 'Features',
                                        value: '• Creates a dedicated thread for updates\n• Analyzes conversation context\n• Performs multi-perspective research\n• Creates a comprehensive Google Doc with findings'
                                    }
                                ],
                                color: 0x3498db
                            }]
                        });
                        break;
                    case 'status':
                        await message.reply({
                            embeds: [{
                                title: '📊 Status Command Help',
                                description: 'Check the status of various services or tasks.',
                                fields: [
                                    {
                                        name: 'Usage',
                                        value: '`!atena status [service]`'
                                    },
                                    {
                                        name: 'Available Services',
                                        value: '• `research` - Check status of active research tasks\n• (no argument) - Check general system status'
                                    },
                                    {
                                        name: 'Example',
                                        value: '`!atena status research`'
                                    }
                                ],
                                color: 0x3498db
                            }]
                        });
                        break;
                    // Add other specific command help cases here
                    default:
                        await message.reply(`No detailed help available for command: ${specificCommand}`);
                }
                return;
            }

            // General help message
            await message.reply({
                embeds: [{
                    title: '🤖 ATENA AI Help',
                    description: 'Here are the available commands:',
                    fields: [
                        {
                            name: '🔍 Research',
                            value: '`!atena research <topic>` - Start a comprehensive research task\n`!atena status research` - Check status of active research tasks'
                        },
                        {
                            name: '📅 Tasks & Calendar',
                            value: '`!atena task <description>` - Create a new task\n`!atena meeting <details>` - Schedule a meeting'
                        },
                        {
                            name: '⚙️ System',
                            value: '`!atena status` - Check system status\n`!atena help [command]` - Get detailed help for a command'
                        },
                        {
                            name: '🧪 Test',
                            value: '`!atena test` - Test if the system is working correctly'
                        }
                    ],
                    color: 0x3498db,
                    footer: {
                        text: 'You can also mention me in a conversation for contextual assistance.'
                    }
                }]
            });
        } catch (error) {
            console.error('Error sending help message:', error);
            await message.reply('An error occurred while sending the help message.');
        }
    }

    private async handleActions(actions: Array<{
        type: string;
        data: any;
    }>, channel: TextChannel): Promise<void> {
        for (const action of actions) {
            await this.logToChannel(`Executing action: ${action.type}`);
            try {
                switch (action.type) {
                    case 'CREATE_TASK':
                        await this.createTask(action.data, channel);
                        break;
                    case 'SEND_REMINDER':
                        await this.sendReminder(action.data, channel);
                        break;
                    case 'SCHEDULE_MEETING':
                        await this.scheduleMeeting(action.data, channel);
                        break;
                    default:
                        console.warn('Unknown action type:', action.type);
                        await this.logToChannel(`Warning: Unknown action type: ${action.type}`);
                }
            } catch (error) {
                await this.logToChannel(`Error executing action ${action.type}: ${error}`);
            }
        }
    }

    // Task Management
    private async createTask(data: {
        title: string;
        description: string;
        priority: Priority;
        category: TaskCategory;
        dueDate?: Date;
    }, channel: TextChannel): Promise<void> {
        try {
            const task = await this.assistant.createTask(
                data.title,
                data.description,
                data.priority,
                data.category,
                data.dueDate
            );

            await this.sendTaskCreationConfirmation(task, channel);
        } catch (error) {
            console.error('Error creating task:', error);
            await channel.send('Failed to create task. Please try again.');
        }
    }

    private async sendTaskCreationConfirmation(task: Task, channel: TextChannel): Promise<void> {
        const embed = {
            color: this.getPriorityColor(task.priority),
            title: 'New Task Created',
            fields: [
                {
                    name: 'Title',
                    value: task.title
                },
                {
                    name: 'Description',
                    value: task.description
                },
                {
                    name: 'Priority',
                    value: task.priority
                },
                {
                    name: 'Category',
                    value: task.category
                },
                {
                    name: 'Due Date',
                    value: task.dueDate ? task.dueDate.toLocaleDateString() : 'Not set'
                }
            ],
            timestamp: new Date().toISOString()
        };

        await channel.send({ embeds: [embed] });
    }

    // Reminder Management
    private async sendReminder(data: {
        message: string;
        mentionUser?: string;
    }, channel: TextChannel): Promise<void> {
        try {
            const mention = data.mentionUser ? `<@${data.mentionUser}> ` : '';
            await channel.send(`${mention}🔔 **Reminder:** ${data.message}`);
        } catch (error) {
            console.error('Error sending reminder:', error);
        }
    }

    // Meeting Management
    private async scheduleMeeting(data: {
        title: string;
        description: string;
        startTime: Date;
        endTime: Date;
        attendees: string[];
    }, channel: TextChannel): Promise<void> {
        try {
            const meeting = await this.assistant.scheduleMeeting(
                data.title,
                data.description,
                data.startTime,
                data.endTime,
                data.attendees
            );

            const embed = {
                color: 0x0099ff,
                title: 'New Meeting Scheduled',
                fields: [
                    {
                        name: 'Title',
                        value: meeting.title
                    },
                    {
                        name: 'Description',
                        value: meeting.description
                    },
                    {
                        name: 'Start Time',
                        value: meeting.startTime.toLocaleString()
                    },
                    {
                        name: 'End Time',
                        value: meeting.endTime.toLocaleString()
                    },
                    {
                        name: 'Attendees',
                        value: meeting.attendees.join(', ')
                    }
                ],
                timestamp: new Date().toISOString()
            };

            await channel.send({ embeds: [embed] });
        } catch (error) {
            console.error('Error scheduling meeting:', error);
            await channel.send('Failed to schedule meeting. Please try again.');
        }
    }

    private async testAllServices(message: Message): Promise<void> {
        const statusEmbed = {
            color: 0x0099ff,
            title: 'Services Connection Test',
            description: 'Testing connection to all integrated services...',
            fields: [] as Array<{ name: string; value: string }>,
            timestamp: new Date().toISOString()
        };

        try {
            // Test Gmail
            const gmailStatus = await this.assistant.testGmailConnection();
            statusEmbed.fields.push({
                name: '📧 Gmail',
                value: gmailStatus ? '✅ Connected' : '❌ Not Connected'
            });

            // Test Calendar
            const calendarStatus = await this.assistant.testCalendarConnection();
            statusEmbed.fields.push({
                name: '📅 Calendar',
                value: calendarStatus ? '✅ Connected' : '❌ Not Connected'
            });

            // Test Google Drive & Docs
            const driveStatus = await this.assistant.testDriveConnection();
            statusEmbed.fields.push({
                name: '📁 Google Drive & Docs',
                value: driveStatus ? '✅ Connected' : '❌ Not Connected'
            });

            // Test LinkedIn
            const linkedInStatus = await this.assistant.testLinkedInConnection();
            statusEmbed.fields.push({
                name: '💼 LinkedIn',
                value: linkedInStatus ? '✅ Connected' : '❌ Not Connected'
            });

            // Test News API
            const newsStatus = await this.assistant.testNewsConnection();
            statusEmbed.fields.push({
                name: '📰 News API',
                value: newsStatus ? '✅ Connected' : '❌ Not Connected'
            });

        } catch (error) {
            console.error('Error testing services:', error);
            statusEmbed.fields.push({
                name: '❌ Error',
                value: 'Failed to test services. Check console for details.'
            });
        }

        await message.reply({ embeds: [statusEmbed] });
    }

    // Utility Methods
    private getPriorityColor(priority: Priority): number {
        switch (priority) {
            case Priority.URGENT:
                return 0xff0000; // Red
            case Priority.HIGH:
                return 0xff9900; // Orange
            case Priority.MEDIUM:
                return 0xffff00; // Yellow
            case Priority.LOW:
                return 0x00ff00; // Green
            default:
                return 0x808080; // Gray
        }
    }

    // Public Methods
    async sendMessage(channelId: string, message: string): Promise<void> {
        const channel = await this.getChannel(channelId);
        if (channel) {
            await channel.send(message);
        }
    }

    private async getChannel(channelId: string): Promise<TextChannel | null> {
        if (this.channels.has(channelId)) {
            return this.channels.get(channelId) || null;
        }

        try {
            const channel = await this.client.channels.fetch(channelId);
            if (channel && channel.isTextBased() && !channel.isDMBased()) {
                this.channels.set(channelId, channel as TextChannel);
                return channel as TextChannel;
            }
        } catch (error) {
            console.error('Error fetching channel:', error);
        }

        return null;
    }

    public addCommand(name: string, handler: (message: Message) => Promise<void>): void {
        this.customCommands.set(name, handler);
    }

    private async gracefulShutdown(): Promise<void> {
        try {
            // Log shutdown initiation
            await this.logToChannel('🔄 Initiating graceful shutdown sequence...');

            // Cancel any pending operations
            if (this.assistant) {
                await this.logToChannel('📝 Saving current state...');
                // Add any cleanup needed for the assistant
            }

            // Log final message
            await this.logToChannel('👋 Goodbye! ATENA AI shutting down...');

            // Small delay to ensure final messages are sent
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Destroy the client connection
            this.client.destroy();

            // Exit the process
            process.exit(0);
        } catch (error) {
            console.error('Error during shutdown:', error);
            await this.logToChannel('❌ Error during shutdown process');
            process.exit(1);
        }
    }

    private getChannelContext(channelId: string): ConversationContext {
        let context = this.conversationContext.get(channelId);
        if (!context) {
            context = {
                lastMessages: [],
                activeTopics: new Set(),
                lastBotInteraction: new Date(0),
                quietModeUsers: new Set()
            };
            this.conversationContext.set(channelId, context);
        }
        return context;
    }

    public async toggleQuietMode(userId: string, channelId: string, enabled: boolean): Promise<void> {
        const context = this.getChannelContext(channelId);
        if (enabled) {
            context.quietModeUsers.add(userId);
        } else {
            context.quietModeUsers.delete(userId);
        }

        const channel = await this.getChannel(channelId);
        if (channel) {
            await channel.send({
                embeds: [{
                    title: enabled ? '🤫 Quiet Mode Enabled' : '🔊 Quiet Mode Disabled',
                    description: `I'll ${enabled ? 'only respond when directly addressed' : 'resume normal monitoring'} for <@${userId}>.`,
                    color: enabled ? 0x95a5a6 : 0x2ecc71
                }]
            });
        }
    }

    private createProgressBar(progress: number): string {
        const barLength = 20;
        const filledLength = Math.round(progress * barLength);
        const emptyLength = barLength - filledLength;
        return '█'.repeat(filledLength) + '░'.repeat(emptyLength) + ` ${Math.round(progress * 100)}%`;
    }

    private formatTimeSpan(start: Date, end: Date): string {
        const diff = Math.abs(end.getTime() - start.getTime());
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes} minutes`;
    }

    /**
     * Add a custom command to the Discord bot
     * @param commandName The name of the command (without prefix)
     * @param handler The function to handle the command
     */
    public addCustomCommand(commandName: string, handler: (message: Message) => Promise<void>): void {
        this.customCommands.set(commandName, handler);
        console.log(`Added custom command: ${commandName}`);
    }
} 