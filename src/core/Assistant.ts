import OpenAI from 'openai';
import { GoogleWorkspaceIntegration } from '../integrations/GoogleWorkspace';
import { LinkedInIntegration } from '../integrations/LinkedIn';
import { NewsIntegration } from '../integrations/News';
import {
    Task,
    Meeting,
    Email,
    Decision,
    Priority,
    TaskStatus,
    TaskCategory,
    AssistantContext,
    UserPreferences,
    LinkedInPost,
    LinkedInNotification,
    NewsArticle
} from '../types';
import { TextChannel } from 'discord.js';

export class Assistant {
    private context: AssistantContext;
    private openai: OpenAI;
    private googleWorkspace: GoogleWorkspaceIntegration;
    private linkedIn: LinkedInIntegration;
    private news: NewsIntegration;
    private checkInterval!: NodeJS.Timeout;

    constructor(
        apiKey: string,
        userPreferences: UserPreferences,
        googleWorkspace: GoogleWorkspaceIntegration,
        linkedIn: LinkedInIntegration
    ) {
        this.openai = new OpenAI({ apiKey });
        this.googleWorkspace = googleWorkspace;
        this.linkedIn = linkedIn;
        this.news = new NewsIntegration(apiKey, googleWorkspace);
        this.context = {
            currentUser: '',
            userPreferences,
            recentDecisions: [],
            upcomingDeadlines: [],
            unreadEmails: [],
            lastChecked: {
                emails: new Date(),
                calendar: new Date(),
                linkedin: new Date(),
                news: new Date()
            },
            relevantNews: []
        };
    }

    /**
     * Initialize the Assistant and its integrations
     */
    public async initialize(): Promise<void> {
        try {
            // Initialize Google Workspace
            await this.initializeGoogleWorkspace();

            // Log initialization of other services
            console.log('All assistant services initialized');
        } catch (error) {
            console.error('Error initializing Assistant:', error);
            throw error;
        }
    }

    private async initializeGoogleWorkspace(): Promise<void> {
        try {
            await this.googleWorkspace.initialize();
            console.log('Google Workspace services initialized');

            // Start proactive monitoring after initialization
            this.startProactiveMonitoring();
        } catch (error) {
            console.error('Error initializing Google Workspace:', error);
            throw error;
        }
    }

    private async startProactiveMonitoring(): Promise<void> {
        // Check every 5 minutes
        this.checkInterval = setInterval(async () => {
            await this.checkForUpdates();
        }, 5 * 60 * 1000);
    }

    private async checkForUpdates(): Promise<void> {
        try {
            // Check for new emails
            const newEmails = await this.checkNewEmails();

            // Check calendar for upcoming meetings
            const upcomingMeetings = await this.checkUpcomingMeetings();

            // Check LinkedIn notifications
            const newLinkedInNotifications = await this.checkLinkedInUpdates();

            // Check relevant news
            const newNewsArticles = await this.checkNewsUpdates();

            // Process all updates with AI to determine actions
            await this.processUpdates(
                newEmails,
                upcomingMeetings,
                newLinkedInNotifications,
                newNewsArticles
            );
        } catch (error) {
            console.error('Error in proactive monitoring:', error);
        }
    }

