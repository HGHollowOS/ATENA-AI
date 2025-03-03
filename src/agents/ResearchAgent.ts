import { Message, ThreadChannel } from 'discord.js';
import { Assistant } from '../core/Assistant';
import { GoogleWorkspaceIntegration } from '../integrations/GoogleWorkspace';
import OpenAI from 'openai';

interface ResearchContext {
    conversationHistory: Array<{
        author: string;
        content: string;
        timestamp: Date;
        authorId?: string;
    }>;
    metaContext: {
        participants: Map<string, {
            role?: string;
            identity?: string;
            relevance?: string;
        }>;
        organizationInfo?: {
            name?: string;
            industry?: string;
            size?: string;
            [key: string]: any;
        };
        projectContext?: string;
        previousResearch?: string[];
    };
    researchFocus: {
        primaryFocus: string;
        secondaryFoci: string[];
        keyTerms: string[];
        [key: string]: any;
    };
    sentiment?: {
        overall?: string;
        keyEmotions?: string[];
        byParticipant?: Record<string, string>;
        [key: string]: any;
    };
    keyPoints?: string[];
    agreements?: string[];
    disagreements?: string[];
    requestId: string;
    messageId: string;
    channelId: string;
}

interface ResearchProgress {
    stage: string;
    progress: number;
    details: string;
    startTime: Date;
    estimatedCompletion: Date;
}

export class ResearchAgent {
    private openai: OpenAI;
    private assistant: Assistant;
    private googleWorkspace: GoogleWorkspaceIntegration;
    private activeResearch: Map<string, ResearchProgress> = new Map();
    private researchContext: Map<string, ResearchContext> = new Map();

    constructor(apiKey: string, assistant: Assistant, googleWorkspace: GoogleWorkspaceIntegration) {
        this.openai = new OpenAI({ apiKey });
        this.assistant = assistant;
        this.googleWorkspace = googleWorkspace;
    }

    /**
     * Safely parse JSON from a string that might include markdown formatting
     * If the string is not valid JSON, return a default value
     */
    private safeJsonParse<T>(jsonString: string, defaultValue: T): T {
        try {
            // If the string is empty or not a string, return the default value
            if (!jsonString || typeof jsonString !== 'string') {
                return defaultValue;
            }

            // Check if the response is a markdown code block
            let cleanJson = jsonString.trim();

            // Try to extract JSON from markdown code blocks
            if (cleanJson.includes('```')) {
                const match = cleanJson.match(/```(?:json)?\s*([\s\S]*?)```/);
                if (match && match[1]) {
                    cleanJson = match[1].trim();
                } else {
                    // If no match found, try removing the start and hoping for the best
                    cleanJson = cleanJson.replace(/```json\s*/, '').replace(/```\s*$/, '');
                }
            }

            // Try to parse as JSON
            try {
                return JSON.parse(cleanJson);
            } catch (jsonError) {
                // If it's not valid JSON and starts with characters that suggest it's plain text
                if (cleanJson.startsWith('Based on') ||
                    /^[A-Z][a-z]/.test(cleanJson) ||
                    cleanJson.includes('\n')) {

                    // It's likely a text analysis, so create a simple JSON object with the content
                    console.log('Converting text response to JSON object');
                    return { content: cleanJson } as unknown as T;
                }

                // If we can't parse it and it doesn't look like text, rethrow the error
                throw jsonError;
            }
        } catch (error) {
            console.error('Error parsing JSON:', error);
            console.error('Original string:', jsonString);
            return defaultValue;
        }
    }

    /**
     * Start a comprehensive research task based on a Discord message
     */
    public async startResearch(message: Message, requestId: string): Promise<ThreadChannel> {
        // Create a thread for the research
        const thread = await message.startThread({
            name: `Research: ${message.content.slice(0, 50)}...`,
            autoArchiveDuration: 1440 // Archive after 24 hours of inactivity
        });

        // Initialize research progress
        this.activeResearch.set(requestId, {
            stage: 'Initializing',
            progress: 0,
            details: 'Setting up research parameters',
            startTime: new Date(),
            estimatedCompletion: new Date(Date.now() + 10 * 60 * 1000) // Initial estimate: 10 minutes
        });

        // Start the research process asynchronously
        this.conductResearch(message, thread, requestId).catch(error => {
            console.error('Error in research process:', error);
            thread.send(`❌ Error during research: ${error.message}. Please try again.`);
        });

        return thread;
    }

