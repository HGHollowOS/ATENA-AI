import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Decision {
    id: string;
    context: DecisionContext;
    options: DecisionOption[];
    criteria: DecisionCriterion[];
    recommendation: Recommendation;
    status: DecisionStatus;
    deadline?: Date;
    stakeholders: string[];
    metadata: Record<string, any>;
    createdAt: Date;
    updatedAt: Date;
}

export interface DecisionContext {
    type: DecisionType;
    description: string;
    scope: string;
    constraints: string[];
    relevantData: Record<string, any>;
    priority: DecisionPriority;
}

export interface DecisionOption {
    id: string;
    title: string;
    description: string;
    pros: string[];
    cons: string[];
    impact: Impact[];
    feasibility: number;
    risk: Risk;
    cost?: number;
    timeline?: string;
    score?: number;
}

export interface DecisionCriterion {
    id: string;
    name: string;
    description: string;
    weight: number;
    evaluationType: CriterionEvaluationType;
    threshold?: number;
    isRequired: boolean;
}

export interface Impact {
    area: string;
    description: string;
    severity: ImpactSeverity;
    probability: number;
    timeframe: string;
}

export interface Risk {
    level: RiskLevel;
    factors: string[];
    mitigations: string[];
}

export interface Recommendation {
    optionId: string;
    rationale: string[];
    confidenceScore: number;
    alternativeOptions: string[];
    considerations: string[];
    nextSteps: string[];
    validUntil?: Date;
}

export enum DecisionType {
    STRATEGIC = 'STRATEGIC',
    TACTICAL = 'TACTICAL',
    OPERATIONAL = 'OPERATIONAL',
    TECHNICAL = 'TECHNICAL',
    RESOURCE = 'RESOURCE'
}

export enum DecisionStatus {
    PENDING = 'PENDING',
    ANALYZING = 'ANALYZING',
    RECOMMENDED = 'RECOMMENDED',
    DECIDED = 'DECIDED',
    IMPLEMENTED = 'IMPLEMENTED',
    CANCELLED = 'CANCELLED'
}

export enum DecisionPriority {
    LOW = 'LOW',
    MEDIUM = 'MEDIUM',
    HIGH = 'HIGH',
    CRITICAL = 'CRITICAL'
}

export enum CriterionEvaluationType {
    NUMERIC = 'NUMERIC',
    BOOLEAN = 'BOOLEAN',
    SCALE = 'SCALE',
    CUSTOM = 'CUSTOM'
}

export enum ImpactSeverity {
    NEGLIGIBLE = 'NEGLIGIBLE',
    MINOR = 'MINOR',
    MODERATE = 'MODERATE',
    MAJOR = 'MAJOR',
    SEVERE = 'SEVERE'
}

export enum RiskLevel {
    MINIMAL = 'MINIMAL',
    LOW = 'LOW',
    MODERATE = 'MODERATE',
    HIGH = 'HIGH',
    EXTREME = 'EXTREME'
}

export class DecisionSupportAgent extends BaseAgent {
    private decisions: Map<string, Decision>;
    private messageBus: MessageBus;
    private analysisInProgress: Set<string>;