    private async processUpdates(
        emails: Email[],
        meetings: Meeting[],
        notifications: LinkedInNotification[],
        newsArticles: NewsArticle[]
    ): Promise<void> {
        if (emails.length === 0 && meetings.length === 0 &&
            notifications.length === 0 && newsArticles.length === 0) {
            return;
        }

        // Prepare context for AI
        const context = {
            emails: emails.map(e => ({
                subject: e.subject,
                from: e.from,
                priority: e.priority,
                snippet: e.body.substring(0, 200)
            })),
            meetings: meetings.map(m => ({
                title: m.title,
                startTime: m.startTime,
                attendees: m.attendees
            })),
            notifications: notifications.map(n => ({
                type: n.type,
                message: n.message,
                timestamp: n.timestamp
            })),
            news: newsArticles.map(article => ({
                title: article.title,
                description: article.description,
                relevanceScore: article.relevanceScore,
                relatedTopics: article.relatedTopics
            }))
        };

        // Ask AI to analyze updates and suggest actions
        const completion = await this.openai.chat.completions.create({
            model: "gpt-4-turbo-preview",
            messages: [
                {
                    role: "system",
                    content: "You are a proactive AI assistant. Analyze these updates and suggest specific actions to take. Consider how news articles might impact ongoing tasks and meetings. IMPORTANT: Your response must be a valid JSON array of action objects with 'type' and 'data' fields."
                },
                {
                    role: "user",
                    content: JSON.stringify(context)
                }
            ]
        });

        const suggestedActions = completion.choices[0].message?.content || '[]';
        try {
            const actions = JSON.parse(suggestedActions);
            await this.executeActions(Array.isArray(actions) ? actions : []);
        } catch (error) {
            console.error('Error parsing suggested actions:', error);
            console.error('Raw response:', suggestedActions);
            // Try to extract actions using a more lenient approach
            await this.extractAndExecuteActions(suggestedActions);
        }
    }