    /**
     * Main research process
     */
    private async conductResearch(message: Message, thread: ThreadChannel, requestId: string): Promise<void> {
        try {
            // Helper function to send updates to the thread
            const sendUpdate = async (update: string, progress: number) => {
                const currentProgress = this.activeResearch.get(requestId);
                if (currentProgress) {
                    this.activeResearch.set(requestId, {
                        ...currentProgress,
                        stage: update,
                        progress,
                        details: update
                    });
                }
                await thread.send({
                    embeds: [{
                        title: `🔍 Research Progress: ${Math.round(progress * 100)}%`,
                        description: update,
                        color: 0x3498db
                    }]
                });
            };

            // 1. Retrieve conversation context & meta info
            await sendUpdate('📥 Gathering conversation context and metadata...', 0.05);
            const context = await this.gatherConversationContext(message, requestId);
            this.researchContext.set(requestId, context);

            // 2. Determine user's research focus
            await sendUpdate('🔎 Analyzing research request to determine focus...', 0.15);
            const researchFocus = await this.determineResearchFocus(context.conversationHistory, message.content);
            context.researchFocus = researchFocus;
            this.researchContext.set(requestId, context);

            // 3. Analyze relevant conversation segments
            await sendUpdate('🧠 Analyzing conversation segments relevant to research focus...', 0.25);
            const analysisResults = await this.analyzeConversation(context);
            await sendUpdate(`Found ${analysisResults.keyPoints.length} key discussion points related to "${researchFocus.topic}"`, 0.35);

            // 4. Perform multi-perspective research
            await sendUpdate('🌐 Conducting multi-perspective analysis...', 0.45);
            const perspectives = await this.performMultiPerspectiveResearch(context, analysisResults);
            await sendUpdate(`Analyzed from ${perspectives.length} different perspectives`, 0.65);

            // 5. Compile comprehensive research document
            await sendUpdate('📊 Compiling comprehensive research document...', 0.75);
            const documentContent = await this.compileResearchDocument(context, analysisResults, perspectives);

            // 6. Create Google Doc
            await sendUpdate('📄 Creating Google Doc with research results...', 0.85);
            const docId = await this.createGoogleDoc(documentContent, `Research: ${context.researchFocus.topic}`);

            // 7. Final report with link to document
            await sendUpdate('✅ Research complete! Finalizing report...', 0.95);

            // Send final report
            await thread.send({
                embeds: [{
                    title: '📑 Research Complete',
                    description: `Your comprehensive research on "${context.researchFocus.topic}" is ready!`,
                    fields: [
                        {
                            name: '📄 Research Document',
                            value: `[Click here to view the full research document](https://docs.google.com/document/d/${docId})`
                        },
                        {
                            name: '🔍 Research Focus',
                            value: context.researchFocus.scope || 'General research on the topic'
                        },
                        {
                            name: '👥 Key Participants',
                            value: Array.from(context.metaContext.participants.entries())
                                .map(([name, info]) => `• ${name}${info.role ? ` (${info.role})` : ''}`)
                                .join('\n') || 'No specific participants identified'
                        }
                    ],
                    color: 0x00ff00,
                    timestamp: new Date().toISOString()
                }]
            });

            // Update research status to complete
            this.activeResearch.set(requestId, {
                stage: 'Complete',
                progress: 1.0,
                details: 'Research completed successfully',
                startTime: this.activeResearch.get(requestId)?.startTime || new Date(),
                estimatedCompletion: new Date()
            });

        } catch (error) {
            console.error('Error in research process:', error);
            await thread.send({
                embeds: [{
                    title: '❌ Research Error',
                    description: `An error occurred during the research process: ${error instanceof Error ? error.message : String(error)}`,
                    color: 0xff0000
                }]
            });

            // Update research status to error
            this.activeResearch.set(requestId, {
                stage: 'Error',
                progress: 0,
                details: `Error: ${error instanceof Error ? error.message : String(error)}`,
                startTime: this.activeResearch.get(requestId)?.startTime || new Date(),
                estimatedCompletion: new Date()
            });
        }
    }

