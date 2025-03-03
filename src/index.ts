import { Assistant } from './core/Assistant';
import { DiscordIntegration } from './integrations/Discord';
import { GoogleWorkspaceIntegration } from './integrations/GoogleWorkspace';
import { LinkedInIntegration } from './integrations/LinkedIn';
import { UserPreferences } from './types';
import { config } from './config/config';
import dotenv from 'dotenv';
import { Message } from 'discord.js';

// Load environment variables
dotenv.config();

// Initialize the application
async function main() {
    try {
        console.log('Starting ATENA AI...');

        // Initialize user preferences
        const userPreferences: UserPreferences = {
            workingHours: {
                start: '09:00',
                end: '17:00'
            },
            timezone: 'UTC',
            notificationPreferences: {
                email: true,
                discord: true,
                urgentOnly: false
            },
            autoResponders: {
                enabled: true,
                templates: {
                    outOfOffice: 'I am currently out of office and will respond to your message when I return.',
                    busy: 'I am currently in a meeting and will get back to you shortly.',
                    default: 'Thank you for your message. I will respond as soon as possible.'
                }
            },
            priorityThresholds: {
                urgent: 9,
                high: 7,
                medium: 4
            }
        };

        // Initialize Google Workspace integration
        const googleWorkspace = new GoogleWorkspaceIntegration({
            clientId: process.env.GOOGLE_CLIENT_ID || '',
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
            redirectUri: process.env.GOOGLE_REDIRECT_URI || '',
            refreshToken: process.env.GOOGLE_REFRESH_TOKEN || ''
        });
        console.log('Google Workspace integration initialized');

        // Initialize LinkedIn integration
        const linkedIn = new LinkedInIntegration(
            process.env.LINKEDIN_CLIENT_ID || '',
            process.env.LINKEDIN_CLIENT_SECRET || ''
        );
        console.log('LinkedIn integration initialized');

        // Initialize core assistant
        const assistant = new Assistant(
            process.env.OPENAI_API_KEY || '',
            userPreferences,
            googleWorkspace,
            linkedIn
        );
        await assistant.initialize();
        console.log('Assistant core initialized');

        // Initialize Discord integration
        const discordToken = process.env.DISCORD_TOKEN;
        if (!discordToken) {
            throw new Error('DISCORD_TOKEN environment variable is not set');
        }

        const discord = new DiscordIntegration(discordToken, assistant, googleWorkspace);
        console.log('Discord integration initialized');

        // Add test command to Discord
        discord.addCustomCommand('test', async (message: Message) => {
            await message.reply('Test command received! The system is working correctly.');
        });

        console.log('ATENA AI is now running');
    } catch (error) {
        console.error('Error starting ATENA AI:', error instanceof Error ? error.message : String(error));
        process.exit(1);
    }
}

// Error handling
process.on('uncaughtException', (error: Error) => {
    console.error('Uncaught Exception:', error);
    // Implement proper error logging and notification
});

process.on('unhandledRejection', (reason: unknown, promise: Promise<unknown>) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    // Implement proper error logging and notification
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('Received SIGTERM signal. Starting graceful shutdown...');
    try {
        // Implement cleanup logic here
        process.exit(0);
    } catch (error) {
        console.error('Error during shutdown:', error);
        process.exit(1);
    }
});

// Start the application
main().catch(error => {
    console.error('Unhandled error in main application:', error instanceof Error ? error.message : String(error));
    process.exit(1);
}); 