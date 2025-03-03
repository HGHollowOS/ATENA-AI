import { MessageBus } from '../core/MessageBus';
import { AgentMessage, AgentPriority } from '../core/types/Agent';

interface TrendingTopic {
    topic: string;
    mentions: number;
    sources: string[];
    firstMentioned: Date;
    lastMentioned: Date;
    relatedTerms: string[];
}

interface SystemHealth {
    agentStatus: Map<string, {
        status: string;
        lastCheck: Date;
        errorCount: number;
        performance: number;
    }>;
    systemMetrics: {
        cpuUsage: number;
        memoryUsage: number;
        activeConnections: number;
        requestLatency: number;
    };
    integrationHealth: Map<string, {
        status: string;
        latency: number;
        errorRate: number;
        lastSync: Date;
    }>;
}

interface WeeklyDigest {
    period: {
        start: Date;
        end: Date;
    };
    trends: TrendingTopic[];
    topDiscussions: {
        threadId: string;
        topic: string;
        participants: number;
        messageCount: number;
        decisions: string[];
    }[];
    systemPerformance: {
        uptime: number;
        totalRequests: number;
        averageLatency: number;
        errorRate: number;
    };
}

export class MonitoringService {
    private static instance: MonitoringService;
    private messageBus: MessageBus;
    private trendingTopics: Map<string, TrendingTopic> = new Map();
    private systemHealth: SystemHealth = {
        agentStatus: new Map(),
        systemMetrics: {
            cpuUsage: 0,
            memoryUsage: 0,
            activeConnections: 0,
            requestLatency: 0
        },
        integrationHealth: new Map()
    };
    private readonly TREND_THRESHOLD = 5;
    private readonly HEALTH_CHECK_INTERVAL = 60000; // 1 minute
    private readonly DIGEST_SCHEDULE = '0 0 * * 0'; // Weekly on Sunday

    private constructor() {
        this.messageBus = MessageBus.getInstance();
        this.setupEventHandlers();
        this.startMonitoring();
    }

    public static getInstance(): MonitoringService {
        if (!MonitoringService.instance) {
            MonitoringService.instance = new MonitoringService();
        }
        return MonitoringService.instance;
    }

    private setupEventHandlers(): void {
        this.messageBus.on('messageDelivered', async (message: AgentMessage) => {
            switch (message.type) {
                case 'DISCORD_MESSAGE_RECEIVED':
                    await this.analyzeMessage(message.content);
                    break;
                case 'DISCORD_TRENDING_TOPIC':
                    await this.processTrendingTopic(message.content);
                    break;
                case 'DISCORD_HEALTH_CHECK':
                    await this.updateDiscordHealth(message.content);
                    break;
                case 'AGENT_STATUS_UPDATE':
                    await this.updateAgentStatus(message.content);
                    break;
            }
        });
    }

    private async analyzeMessage(content: any): Promise<void> {
        // Extract potential topics and terms
        const terms = await this.extractKeyTerms(content.content);

        for (const term of terms) {
            if (!this.trendingTopics.has(term)) {
                this.trendingTopics.set(term, {
                    topic: term,
                    mentions: 0,
                    sources: [],
                    firstMentioned: new Date(),
                    lastMentioned: new Date(),
                    relatedTerms: []
                });
            }

            const topic = this.trendingTopics.get(term)!;
            topic.mentions++;
            topic.lastMentioned = new Date();
            topic.sources.push('discord');

            if (topic.mentions >= this.TREND_THRESHOLD) {
                await this.checkExternalTrends(term);
            }
        }
    }

    private async extractKeyTerms(text: string): Promise<string[]> {
        // Placeholder for NLP processing
        // Would use something like OpenAI's API or other NLP service
        return text.split(' ').filter(word => word.length > 4);
    }

    private async checkExternalTrends(topic: string): Promise<void> {
        try {
            // Check Twitter/X trends
            const twitterTrends = await this.checkTwitterTrends(topic);

            // Check news headlines
            const newsHeadlines = await this.checkNewsHeadlines(topic);

            if (twitterTrends || newsHeadlines) {
                await this.messageBus.broadcast({
                    type: 'EXTERNAL_TREND_DETECTED',
                    content: {
                        topic,
                        twitter: twitterTrends,
                        news: newsHeadlines
                    },
                    priority: AgentPriority.HIGH,
                    sender: 'monitoring_service'
                });
            }
        } catch (error) {
            console.error('Error checking external trends:', error);
        }
    }