    /**
     * Gather conversation context for research
     */
    private async gatherConversationContext(message: Message, requestId: string): Promise<ResearchContext> {
        // Get recent messages from the channel
        const messages = await message.channel.messages.fetch({ limit: 100 });

        // Convert to a format suitable for analysis
        const conversationHistory = Array.from(messages.values())
            .filter(m => !m.author.bot) // Exclude bot messages
            .sort((a, b) => a.createdTimestamp - b.createdTimestamp) // Sort by timestamp
            .map(m => ({
                author: m.author.username,
                authorId: m.author.id,
                content: m.content,
                timestamp: m.createdAt
            }));

        // Analyze participants
        const participants = new Map();

        // Get unique participants
        const uniqueParticipants = [...new Set(conversationHistory.map(m => m.author))];

        // Analyze each participant's messages
        for (const participant of uniqueParticipants) {
            const participantMessages = conversationHistory.filter(m => m.author === participant);

            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: `Analyze this participant's messages to determine their role and relevance:\n\nParticipant: ${participant}\n\nMessages:\n${participantMessages.map(m => m.content).join('\n\n')}`
                    }
                ]
            });

            try {
                // Define an interface for the expected result structure
                interface ParticipantAnalysis {
                    role?: string;
                    identity?: string;
                    relevance?: string;
                    content?: string;
                }

                const result = this.safeJsonParse<ParticipantAnalysis>(analysis.choices[0].message?.content || '{}', {});

                // If result has content property, it's a text response that was converted to an object
                if (result.content) {
                    // Extract information from the text content
                    const content = result.content;
                    let role = 'Unknown';
                    let identity = 'Unknown';
                    let relevance = 'Unknown';

                    // Try to extract role from the content
                    if (content.includes('role')) {
                        const roleMatch = content.match(/role[:\s]+(.*?)(?:\.|,|\n|$)/i);
                        if (roleMatch) role = roleMatch[1].trim();
                    }

                    // Extract identity information
                    if (content.includes('identity')) {
                        const identityMatch = content.match(/identity[:\s]+(.*?)(?:\.|,|\n|$)/i);
                        if (identityMatch) identity = identityMatch[1].trim();
                    } else {
                        // Use the participant name as identity if not found
                        identity = participant;
                    }

                    // Extract relevance information
                    if (content.includes('relevance')) {
                        const relevanceMatch = content.match(/relevance[:\s]+(.*?)(?:\.|,|\n|$)/i);
                        if (relevanceMatch) relevance = relevanceMatch[1].trim();
                    } else if (content.length > 100) {
                        // Use a summary of the content as relevance
                        relevance = content.substring(0, 100) + '...';
                    }

                    participants.set(participant, { role, identity, relevance });
                } else {
                    // Handle the case where result is a properly formatted JSON object
                    participants.set(participant, {
                        role: result.role || 'Unknown',
                        identity: result.identity || 'Unknown',
                        relevance: result.relevance || 'Unknown'
                    });
                }
            } catch (error) {
                console.error('Error parsing participant analysis:', error);
                // Set default values in case of error
                participants.set(participant, {
                    role: 'Unknown',
                    identity: participant,
                    relevance: 'Unknown'
                });
            }
        }

        // Extract organization info if available
        const orgInfo = await this.extractOrganizationInfo(conversationHistory);

        return {
            conversationHistory,
            metaContext: {
                participants,
                organizationInfo: orgInfo,
                previousResearch: [] // Will be populated if there are previous research results
            },
            researchFocus: {
                primaryFocus: message.content.replace(/!atena\s+research/i, '').trim(),
                secondaryFoci: [],
                keyTerms: []
            },
            requestId,
            messageId: message.id,
            channelId: message.channelId
        };
    }

    /**
     * Extract organization information from conversation history
     */
    private async extractOrganizationInfo(conversationHistory: Array<any>): Promise<any> {
        const allContent = conversationHistory.map(m => m.content).join('\n');

        const analysis = await this.openai.chat.completions.create({
            model: "gpt-4-turbo-preview",
            messages: [
                {
                    role: "system",
                    content: "Extract organization information from this conversation. Look for company name, industry, goals, and any project context. Return a JSON object with fields: name, industry, goals (array), projectContext."
                },
                {
                    role: "user",
                    content: allContent
                }
            ]
        });

        // Define interface for organization info
        interface OrganizationInfo {
            name?: string;
            industry?: string;
            goals?: string[];
            projectContext?: string;
            content?: string; // For text responses
        }

        const defaultOrgInfo: OrganizationInfo = {
            name: "Unknown",
            industry: "Unknown",
            goals: [],
            projectContext: ""
        };

        const result = this.safeJsonParse<OrganizationInfo>(
            analysis.choices[0].message?.content || '{}',
            defaultOrgInfo
        );

        // If we got a text response instead of JSON, try to extract info from it
        if (result.content) {
            const content = result.content;
            const orgInfo: OrganizationInfo = { ...defaultOrgInfo };

            // Try to extract name
            if (content.includes('name') || content.includes('company')) {
                const nameMatch = content.match(/(?:name|company)[:\s]+(.*?)(?:\.|,|\n|$)/i);
                if (nameMatch) orgInfo.name = nameMatch[1].trim();
            }

            // Try to extract industry
            if (content.includes('industry')) {
                const industryMatch = content.match(/industry[:\s]+(.*?)(?:\.|,|\n|$)/i);
                if (industryMatch) orgInfo.industry = industryMatch[1].trim();
            }

            // Try to extract goals
            if (content.includes('goals') || content.includes('objectives')) {
                const goalsSection = content.match(/(?:goals|objectives)[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)/is);
                if (goalsSection) {
                    const goalsList = goalsSection[1].split(/\n-|\n\d+\.|\n•/).filter(Boolean);
                    orgInfo.goals = goalsList.map(g => g.trim());
                }
            }

            // Try to extract project context
            if (content.includes('project') || content.includes('context')) {
                const contextMatch = content.match(/(?:project|context)[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)/is);
                if (contextMatch) orgInfo.projectContext = contextMatch[1].trim();
            }

            return orgInfo;
        }

        return result;
    }

    /**
     * Determine the focus of the research request
     */
    private async determineResearchFocus(messages: Array<{ content: string }>, requestMessage: string): Promise<any> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Based on these messages and the research request, determine the main focus areas for research. Return a JSON object with primaryFocus, secondaryFoci (array), and keyTerms (array)."
                    },
                    {
                        role: "user",
                        content: `Research request: ${requestMessage}\n\nContext messages:\n${messages.map(m => m.content).join('\n\n')}`
                    }
                ]
            });

            return this.safeJsonParse(analysis.choices[0].message?.content || '{}', {});
        } catch (error) {
            console.error('Error parsing research focus:', error);
            return {};
        }
    }

    /**
     * Analyze conversation segments relevant to the research focus
     */
    private async analyzeConversation(context: ResearchContext): Promise<any> {
        // Filter conversation to relevant segments based on research focus
        const relevantMessages = await this.filterRelevantMessages(context.conversationHistory, context.researchFocus);

        // Analyze sentiment and tone
        const sentiment = await this.analyzeSentiment(relevantMessages);

        // Extract key points and topics
        const keyPoints = await this.extractKeyPoints(relevantMessages);

        // Identify agreements and disagreements
        const agreements = await this.identifyAgreementsDisagreements(relevantMessages);

        return {
            relevantMessages,
            sentiment,
            keyPoints,
            agreements
        };
    }

    /**
     * Filter messages relevant to the research focus
     */
    private async filterRelevantMessages(messages: Array<any>, focus: any): Promise<Array<any>> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: `Filter these messages for relevance to the research focus: ${JSON.stringify(focus)}. Return a JSON array of indices (0-based) of relevant messages.`
                    },
                    {
                        role: "user",
                        content: messages.map((m, i) => `[${i}] ${m.author}: ${m.content}`).join('\n\n')
                    }
                ]
            });

            const relevantIndices = this.safeJsonParse(analysis.choices[0].message?.content || '[]', []);
            return relevantIndices.map((i: number) => messages[i]).filter(Boolean);
        } catch (error) {
            console.error('Error filtering relevant messages:', error);
            return messages;
        }
    }

    /**
     * Analyze sentiment and tone of messages
     */
    private async analyzeSentiment(messages: Array<any>): Promise<any> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Analyze the sentiment of these messages. Return a JSON object with overall sentiment, key emotions, and sentiment by participant."
                    },
                    {
                        role: "user",
                        content: messages.map(m => `${m.author}: ${m.content}`).join('\n\n')
                    }
                ]
            });

            return this.safeJsonParse(analysis.choices[0].message?.content || '{}', {});
        } catch (error) {
            console.error('Error parsing sentiment analysis:', error);
            return {};
        }
    }

    /**
     * Extract key points and topics from messages
     */
    private async extractKeyPoints(messages: Array<any>): Promise<string[]> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Extract the key points from these messages. Return a JSON array of strings, each representing an important point."
                    },
                    {
                        role: "user",
                        content: messages.map(m => `${m.author}: ${m.content}`).join('\n\n')
                    }
                ]
            });

            return this.safeJsonParse(analysis.choices[0].message?.content || '[]', []);
        } catch (error) {
            console.error('Error parsing key points:', error);
            return [];
        }
    }

    /**
     * Identify agreements and disagreements in the conversation
     */
    private async identifyAgreementsDisagreements(messages: Array<any>): Promise<any> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Identify points of agreement and disagreement in these messages. Return a JSON object with agreements (array) and disagreements (array)."
                    },
                    {
                        role: "user",
                        content: messages.map(m => `${m.author}: ${m.content}`).join('\n\n')
                    }
                ]
            });

            return this.safeJsonParse(analysis.choices[0].message?.content || '{}', {});
        } catch (error) {
            console.error('Error parsing agreements/disagreements:', error);
            return { agreements: [], disagreements: [] };
        }
    }

    /**
     * Perform multi-perspective research on the topic
     */
    private async performMultiPerspectiveResearch(context: ResearchContext, analysisResults: any): Promise<Array<any>> {
        const perspectives = [
            { type: 'business', prompt: 'Analyze from a business perspective, considering market opportunities, competitive landscape, and business models.' },
            { type: 'technical', prompt: 'Analyze from a technical perspective, considering feasibility, implementation challenges, and technical requirements.' },
            { type: 'legal', prompt: 'Analyze from a legal and regulatory perspective, considering compliance requirements, legal risks, and regulatory trends.' },
            { type: 'market', prompt: 'Analyze from a market perspective, considering customer needs, market trends, and adoption barriers.' },
            { type: 'recommendations', prompt: 'Provide strategic recommendations based on the analysis, including next steps, potential partnerships, and growth opportunities.' }
        ];

        // Define interface for perspective analysis
        interface PerspectiveAnalysis {
            summary?: string;
            keyInsights?: string[];
            implications?: string[];
            content?: string; // For text responses
        }

        const results = [];

        for (const perspective of perspectives) {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: `You are conducting research from a specific perspective: ${perspective.type}. ${perspective.prompt} Return a JSON object with fields: summary, keyInsights (array), implications (array).`
                    },
                    {
                        role: "user",
                        content: `Research focus: ${JSON.stringify(context.researchFocus)}\n\nKey points from conversation: ${JSON.stringify(analysisResults.keyPoints)}\n\nAgreements and disagreements: ${JSON.stringify(analysisResults.agreements)}`
                    }
                ]
            });

            // Default values for perspective analysis
            const defaultAnalysis: PerspectiveAnalysis = {
                summary: `Analysis from ${perspective.type} perspective`,
                keyInsights: [],
                implications: []
            };

            try {
                const result = this.safeJsonParse<PerspectiveAnalysis>(
                    analysis.choices[0].message?.content || '{}',
                    defaultAnalysis
                );

                // If we got a text response instead of JSON, try to extract info from it
                if (result.content) {
                    const content = result.content;
                    const perspectiveResult: PerspectiveAnalysis = { ...defaultAnalysis };

                    // Try to extract summary
                    if (content.includes('summary')) {
                        const summaryMatch = content.match(/summary[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)/is);
                        if (summaryMatch) perspectiveResult.summary = summaryMatch[1].trim();
                    } else {
                        // Use first paragraph as summary if no explicit summary
                        const firstPara = content.split('\n\n')[0];
                        if (firstPara) perspectiveResult.summary = firstPara.trim();
                    }

                    // Try to extract key insights
                    if (content.includes('key insights') || content.includes('keyInsights')) {
                        const insightsSection = content.match(/(?:key insights|keyInsights)[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)/is);
                        if (insightsSection) {
                            const insightsList = insightsSection[1].split(/\n-|\n\d+\.|\n•/).filter(Boolean);
                            perspectiveResult.keyInsights = insightsList.map(i => i.trim());
                        }
                    }

                    // Try to extract implications
                    if (content.includes('implications')) {
                        const implicationsSection = content.match(/implications[:\s]+(.*?)(?=\n\n|\n[A-Z]|$)/is);
                        if (implicationsSection) {
                            const implicationsList = implicationsSection[1].split(/\n-|\n\d+\.|\n•/).filter(Boolean);
                            perspectiveResult.implications = implicationsList.map(i => i.trim());
                        }
                    }

                    results.push({
                        type: perspective.type,
                        ...perspectiveResult
                    });
                } else {
                    // Handle the case where result is a properly formatted JSON object
                    results.push({
                        type: perspective.type,
                        ...result
                    });
                }
            } catch (error) {
                console.error(`Error parsing ${perspective.type} perspective:`, error);
                // Add default values in case of error
                results.push({
                    type: perspective.type,
                    ...defaultAnalysis
                });
            }
        }

        return results;
    }

    /**
     * Compile comprehensive research document
     */
    private async compileResearchDocument(context: ResearchContext, analysisResults: any, perspectives: Array<any>): Promise<string> {
        const template = `
# Comprehensive Research: ${context.researchFocus.topic}

## Executive Summary
${this.generateExecutiveSummary(context, analysisResults, perspectives)}

## Research Context
- **Research Focus**: ${context.researchFocus.scope}
- **Conversation Timeline**: ${this.formatTimespan(context.conversationHistory)}
- **Key Participants**: ${Array.from(context.metaContext.participants.entries())
                .map(([name, info]) => `${name}${info.role ? ` (${info.role})` : ''}`)
                .join(', ')}

## Key Discussion Points
${this.formatKeyPoints(analysisResults.keyPoints)}

## Sentiment Analysis
${this.formatSentiment(analysisResults.sentiment)}

## Multi-Perspective Analysis
${this.formatPerspectives(perspectives)}

## Agreements & Disagreements
${this.formatAgreementsDisagreements(analysisResults.agreements)}

## Strategic Recommendations
${this.formatRecommendations(perspectives.find(p => p.type === 'recommendations'))}

## Next Steps
${this.generateNextSteps(context, perspectives)}

## Appendix: Relevant Messages
${this.formatRelevantMessages(analysisResults.relevantMessages)}
`;

        return template;
    }

    /**
     * Create a Google Doc with the research results
     */
    private async createGoogleDoc(content: string, title: string): Promise<string> {
        try {
            return await this.googleWorkspace.createDocument(title, content);
        } catch (error) {
            console.error('Error creating Google Doc:', error);
            throw new Error('Failed to create Google Doc with research results');
        }
    }

    /**
     * Get the status of a research task
     */
    public getResearchStatus(requestId: string): ResearchProgress | null {
        return this.activeResearch.get(requestId) || null;
    }

    /**
     * Helper methods for formatting research document
     */
    private generateExecutiveSummary(context: any, analysisResults: any, perspectives: any[]): string {
        // Implementation would generate a concise executive summary
        return `This research analyzes "${context.researchFocus.topic}" based on a conversation with ${context.metaContext.participants.size} participants. 
The analysis reveals ${analysisResults.keyPoints.length} key discussion points and examines the topic from ${perspectives.length} different perspectives.`;
    }

    private formatTimespan(history: any[]): string {
        if (history.length === 0) return 'No messages';
        const start = history[0].timestamp;
        const end = history[history.length - 1].timestamp;
        const diff = Math.abs(end.getTime() - start.getTime());
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `${hours}h ${minutes}m (${history.length} messages)`;
        }
        return `${minutes}m (${history.length} messages)`;
    }

    private formatKeyPoints(keyPoints: any[]): string {
        if (!keyPoints || keyPoints.length === 0) return 'No key points identified.';

        return keyPoints.map(point =>
            `### ${point.point}\n**Author**: ${point.author}\n**Context**: ${point.context}\n**Significance**: ${point.significance}\n`
        ).join('\n');
    }

    private formatSentiment(sentiment: any): string {
        if (!sentiment) return 'No sentiment analysis available.';

        let result = `**Overall Sentiment**: ${sentiment.overall || 'Neutral'}\n\n`;

        if (sentiment.byParticipant && Object.keys(sentiment.byParticipant).length > 0) {
            result += '**Sentiment by Participant**:\n';
            for (const [participant, participantSentiment] of Object.entries(sentiment.byParticipant)) {
                result += `- ${participant}: ${participantSentiment}\n`;
            }
            result += '\n';
        }

        if (sentiment.emotionalTrends && sentiment.emotionalTrends.length > 0) {
            result += '**Emotional Trends**:\n';
            for (const trend of sentiment.emotionalTrends) {
                result += `- ${trend}\n`;
            }
            result += '\n';
        }

        if (sentiment.toneShifts && sentiment.toneShifts.length > 0) {
            result += '**Tone Shifts**:\n';
            for (const shift of sentiment.toneShifts) {
                result += `- ${shift}\n`;
            }
        }

        return result;
    }

    private formatPerspectives(perspectives: any[]): string {
        if (!perspectives || perspectives.length === 0) return 'No perspective analysis available.';

        return perspectives.map(perspective =>
            `### ${perspective.type.charAt(0).toUpperCase() + perspective.type.slice(1)} Perspective\n${perspective.summary}\n\n**Key Insights**:\n${perspective.keyInsights.map((insight: string) => `- ${insight}`).join('\n')}\n\n**Implications**:\n${perspective.implications.map((implication: string) => `- ${implication}`).join('\n')}\n`
        ).join('\n');
    }

    /**
     * Format agreements and disagreements for the research document
     */
    private formatAgreementsDisagreements(agreements: any): string {
        if (!agreements) return 'No agreement/disagreement analysis available.';

        let result = '';

        if (agreements.agreements && agreements.agreements.length > 0) {
            result += '### Points of Agreement\n';
            for (const agreement of agreements.agreements) {
                const participants = agreement.participants ? agreement.participants.join(', ') : 'Unknown';
                result += `- **Topic**: ${agreement.topic || 'Unspecified'}\n  **Participants**: ${participants}\n  **Details**: ${agreement.details || 'No details provided'}\n\n`;
            }
        } else {
            result += '### Points of Agreement\nNo significant agreements identified.\n\n';
        }

        if (agreements.disagreements && agreements.disagreements.length > 0) {
            result += '### Points of Disagreement\n';
            for (const disagreement of agreements.disagreements) {
                const participants = disagreement.participants ? disagreement.participants.join(', ') : 'Unknown';
                result += `- **Topic**: ${disagreement.topic || 'Unspecified'}\n  **Participants**: ${participants}\n  **Details**: ${disagreement.details || 'No details provided'}\n\n`;
            }
        } else {
            result += '### Points of Disagreement\nNo significant disagreements identified.\n';
        }

        return result;
    }

    private formatRecommendations(recommendations: any): string {
        if (!recommendations) return 'No recommendations available.';

        return `${recommendations.summary}\n\n**Key Recommendations**:\n${recommendations.keyInsights.map((insight: string) => `- ${insight}`).join('\n')}`;
    }

    private generateNextSteps(context: any, perspectives: any[]): string {
        const recommendationsPerspective = perspectives.find(p => p.type === 'recommendations');
        if (!recommendationsPerspective) return 'No specific next steps identified.';

        return `Based on this research, the following next steps are recommended:\n\n${recommendationsPerspective.implications.map((implication: string) => `- ${implication}`).join('\n')}`;
    }

    private formatRelevantMessages(messages: any[]): string {
        if (!messages || messages.length === 0) return 'No relevant messages.';

        return messages.map(message =>
            `**${message.author}** (${new Date(message.timestamp).toLocaleString()}):\n${message.content}\n`
        ).join('\n---\n\n');
    }

    private async generateResearchSummary(context: ResearchContext): Promise<any> {
        try {
            const analysis = await this.openai.chat.completions.create({
                model: "gpt-4-turbo-preview",
                messages: [
                    {
                        role: "system",
                        content: "Generate a comprehensive research summary based on the conversation analysis. Include key findings, insights, and recommendations. Return a JSON object with fields: summary, keyFindings (array), insights (array), recommendations (array), and nextSteps (array)."
                    },
                    {
                        role: "user",
                        content: JSON.stringify({
                            researchFocus: context.researchFocus,
                            organizationInfo: context.metaContext.organizationInfo,
                            participants: Array.from(context.metaContext.participants.entries()).map(([name, data]) => ({ name, ...data })),
                            sentiment: context.sentiment,
                            keyPoints: context.keyPoints,
                            agreements: context.agreements,
                            disagreements: context.disagreements
                        })
                    }
                ]
            });

            const result = this.safeJsonParse(analysis.choices[0].message?.content || '{}', {});
            return result;
        } catch (error) {
            console.error('Error generating research summary:', error);
            return {
                summary: 'Unable to generate summary due to an error.',
                keyFindings: [],
                insights: [],
                recommendations: [],
                nextSteps: []
            };
        }
    }
} 