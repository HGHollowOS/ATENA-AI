import { Message, TextChannel, NewsChannel } from 'discord.js';
import { DiscordService } from './DiscordService';
import { MonitoringService } from './MonitoringService';
import { MessageBus } from '../core/MessageBus';
import { AgentMessage, AgentPriority } from '../core/types/Agent';

interface Command {
    name: string;
    description: string;
    usage: string;
    examples: string[];
    execute: (message: Message, args: string[]) => Promise<void>;
}

export class CommandHandler {
    private static instance: CommandHandler;
    private readonly prefix = '!atena';
    private commands: Map<string, Command> = new Map();
    private discordService: DiscordService;
    private monitoringService: MonitoringService;
    private messageBus: MessageBus;

    private constructor() {
        this.discordService = DiscordService.getInstance();
        this.monitoringService = MonitoringService.getInstance();
        this.messageBus = MessageBus.getInstance();
        this.registerCommands();
    }

    public static getInstance(): CommandHandler {
        if (!CommandHandler.instance) {
            CommandHandler.instance = new CommandHandler();
        }
        return CommandHandler.instance;
    }

    private registerCommands(): void {
        // System Commands
        this.commands.set('quiet', {
            name: 'quiet',
            description: 'Toggle quiet mode for the bot',
            usage: '!atena quiet [on/off]',
            examples: ['!atena quiet on', '!atena quiet off'],
            execute: async (message, args) => {
                const mode = args[0]?.toLowerCase();
                if (mode !== 'on' && mode !== 'off') {
                    await message.reply('Please specify either "on" or "off" for quiet mode.');
                    return;
                }
                await this.discordService.toggleQuietMode(message.author.id, message.channelId, mode === 'on');
            }
        });

        // Research Commands
        this.commands.set('research', {
            name: 'research',
            description: 'Start a research task with progress tracking',
            usage: '!atena research <topic>',
            examples: [
                '!atena research quantum computing in AI',
                '!atena research latest developments in LLMs'
            ],
            execute: async (message, args) => {
                const topic = args.join(' ');
                if (!topic) {
                    await message.reply('Please specify a topic to research.');
                    return;
                }
                await this.discordService.startResearch(topic, message);
            }
        });

        // Progress Tracking
        this.commands.set('progress', {
            name: 'progress',
            description: 'Check the progress of ongoing tasks',
            usage: '!atena progress [taskId]',
            examples: ['!atena progress', '!atena progress research-123'],
            execute: async (message, args) => {
                const taskId = args[0];
                await this.discordService.showProgress(message.channelId, taskId);
            }
        });

        // Admin Commands
        this.commands.set('shutdown', {
            name: 'shutdown',
            description: 'Safely shut down the bot (Admin only)',
            usage: '!atena shutdown',
            examples: ['!atena shutdown'],
            execute: async (message, args) => {
                const ADMIN_USERNAME = 'howdyhakuna';
                if (message.author.username === ADMIN_USERNAME) {
                    await this.discordService.logToChannel(`🔄 Shutdown command received from admin ${message.author.username}`);
                    await message.reply('Initiating shutdown sequence...');
                    await this.gracefulShutdown();
                } else {
                    await message.reply('⛔ You do not have permission to use this command.');
                    await this.discordService.logToChannel(`❌ Unauthorized shutdown attempt from ${message.author.username}`);
                }
            }
        });

        // Analytics and Insights Commands
        this.commands.set('trends', {
            name: 'trends',
            description: 'Show current trending topics and discussions',
            usage: '!atena trends [timeframe]',
            examples: [
                '!atena trends today',
                '!atena trends week'
            ],
            execute: async (message, args) => {
                const timeframe = args[0] || 'today';
                // Implementation will fetch trends from MonitoringService
                await message.reply('Analyzing trends...');
            }
        });

        // Channel Management Commands
        this.commands.set('organize', {
            name: 'organize',
            description: 'Suggest or implement channel organization',
            usage: '!atena organize [suggest/apply]',
            examples: [
                '!atena organize suggest',
                '!atena organize apply'
            ],
            execute: async (message, args) => {
                const action = args[0] || 'suggest';
                if (!message.guild) return;

                if (action === 'suggest') {
                    await message.reply('Analyzing channel activity and generating suggestions...');
                } else if (action === 'apply') {
                    await message.reply('Implementing recommended channel organization...');
                }
            }
        });

        // Summary and Digest Commands
        this.commands.set('summarize', {
            name: 'summarize',
            description: 'Summarize a thread or conversation',
            usage: '!atena summarize [thread/channel] [timeframe]',
            examples: [
                '!atena summarize thread',
                '!atena summarize channel 24h'
            ],
            execute: async (message, args) => {
                const target = args[0] || 'thread';
                const timeframe = args[1] || '24h';
                await message.reply('Generating summary...');
            }
        });

        // System Status Commands
        this.commands.set('status', {
            name: 'status',
            description: 'Show system status and health metrics',
            usage: '!atena status [component]',
            examples: [
                '!atena status',
                '!atena status agents'
            ],
            execute: async (message, args) => {
                const component = args[0];
                await message.reply('Fetching system status...');
            }
        });

        // Help and Documentation
        this.commands.set('help', {
            name: 'help',
            description: 'Show available commands and usage',
            usage: '!atena help [command]',
            examples: [
                '!atena help',
                '!atena help research'
            ],
            execute: async (message, args) => {
                const commandName = args[0];
                if (commandName) {
                    const command = this.commands.get(commandName);
                    if (command) {
                        await message.reply({
                            embeds: [{
                                title: `Command: ${command.name}`,
                                description: command.description,
                                fields: [
                                    { name: 'Usage', value: command.usage },
                                    { name: 'Examples', value: command.examples.join('\n') }
                                ]
                            }]
                        });
                        return;
                    }
                }

                const categories = {
                    'Getting Started': ['help', 'status', 'test'],
                    'Research & Analysis': ['research', 'progress'],
                    'System Controls': ['quiet', 'shutdown'],
                    'Analytics': ['trends', 'summarize'],
                    'Feedback': ['feedback']
                };

                const fields = Object.entries(categories).map(([category, commandNames]) => ({
                    name: category,
                    value: commandNames
                        .map(name => {
                            const cmd = this.commands.get(name);
                            return cmd ? `\`${this.prefix} ${cmd.name}\` - ${cmd.description}\n*Example: ${cmd.examples[0]}*` : '';
                        })
                        .filter(Boolean)
                        .join('\n\n')
                }));

                await message.reply({
                    embeds: [{
                        title: '🤖 ATENA AI - Command Guide',
                        description: `Welcome to ATENA AI! Here's how to use the available commands.\nUse \`${this.prefix} help <command>\` for detailed information about any command.`,
                        fields,
                        color: 0x3498db,
                        footer: {
                            text: 'Pro Tip: All commands start with !atena'
                        }
                    }]
                });
            }
        });

        // Feedback System
        this.commands.set('feedback', {
            name: 'feedback',
            description: 'Provide feedback or report issues',
            usage: '!atena feedback <rating> <comment>',
            examples: [
                '!atena feedback 5 Great research on quantum computing!',
                '!atena feedback 3 Could provide more detailed examples'
            ],
            execute: async (message, args) => {
                const [rating, ...feedback] = args;
                const numericRating = parseInt(rating);

                if (isNaN(numericRating) || numericRating < 1 || numericRating > 5) {
                    await message.reply('Please provide a rating between 1 and 5!');
                    return;
                }

                await this.messageBus.broadcast({
                    type: 'FEEDBACK_RECEIVED',
                    content: {
                        rating: numericRating,
                        feedback: feedback.join(' '),
                        userId: message.author.id,
                        channelId: message.channelId
                    },
                    priority: AgentPriority.HIGH,
                    sender: 'command_handler'
                });

                await message.reply('Thank you for your feedback!');
            }
        });
    }