    constructor() {
        const config: AgentConfig = {
            id: 'decision_support',
            name: 'Decision Support Agent',
            description: 'Analyzes data and provides decision recommendations',
            capabilities: [
                'decision_analysis',
                'risk_assessment',
                'impact_analysis',
                'option_evaluation',
                'recommendation_generation',
                'criteria_weighting'
            ],
            dependencies: []
        };

        super(config);
        this.decisions = new Map();
        this.messageBus = MessageBus.getInstance();
        this.analysisInProgress = new Set();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'CREATE_DECISION':
                await this.createDecision(message.content);
                break;

            case 'UPDATE_DECISION':
                await this.updateDecision(
                    message.content.decisionId,
                    message.content.updates
                );
                break;

            case 'ANALYZE_DECISION':
                await this.analyzeDecision(message.content.decisionId);
                break;

            case 'GET_DECISION':
                await this.sendDecisionDetails(message);
                break;

            case 'LIST_DECISIONS':
                await this.sendDecisionsList(message);
                break;

            case 'ADD_OPTION':
                await this.addOption(
                    message.content.decisionId,
                    message.content.option
                );
                break;

            case 'UPDATE_CRITERIA':
                await this.updateCriteria(
                    message.content.decisionId,
                    message.content.criteria
                );
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createDecision(decisionData: Partial<Decision>): Promise<void> {
        const decisionId = this.generateDecisionId();
        const now = new Date();

        const decision: Decision = {
            id: decisionId,
            context: decisionData.context || {
                type: DecisionType.OPERATIONAL,
                description: '',
                scope: '',
                constraints: [],
                relevantData: {},
                priority: DecisionPriority.MEDIUM
            },
            options: decisionData.options || [],
            criteria: decisionData.criteria || [],
            recommendation: decisionData.recommendation || {
                optionId: '',
                rationale: [],
                confidenceScore: 0,
                alternativeOptions: [],
                considerations: [],
                nextSteps: []
            },
            status: DecisionStatus.PENDING,
            stakeholders: decisionData.stakeholders || [],
            metadata: decisionData.metadata || {},
            createdAt: now,
            updatedAt: now,
            ...decisionData
        };

        this.decisions.set(decisionId, decision);

        await this.messageBus.broadcast({
            type: 'DECISION_CREATED',
            content: { decision },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });

        // Start analysis if there are options and criteria
        if (decision.options.length > 0 && decision.criteria.length > 0) {
            await this.analyzeDecision(decisionId);
        }
    }

    private async updateDecision(
        decisionId: string,
        updates: Partial<Decision>
    ): Promise<void> {
        const decision = this.decisions.get(decisionId);
        if (!decision) {
            throw new Error(`Decision ${decisionId} not found`);
        }

        const updatedDecision: Decision = {
            ...decision,
            ...updates,
            updatedAt: new Date()
        };

        this.decisions.set(decisionId, updatedDecision);

        await this.messageBus.broadcast({
            type: 'DECISION_UPDATED',
            content: { decision: updatedDecision },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });

        // Re-analyze if significant changes were made
        if (
            updates.options ||
            updates.criteria ||
            updates.context?.constraints
        ) {
            await this.analyzeDecision(decisionId);
        }
    }

    private async addOption(
        decisionId: string,
        option: DecisionOption
    ): Promise<void> {
        const decision = this.decisions.get(decisionId);
        if (!decision) {
            throw new Error(`Decision ${decisionId} not found`);
        }

        const updatedOptions = [...decision.options, option];
        await this.updateDecision(decisionId, { options: updatedOptions });
    }

    private async updateCriteria(
        decisionId: string,
        criteria: DecisionCriterion[]
    ): Promise<void> {
        const decision = this.decisions.get(decisionId);
        if (!decision) {
            throw new Error(`Decision ${decisionId} not found`);
        }

        await this.updateDecision(decisionId, { criteria });
    }

    private async analyzeDecision(decisionId: string): Promise<void> {
        if (this.analysisInProgress.has(decisionId)) {
            return;
        }

        const decision = this.decisions.get(decisionId);
        if (!decision) {
            throw new Error(`Decision ${decisionId} not found`);
        }

        try {
            this.analysisInProgress.add(decisionId);
            await this.updateDecision(decisionId, { status: DecisionStatus.ANALYZING });

            // Evaluate each option against the criteria
            const evaluatedOptions = await Promise.all(
                decision.options.map(async option => {
                    const evaluatedOption = { ...option };
                    evaluatedOption.score = await this.evaluateOption(option, decision.criteria);
                    return evaluatedOption;
                })
            );

            // Sort options by score
            const sortedOptions = evaluatedOptions.sort((a, b) =>
                (b.score || 0) - (a.score || 0)
            );

            // Generate recommendation
            const recommendation: Recommendation = {
                optionId: sortedOptions[0].id,
                rationale: this.generateRationale(sortedOptions[0], decision),
                confidenceScore: this.calculateConfidenceScore(sortedOptions[0], decision),
                alternativeOptions: sortedOptions.slice(1, 3).map(opt => opt.id),
                considerations: this.generateConsiderations(sortedOptions[0], decision),
                nextSteps: this.generateNextSteps(sortedOptions[0], decision)
            };

            await this.updateDecision(decisionId, {
                options: evaluatedOptions,
                recommendation,
                status: DecisionStatus.RECOMMENDED
            });

        } catch (error) {
            console.error(`Error analyzing decision ${decisionId}:`, error);
            await this.handleError(error as Error);
        } finally {
            this.analysisInProgress.delete(decisionId);
        }
    }

    private async evaluateOption(
        option: DecisionOption,
        criteria: DecisionCriterion[]
    ): Promise<number> {
        let totalScore = 0;
        let totalWeight = 0;

        for (const criterion of criteria) {
            const score = await this.evaluateCriterion(option, criterion);
            totalScore += score * criterion.weight;
            totalWeight += criterion.weight;
        }

        return totalWeight > 0 ? totalScore / totalWeight : 0;
    }

    private async evaluateCriterion(
        option: DecisionOption,
        criterion: DecisionCriterion
    ): Promise<number> {
        // Implement criterion-specific evaluation logic
        switch (criterion.evaluationType) {
            case CriterionEvaluationType.NUMERIC:
                return this.evaluateNumericCriterion(option, criterion);

            case CriterionEvaluationType.BOOLEAN:
                return this.evaluateBooleanCriterion(option, criterion);

            case CriterionEvaluationType.SCALE:
                return this.evaluateScaleCriterion(option, criterion);

            case CriterionEvaluationType.CUSTOM:
                return this.evaluateCustomCriterion(option, criterion);

            default:
                return 0;
        }
    }

    private evaluateNumericCriterion(
        option: DecisionOption,
        criterion: DecisionCriterion
    ): number {
        // Implement numeric evaluation logic
        return 0;
    }

    private evaluateBooleanCriterion(
        option: DecisionOption,
        criterion: DecisionCriterion
    ): number {
        // Implement boolean evaluation logic
        return 0;
    }

    private evaluateScaleCriterion(
        option: DecisionOption,
        criterion: DecisionCriterion
    ): number {
        // Implement scale evaluation logic
        return 0;
    }

    private evaluateCustomCriterion(
        option: DecisionOption,
        criterion: DecisionCriterion
    ): number {
        // Implement custom evaluation logic
        return 0;
    }

    private generateRationale(
        option: DecisionOption,
        decision: Decision
    ): string[] {
        // Implement rationale generation logic
        return [];
    }

    private calculateConfidenceScore(
        option: DecisionOption,
        decision: Decision
    ): number {
        // Implement confidence score calculation logic
        return 0;
    }

    private generateConsiderations(
        option: DecisionOption,
        decision: Decision
    ): string[] {
        // Implement considerations generation logic
        return [];
    }

    private generateNextSteps(
        option: DecisionOption,
        decision: Decision
    ): string[] {
        // Implement next steps generation logic
        return [];
    }

    private async sendDecisionDetails(message: AgentMessage): Promise<void> {
        const decisionId = message.content.decisionId;
        const decision = this.decisions.get(decisionId);

        await this.messageBus.sendMessage({
            type: 'DECISION_DETAILS_RESPONSE',
            content: { decision },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendDecisionsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let decisions = Array.from(this.decisions.values());

        // Apply filters
        if (filters.type) {
            decisions = decisions.filter(
                decision => decision.context.type === filters.type
            );
        }
        if (filters.status) {
            decisions = decisions.filter(
                decision => decision.status === filters.status
            );
        }
        if (filters.priority) {
            decisions = decisions.filter(
                decision => decision.context.priority === filters.priority
            );
        }
        if (filters.stakeholder) {
            decisions = decisions.filter(decision =>
                decision.stakeholders.includes(filters.stakeholder)
            );
        }

        await this.messageBus.sendMessage({
            type: 'DECISIONS_LIST_RESPONSE',
            content: { decisions },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateDecisionId(): string {
        return `decision-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Decision Support Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getDecisionCount(): number {
        return this.decisions.size;
    }

    public getDecisionsByType(type: DecisionType): Decision[] {
        return Array.from(this.decisions.values())
            .filter(decision => decision.context.type === type);
    }

    public getDecisionsByStatus(status: DecisionStatus): Decision[] {
        return Array.from(this.decisions.values())
            .filter(decision => decision.status === status);
    }
} 