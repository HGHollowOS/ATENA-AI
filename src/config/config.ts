/**
 * Application configuration
 */
export const config = {
    // OpenAI API configuration
    openai: {
        apiKey: process.env.OPENAI_API_KEY || '',
        model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
        maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '4096', 10),
    },

    // Discord configuration
    discord: {
        token: process.env.DISCORD_TOKEN || '',
        prefix: process.env.DISCORD_PREFIX || '!atena',
        adminUsers: (process.env.DISCORD_ADMIN_USERS || '').split(',').filter(Boolean),
    },

    // Google Workspace configuration
    googleWorkspace: {
        credentials: process.env.GOOGLE_CREDENTIALS || '',
        folderName: process.env.GOOGLE_FOLDER_NAME || 'ATENA AI Research',
    },

    // Research agent configuration
    research: {
        defaultTimeoutMinutes: parseInt(process.env.RESEARCH_TIMEOUT_MINUTES || '10', 10),
        maxMessagesToAnalyze: parseInt(process.env.RESEARCH_MAX_MESSAGES || '100', 10),
        threadArchiveDuration: parseInt(process.env.RESEARCH_THREAD_ARCHIVE_DURATION || '1440', 10), // 24 hours
    },

    // Logging configuration
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        file: process.env.LOG_FILE || 'logs/atena.log',
    },
}; 