    private async checkTwitterTrends(topic: string): Promise<any> {
        // Implement Twitter/X API integration
        return null;
    }

    private async checkNewsHeadlines(topic: string): Promise<any> {
        // Implement News API integration
        return null;
    }

    private startMonitoring(): void {
        // System health monitoring
        setInterval(() => {
            this.checkSystemHealth();
        }, this.HEALTH_CHECK_INTERVAL);

        // Weekly digest scheduling
        this.scheduleWeeklyDigest();
    }

    private async checkSystemHealth(): Promise<void> {
        // Update system metrics
        this.systemHealth.systemMetrics = await this.collectSystemMetrics();

        // Check for anomalies
        const anomalies = this.detectAnomalies();
        if (anomalies.length > 0) {
            await this.messageBus.broadcast({
                type: 'SYSTEM_HEALTH_ALERT',
                content: {
                    anomalies,
                    metrics: this.systemHealth.systemMetrics
                },
                priority: AgentPriority.HIGH,
                sender: 'monitoring_service'
            });
        }
    }

    private async collectSystemMetrics(): Promise<any> {
        // Implement system metrics collection
        return {
            cpuUsage: 0,
            memoryUsage: 0,
            activeConnections: 0,
            requestLatency: 0
        };
    }

    private detectAnomalies(): string[] {
        const anomalies: string[] = [];
        const metrics = this.systemHealth.systemMetrics;

        if (metrics.cpuUsage > 80) {
            anomalies.push('High CPU usage detected');
        }
        if (metrics.memoryUsage > 80) {
            anomalies.push('High memory usage detected');
        }
        if (metrics.requestLatency > 1000) {
            anomalies.push('High request latency detected');
        }

        return anomalies;
    }

    private scheduleWeeklyDigest(): void {
        // Schedule weekly digest generation
        // Would use a proper scheduler like node-cron in production
        setInterval(() => {
            this.generateWeeklyDigest();
        }, 7 * 24 * 60 * 60 * 1000); // Weekly
    }

    private async generateWeeklyDigest(): Promise<void> {
        const digest: WeeklyDigest = {
            period: {
                start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
                end: new Date()
            },
            trends: Array.from(this.trendingTopics.values())
                .filter(topic => topic.lastMentioned > this.getLastWeek())
                .sort((a, b) => b.mentions - a.mentions)
                .slice(0, 10),
            topDiscussions: [], // Would be populated from Discord data
            systemPerformance: {
                uptime: 100, // Placeholder
                totalRequests: 0,
                averageLatency: 0,
                errorRate: 0
            }
        };

        await this.messageBus.broadcast({
            type: 'WEEKLY_DIGEST_READY',
            content: digest,
            priority: AgentPriority.MEDIUM,
            sender: 'monitoring_service'
        });
    }

    private getLastWeek(): Date {
        return new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    }

    public async updateAgentStatus(status: any): Promise<void> {
        this.systemHealth.agentStatus.set(status.agentId, {
            status: status.status,
            lastCheck: new Date(),
            errorCount: status.errorCount || 0,
            performance: status.performance || 100
        });
    }

    public async updateDiscordHealth(metrics: any): Promise<void> {
        this.systemHealth.integrationHealth.set('discord', {
            status: 'healthy',
            latency: metrics.messageLatency,
            errorRate: 0,
            lastSync: new Date()
        });
    }

    private async processTrendingTopic(content: any): Promise<void> {
        const { channelId, guildId, messageCount, uniqueUsers } = content;

        // Create or update trending topic
        const topicKey = `${guildId}:${channelId}`;
        if (!this.trendingTopics.has(topicKey)) {
            this.trendingTopics.set(topicKey, {
                topic: 'Channel Trend', // Would be replaced with actual topic analysis
                mentions: messageCount,
                sources: ['discord'],
                firstMentioned: new Date(),
                lastMentioned: new Date(),
                relatedTerms: []
            });
        } else {
            const topic = this.trendingTopics.get(topicKey)!;
            topic.mentions += messageCount;
            topic.lastMentioned = new Date();
        }

        // Check external trends if threshold is met
        if (messageCount >= this.TREND_THRESHOLD) {
            await this.checkExternalTrends(topicKey);
        }
    }
} 