    private async extractAndExecuteActions(content: string): Promise<void> {
        try {
            // Ask GPT to convert the text response to valid JSON
            const completion = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Convert the following text into a valid JSON array of action objects. Each action should have 'type' and 'data' fields. Valid action types are: SEND_EMAIL, SCHEDULE_MEETING, POST_LINKEDIN, CREATE_TASK. Return ONLY the JSON array, nothing else."
                    },
                    {
                        role: "user",
                        content
                    }
                ]
            });

            const jsonString = completion.choices[0].message?.content?.trim() || '[]';
            const actions = JSON.parse(jsonString);
            await this.executeActions(Array.isArray(actions) ? actions : []);
        } catch (error) {
            console.error('Failed to extract actions from text:', error);
        }
    }

    private async checkNewsUpdates(): Promise<NewsArticle[]> {
        const articles = await this.news.getRelevantNews();
        const newArticles = articles.filter(article =>
            article.publishedAt > this.context.lastChecked.news
        );

        // Update context with new articles
        this.context.relevantNews = [
            ...newArticles,
            ...this.context.relevantNews
        ].slice(0, 50); // Keep only the 50 most recent articles

        return newArticles;
    }

    public async testNewsConnection(): Promise<boolean> {
        try {
            await this.news.testConnection();
            return true;
        } catch (error) {
            console.error('News API connection test failed:', error);
            return false;
        }
    }

    private async executeActions(actions: any[]): Promise<void> {
        for (const action of actions) {
            switch (action.type) {
                case 'SEND_EMAIL':
                    await this.draftEmail(
                        action.data.subject,
                        action.data.to,
                        action.data.body,
                        action.data.priority
                    );
                    break;
                case 'SCHEDULE_MEETING':
                    await this.scheduleMeeting(
                        action.data.title,
                        action.data.description,
                        new Date(action.data.startTime),
                        new Date(action.data.endTime),
                        action.data.attendees
                    );
                    break;
                case 'POST_LINKEDIN':
                    await this.postToLinkedIn(action.data);
                    break;
                case 'CREATE_TASK':
                    await this.createTask(
                        action.data.title,
                        action.data.description,
                        action.data.priority,
                        action.data.category,
                        action.data.dueDate ? new Date(action.data.dueDate) : undefined
                    );
                    break;
            }
        }
    }

    private async checkNewEmails(): Promise<Email[]> {
        const emails = await this.googleWorkspace.getUnreadEmails();
        return emails.filter(email =>
            new Date(email.createdAt) > this.context.lastChecked.emails
        );
    }

    private async checkUpcomingMeetings(): Promise<Meeting[]> {
        const meetings = await this.googleWorkspace.getUpcomingMeetings();
        return meetings.filter(meeting =>
            meeting.startTime > new Date() &&
            meeting.startTime < new Date(Date.now() + 24 * 60 * 60 * 1000)
        );
    }

    private async checkLinkedInUpdates(): Promise<LinkedInNotification[]> {
        const notifications = await this.linkedIn.getNotifications();
        return notifications.filter(notification =>
            notification.timestamp > this.context.lastChecked.linkedin
        );
    }

    public async postToLinkedIn(post: LinkedInPost): Promise<string> {
        return await this.linkedIn.postUpdate(post);
    }

    public async testLinkedInConnection(): Promise<boolean> {
        try {
            await this.linkedIn.testConnection();
            return true;
        } catch (error) {
            console.error('LinkedIn connection test failed:', error);
            return false;
        }
    }

    public async testGmailConnection(): Promise<boolean> {
        try {
            await this.googleWorkspace.testGmailConnection();
            return true;
        } catch (error) {
            console.error('Gmail connection test failed:', error);
            return false;
        }
    }

    public async testCalendarConnection(): Promise<boolean> {
        try {
            await this.googleWorkspace.testCalendarConnection();
            return true;
        } catch (error) {
            console.error('Calendar connection test failed:', error);
            return false;
        }
    }

    public async testDriveConnection(): Promise<boolean> {
        try {
            await this.googleWorkspace.testDriveConnection();
            return true;
        } catch (error) {
            console.error('Drive connection test failed:', error);
            return false;
        }
    }

    // Core functionality: Process incoming information
    public async processInformation(info: any): Promise<string> {
        try {
            const context = await this.analyzeContext(info);

            // For conversational interactions
            if (context.type === 'conversation') {
                const completion = await this.openai.chat.completions.create({
                    model: "gpt-4-turbo-preview",
                    messages: [
                        {
                            role: "system",
                            content: `You are ATENA AI, a helpful and friendly AI assistant. You can help with tasks, 
                            schedule meetings, set reminders, and engage in natural conversations. Always be helpful, 
                            clear, and concise. If you're not sure about something, ask for clarification.
                            Current user: ${context.username}
                            Channel: ${context.isDirectMessage ? 'Direct Message' : 'Server Channel'}
                            `
                        },
                        {
                            role: "user",
                            content: context.content
                        }
                    ]
                });

                const response = completion.choices[0].message?.content || 'I apologize, but I was unable to process your message.';

                // Check if the response indicates any actions needed
                if (response.toLowerCase().includes('schedule') ||
                    response.toLowerCase().includes('reminder') ||
                    response.toLowerCase().includes('task')) {
                    // Process potential actions from the conversation
                    await this.processConversationalActions(context, response);
                }

                return response;
            }

            // For command responses
            if (info.isCommandResponse) {
                return info.response;
            }

            // For other types of information, proceed with existing logic
            return await this.generateResponse(context);
        } catch (error) {
            console.error('Error processing information:', error);
            return 'I apologize, but I encountered an error processing your request. Please try again.';
        }
    }

    private async processConversationalActions(context: any, response: string): Promise<void> {
        try {
            // Ask GPT to analyze if any actions should be taken based on the conversation
            const actionAnalysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Analyze this conversation and determine if any actions should be taken. Return a JSON array of actions if needed, or an empty array if no actions are needed. Possible actions: CREATE_TASK, SEND_REMINDER, SCHEDULE_MEETING"
                    },
                    {
                        role: "user",
                        content: `User message: ${context.content}\nAI response: ${response}`
                    }
                ]
            });

            const actions = JSON.parse(actionAnalysis.choices[0].message?.content || '[]');
            if (actions.length > 0) {
                await this.executeActions(actions);
            }
        } catch (error) {
            console.error('Error processing conversational actions:', error);
        }
    }

    private async analyzeContext(info: any): Promise<any> {
        try {
            // If the input is already an object, use it directly
            if (typeof info === 'object' && info !== null) {
                return info;
            }

            // Only try to parse as JSON if it's a string and looks like JSON
            if (typeof info === 'string' && info.trim().startsWith('{')) {
                return JSON.parse(info);
            }

            // Otherwise, create a simple context object
            return {
                type: 'text',
                content: info
            };
        } catch (error) {
            console.error('Error analyzing context:', error);
            throw error;
        }
    }

    // Response generation based on analysis
    private async generateResponse(analysis: any): Promise<string> {
        const completion = await this.openai.chat.completions.create({
            model: "gpt-4",
            messages: [
                {
                    role: "system",
                    content: "You are an AI assistant generating helpful responses."
                },
                {
                    role: "user",
                    content: JSON.stringify(analysis)
                }
            ]
        });

        return completion.choices[0].message?.content || '';
    }

    // Task Management
    async createTask(
        title: string,
        description: string,
        priority: Priority,
        category: TaskCategory,
        dueDate?: Date
    ): Promise<Task> {
        const task: Task = {
            id: this.generateId(),
            title,
            description,
            priority,
            status: TaskStatus.TODO,
            category,
            dueDate,
            createdAt: new Date(),
            updatedAt: new Date()
        };

        // Add task to context
        this.context.upcomingDeadlines.push(task);
        return task;
    }

    // Meeting Management
    async scheduleMeeting(
        title: string,
        description: string,
        startTime: Date,
        endTime: Date,
        attendees: string[]
    ): Promise<Meeting> {
        const meeting: Meeting = {
            id: this.generateId(),
            title,
            description,
            startTime,
            endTime,
            attendees,
            agenda: [],
            decisions: [],
            actionItems: []
        };

        // Schedule in Google Calendar
        await this.googleWorkspace.scheduleMeeting(meeting);

        return meeting;
    }

    // Email Management
    async draftEmail(
        subject: string,
        to: string[],
        body: string,
        priority: Priority
    ): Promise<Email> {
        const email: Email = {
            id: this.generateId(),
            subject,
            from: this.context.currentUser,
            to,
            body,
            priority,
            status: 'DRAFT',
            createdAt: new Date()
        };

        return email;
    }

    // Decision Support
    async analyzeDecision(decision: Decision): Promise<{
        recommendation: string;
        analysis: string;
        risks: string[];
    }> {
        const completion = await this.openai.chat.completions.create({
            model: "gpt-4",
            messages: [
                {
                    role: "system",
                    content: "You are an AI assistant analyzing a business decision."
                },
                {
                    role: "user",
                    content: JSON.stringify(decision)
                }
            ]
        });

        const analysis = completion.choices[0].message?.content || '';
        return this.parseDecisionAnalysis(analysis);
    }

    // Utility methods
    private generateId(): string {
        return Math.random().toString(36).substring(2) + Date.now().toString(36);
    }

    private async generateEmbedding(text: string): Promise<number[]> {
        const response = await this.openai.embeddings.create({
            model: "text-embedding-ada-002",
            input: text
        });

        return response.data[0].embedding;
    }

    private structureAnalysis(analysis: string): any {
        // Implementation to parse and structure the analysis
        return JSON.parse(analysis);
    }

    private parseDecisionAnalysis(analysis: string): any {
        // Implementation to parse decision analysis
        return JSON.parse(analysis);
    }

    private updateContext(analysis: any): void {
        // Implementation to update assistant context based on new information
        this.context = {
            ...this.context,
            // Update relevant fields based on analysis
        };
    }

    // Task Management Methods
    public async listTasks(channel: TextChannel): Promise<void> {
        try {
            const tasks = await this.googleWorkspace.getTasks();
            const tasksByCategory = tasks.reduce((acc, task) => {
                if (!acc[task.category]) {
                    acc[task.category] = [];
                }
                acc[task.category].push(task);
                return acc;
            }, {} as Record<TaskCategory, Task[]>);

            const embed = {
                color: 0x0099ff,
                title: '📝 Task List',
                fields: Object.entries(tasksByCategory).map(([category, tasks]) => ({
                    name: `${category} (${tasks.length})`,
                    value: tasks.map(task =>
                        `• ${task.title} [${task.status}] ${task.priority === Priority.URGENT ? '🔴' :
                            task.priority === Priority.HIGH ? '🟡' : '⚪'}`
                    ).join('\n') || 'No tasks'
                })),
                timestamp: new Date().toISOString()
            };

            await channel.send({ embeds: [embed] });
        } catch (error) {
            console.error('Error listing tasks:', error);
            await channel.send('Failed to retrieve tasks. Please try again.');
        }
    }

    public async updateTaskStatus(taskId: string, newStatus: string, channel: TextChannel): Promise<void> {
        try {
            const task = await this.googleWorkspace.updateTaskStatus(taskId, newStatus as TaskStatus);
            await channel.send({
                embeds: [{
                    title: '✅ Task Updated',
                    description: `Task "${task.title}" status changed to ${newStatus}`,
                    color: 0x00ff00
                }]
            });
        } catch (error) {
            console.error('Error updating task:', error);
            await channel.send('Failed to update task status. Please try again.');
        }
    }

    public async listMeetings(channel: TextChannel): Promise<void> {
        try {
            const meetings = await this.googleWorkspace.getUpcomingMeetings();
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);

            const todayMeetings = meetings.filter(m =>
                m.startTime.toDateString() === today.toDateString()
            );

            const tomorrowMeetings = meetings.filter(m =>
                m.startTime.toDateString() === tomorrow.toDateString()
            );

            const laterMeetings = meetings.filter(m =>
                m.startTime > tomorrow && m.startTime <= new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)
            );

            const embed = {
                color: 0x0099ff,
                title: '📅 Upcoming Meetings',
                fields: [
                    {
                        name: '📍 Today',
                        value: todayMeetings.map(m =>
                            `• ${m.startTime.toLocaleTimeString()} - ${m.title} (${m.attendees.length} attendees)`
                        ).join('\n') || 'No meetings'
                    },
                    {
                        name: '📍 Tomorrow',
                        value: tomorrowMeetings.map(m =>
                            `• ${m.startTime.toLocaleTimeString()} - ${m.title} (${m.attendees.length} attendees)`
                        ).join('\n') || 'No meetings'
                    },
                    {
                        name: '📍 Next 7 Days',
                        value: laterMeetings.map(m =>
                            `• ${m.startTime.toLocaleDateString()} ${m.startTime.toLocaleTimeString()} - ${m.title}`
                        ).join('\n') || 'No meetings'
                    }
                ],
                timestamp: new Date().toISOString()
            };

            await channel.send({ embeds: [embed] });
        } catch (error) {
            console.error('Error listing meetings:', error);
            await channel.send('Failed to retrieve meetings. Please try again.');
        }
    }

    public async analyzeSentiment(conversationHistory: Array<{ content: string }>): Promise<{ overall: string }> {
        try {
            const completion = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Analyze the sentiment of this conversation. Return a brief, one-word description of the overall tone."
                    },
                    {
                        role: "user",
                        content: conversationHistory.map(m => m.content).join('\n')
                    }
                ]
            });

            return {
                overall: completion.choices[0].message?.content?.trim() || 'neutral'
            };
        } catch (error) {
            console.error('Error analyzing sentiment:', error);
            return { overall: 'neutral' };
        }
    }

    public async generateResearchSummary(params: {
        topics: string[];
        conversationHistory: Array<{ content: string; author: string; timestamp: Date }>;
        requestedTopic: string;
        sentiment?: { overall: string };
        patterns?: string[];
    }): Promise<string> {
        try {
            const completion = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Generate a concise summary of this conversation, focusing on key points and insights."
                    },
                    {
                        role: "user",
                        content: JSON.stringify(params)
                    }
                ]
            });

            return completion.choices[0].message?.content || 'Unable to generate summary';
        } catch (error) {
            console.error('Error generating summary:', error);
            return 'Error generating summary';
        }
    }

    public async generateRecommendations(params: {
        topics: string[];
        patterns: string[];
        sentiment: { overall: string };
    }): Promise<string[]> {
        try {
            const completion = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Based on the conversation analysis, provide 3 key recommendations or insights."
                    },
                    {
                        role: "user",
                        content: JSON.stringify(params)
                    }
                ]
            });

            const recommendations = completion.choices[0].message?.content?.split('\n') || [];
            return recommendations.slice(0, 3);
        } catch (error) {
            console.error('Error generating recommendations:', error);
            return ['Unable to generate recommendations'];
        }
    }
} 