    public async handleMessage(message: Message): Promise<void> {
        if (!message.content.startsWith(this.prefix) || message.author.bot) return;

        const args = message.content.slice(this.prefix.length).trim().split(/ +/);
        const commandName = args.shift()?.toLowerCase();

        if (!commandName) return;

        const command = this.commands.get(commandName);
        if (!command) {
            await message.reply({
                content: `Unknown command. Use \`${this.prefix} help\` to see available commands.`,
                allowedMentions: { repliedUser: true }
            });
            return;
        }

        try {
            await command.execute(message, args);
        } catch (error) {
            console.error('Error executing command:', error);
            await message.reply({
                content: 'There was an error executing that command! Please try again later.',
                allowedMentions: { repliedUser: true }
            });
        }
    }

    private createHelpEmbed(command?: Command): any {
        if (command) {
            return {
                embeds: [{
                    color: 0x0099ff,
                    title: `Command: ${command.name}`,
                    description: command.description,
                    fields: [
                        { name: 'Usage', value: command.usage },
                        { name: 'Examples', value: command.examples.join('\n') }
                    ]
                }]
            };
        }

        return {
            embeds: [{
                color: 0x0099ff,
                title: 'ATENA AI - Available Commands',
                description: 'Here are all available commands:',
                fields: Array.from(this.commands.values()).map(cmd => ({
                    name: cmd.name,
                    value: cmd.description
                })),
                footer: {
                    text: `Type ${this.prefix} help <command> for detailed information`
                }
            }]
        };
    }

    private async gracefulShutdown(): Promise<void> {
        try {
            // Log shutdown initiation
            await this.discordService.logToChannel('🔄 Initiating graceful shutdown sequence...');

            // Cancel any pending operations
            await this.discordService.logToChannel('📝 Saving current state...');

            // Log final message
            await this.discordService.logToChannel('👋 Goodbye! ATENA AI shutting down...');

            // Small delay to ensure final messages are sent
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Destroy the Discord client and exit
            await this.discordService.stop();
            process.exit(0);
        } catch (error) {
            console.error('Error during shutdown:', error);
            await this.discordService.logToChannel('❌ Error during shutdown process');
            process.exit(1);
        }
    }
} 