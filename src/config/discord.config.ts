import { DiscordConfig, IntegrationType, CredentialType } from '../agents/IntegrationAgent';

export const discordConfig: DiscordConfig = {
    botToken: process.env.DISCORD_BOT_TOKEN || '',
    clientId: process.env.DISCORD_CLIENT_ID || '',
    clientSecret: process.env.DISCORD_CLIENT_SECRET || '',
    guildIds: (process.env.DISCORD_GUILD_IDS || '').split(','),
    permissions: [
        'READ_MESSAGES',
        'SEND_MESSAGES',
        'CREATE_PUBLIC_THREADS',
        'SEND_MESSAGES_IN_THREADS',
        'ADD_REACTIONS',
        'READ_MESSAGE_HISTORY'
    ],
    apiVersion: 'v10',
    baseUrl: 'https://discord.com/api/v10',
    endpoints: {
        messages: {
            path: '/channels/{channelId}/messages',
            method: 'POST',
            requiresAuth: true,
            rateLimit: {
                requests: 5,
                period: 5000 // 5 seconds
            }
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
    },
    eventHandlers: {
        messageCreate: true,
        messageUpdate: true,
        messageDelete: true,
        threadCreate: true,
        threadUpdate: true,
        reactionAdd: true,
        reactionRemove: true
    }
};

export const discordCredentials = {
    type: CredentialType.OAUTH2,
    data: {
        botToken: process.env.DISCORD_BOT_TOKEN || '',
        clientId: process.env.DISCORD_CLIENT_ID || '',
        clientSecret: process.env.DISCORD_CLIENT_SECRET || '',
    },
    scopes: [
        'bot',
        'messages.read',
        'guilds',
        'guild.messages.read',
        'guild.messages.write'
    ]
};

export const createDiscordIntegration = () => ({
    name: 'Discord Integration',
    type: IntegrationType.DISCORD,
    provider: 'Discord',
    config: discordConfig,
    credentials: discordCredentials,
    capabilities: [
        'message_management',
        'thread_management',
        'reaction_management',
        'guild_management'
    ],
    metadata: {
        description: 'Discord integration for ATENA AI system',
        version: '1.0.0'
    }
}); 