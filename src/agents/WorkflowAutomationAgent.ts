import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Workflow {
    id: string;
    name: string;
    description: string;
    status: WorkflowStatus;
    type: WorkflowType;
    steps: WorkflowStep[];
    triggers: WorkflowTrigger[];
    variables: Record<string, WorkflowVariable>;
    metadata: Record<string, any>;
    createdAt: Date;
    updatedAt: Date;
    lastRunAt?: Date;
    nextRunAt?: Date;
}

export interface WorkflowStep {
    id: string;
    name: string;
    type: StepType;
    status: StepStatus;
    action: WorkflowAction;
    conditions: WorkflowCondition[];
    retryPolicy?: RetryPolicy;
    timeout?: number;
    dependencies: string[];
    metadata: Record<string, any>;
    startedAt?: Date;
    completedAt?: Date;
    error?: Error;
}

export interface WorkflowAction {
    type: ActionType;
    target: string;
    operation: string;
    parameters: Record<string, any>;
    expectedOutput?: Record<string, any>;
    timeout?: number;
}

export interface WorkflowCondition {
    type: ConditionType;
    field: string;
    operator: string;
    value: any;
    metadata: Record<string, any>;
}

export interface WorkflowTrigger {
    type: TriggerType;
    schedule?: string;
    event?: string;
    condition?: WorkflowCondition;
    metadata: Record<string, any>;
}

export interface WorkflowVariable {
    name: string;
    type: VariableType;
    value: any;
    scope: VariableScope;
    isSecret: boolean;
}

export interface RetryPolicy {
    maxAttempts: number;
    backoffType: BackoffType;
    initialInterval: number;
    maxInterval: number;
    multiplier: number;
}

export enum WorkflowStatus {
    DRAFT = 'DRAFT',
    ACTIVE = 'ACTIVE',
    RUNNING = 'RUNNING',
    PAUSED = 'PAUSED',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
    TERMINATED = 'TERMINATED'
}

export enum WorkflowType {
    SCHEDULED = 'SCHEDULED',
    EVENT_DRIVEN = 'EVENT_DRIVEN',
    MANUAL = 'MANUAL',
    HYBRID = 'HYBRID'
}

export enum StepType {
    TASK = 'TASK',
    DECISION = 'DECISION',
    NOTIFICATION = 'NOTIFICATION',
    INTEGRATION = 'INTEGRATION',
    SUBPROCESS = 'SUBPROCESS'
}

export enum StepStatus {
    PENDING = 'PENDING',
    RUNNING = 'RUNNING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
    SKIPPED = 'SKIPPED'
}

export enum ActionType {
    API_CALL = 'API_CALL',
    FUNCTION = 'FUNCTION',
    SCRIPT = 'SCRIPT',
    EMAIL = 'EMAIL',
    NOTIFICATION = 'NOTIFICATION',
    DATABASE = 'DATABASE'
}

export enum ConditionType {
    COMPARISON = 'COMPARISON',
    LOGICAL = 'LOGICAL',
    TEMPORAL = 'TEMPORAL',
    CUSTOM = 'CUSTOM'
}

export enum TriggerType {
    SCHEDULE = 'SCHEDULE',
    EVENT = 'EVENT',
    CONDITION = 'CONDITION',
    MANUAL = 'MANUAL'
}

export enum VariableType {
    STRING = 'STRING',
    NUMBER = 'NUMBER',
    BOOLEAN = 'BOOLEAN',
    OBJECT = 'OBJECT',
    ARRAY = 'ARRAY'
}

export enum VariableScope {
    WORKFLOW = 'WORKFLOW',
    STEP = 'STEP',
    GLOBAL = 'GLOBAL'
}

export enum BackoffType {
    FIXED = 'FIXED',
    EXPONENTIAL = 'EXPONENTIAL',
    LINEAR = 'LINEAR'
}

export class WorkflowAutomationAgent extends BaseAgent {
    private workflows: Map<string, Workflow>;
    private messageBus: MessageBus;
    private activeWorkflows: Set<string>;
    private scheduledTasks: Map<string, NodeJS.Timeout>;

    constructor() {
        const config: AgentConfig = {
            id: 'workflow_automation',
            name: 'Workflow Automation Agent',
            description: 'Manages automated workflows and processes',
            capabilities: [
                'workflow_execution',
                'process_automation',
                'task_scheduling',
                'event_handling',
                'condition_evaluation',
                'error_handling'
            ],
            dependencies: []
        };

        super(config);
        this.workflows = new Map();
        this.messageBus = MessageBus.getInstance();
        this.activeWorkflows = new Set();
        this.scheduledTasks = new Map();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.startScheduler();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'CREATE_WORKFLOW':
                await this.createWorkflow(message.content);
                break;

            case 'UPDATE_WORKFLOW':
                await this.updateWorkflow(
                    message.content.workflowId,
                    message.content.updates
                );
                break;

            case 'DELETE_WORKFLOW':
                await this.deleteWorkflow(message.content.workflowId);
                break;

            case 'START_WORKFLOW':
                await this.startWorkflow(
                    message.content.workflowId,
                    message.content.variables
                );
                break;

            case 'STOP_WORKFLOW':
                await this.stopWorkflow(message.content.workflowId);
                break;

            case 'GET_WORKFLOW':
                await this.sendWorkflowDetails(message);
                break;

            case 'LIST_WORKFLOWS':
                await this.sendWorkflowsList(message);
                break;

            case 'WORKFLOW_EVENT':
                await this.handleWorkflowEvent(message.content);
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createWorkflow(workflowData: Partial<Workflow>): Promise<void> {
        const workflowId = this.generateWorkflowId();
        const now = new Date();

        const workflow: Workflow = {
            id: workflowId,
            name: workflowData.name || '',
            description: workflowData.description || '',
            status: WorkflowStatus.DRAFT,
            type: workflowData.type || WorkflowType.MANUAL,
            steps: workflowData.steps || [],
            triggers: workflowData.triggers || [],
            variables: workflowData.variables || {},
            metadata: workflowData.metadata || {},
            createdAt: now,
            updatedAt: now,
            ...workflowData
        };

        this.workflows.set(workflowId, workflow);

        if (workflow.type === WorkflowType.SCHEDULED) {
            this.scheduleWorkflow(workflow);
        }

        await this.messageBus.broadcast({
            type: 'WORKFLOW_CREATED',
            content: { workflow },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateWorkflow(
        workflowId: string,
        updates: Partial<Workflow>
    ): Promise<void> {
        const workflow = this.workflows.get(workflowId);
        if (!workflow) {
            throw new Error(`Workflow ${workflowId} not found`);
        }

        const updatedWorkflow: Workflow = {
            ...workflow,
            ...updates,
            updatedAt: new Date()
        };

        this.workflows.set(workflowId, updatedWorkflow);

        // Update scheduling if needed
        if (
            workflow.type === WorkflowType.SCHEDULED ||
            updates.type === WorkflowType.SCHEDULED
        ) {
            this.unscheduleWorkflow(workflowId);
            this.scheduleWorkflow(updatedWorkflow);
        }

        await this.messageBus.broadcast({
            type: 'WORKFLOW_UPDATED',
            content: { workflow: updatedWorkflow },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async deleteWorkflow(workflowId: string): Promise<void> {
        const workflow = this.workflows.get(workflowId);
        if (!workflow) {
            throw new Error(`Workflow ${workflowId} not found`);
        }

        if (this.activeWorkflows.has(workflowId)) {
            await this.stopWorkflow(workflowId);
        }

        this.unscheduleWorkflow(workflowId);
        this.workflows.delete(workflowId);

        await this.messageBus.broadcast({
            type: 'WORKFLOW_DELETED',
            content: { workflowId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async startWorkflow(
        workflowId: string,
        variables?: Record<string, any>
    ): Promise<void> {
        const workflow = this.workflows.get(workflowId);
        if (!workflow) {
            throw new Error(`Workflow ${workflowId} not found`);
        }

        if (this.activeWorkflows.has(workflowId)) {
            throw new Error(`Workflow ${workflowId} is already running`);
        }

        try {
            this.activeWorkflows.add(workflowId);
            await this.updateWorkflow(workflowId, {
                status: WorkflowStatus.RUNNING,
                lastRunAt: new Date()
            });

            // Initialize workflow variables
            if (variables) {
                for (const [key, value] of Object.entries(variables)) {
                    if (workflow.variables[key]) {
                        workflow.variables[key].value = value;
                    }
                }
            }

            // Execute workflow steps
            await this.executeWorkflowSteps(workflow);

            await this.updateWorkflow(workflowId, {
                status: WorkflowStatus.COMPLETED
            });
        } catch (error) {
            console.error(`Error executing workflow ${workflowId}:`, error);
            await this.updateWorkflow(workflowId, {
                status: WorkflowStatus.FAILED
            });
            throw error;
        } finally {
            this.activeWorkflows.delete(workflowId);
        }
    }

    private async stopWorkflow(workflowId: string): Promise<void> {
        if (!this.activeWorkflows.has(workflowId)) {
            return;
        }

        await this.updateWorkflow(workflowId, {
            status: WorkflowStatus.TERMINATED
        });

        this.activeWorkflows.delete(workflowId);
    }

    private async executeWorkflowSteps(workflow: Workflow): Promise<void> {
        const executedSteps = new Set<string>();
        const pendingSteps = new Set(workflow.steps.map(step => step.id));

        while (pendingSteps.size > 0) {
            const readySteps = Array.from(pendingSteps).filter(stepId => {
                const step = workflow.steps.find(s => s.id === stepId);
                return step && this.areStepDependenciesMet(step, executedSteps);
            });

            if (readySteps.length === 0) {
                throw new Error('Workflow deadlock detected');
            }

            await Promise.all(
                readySteps.map(stepId => this.executeStep(workflow, stepId))
            );

            for (const stepId of readySteps) {
                executedSteps.add(stepId);
                pendingSteps.delete(stepId);
            }
        }
    }

    private areStepDependenciesMet(
        step: WorkflowStep,
        executedSteps: Set<string>
    ): boolean {
        return step.dependencies.every(depId => executedSteps.has(depId));
    }

    private async executeStep(
        workflow: Workflow,
        stepId: string
    ): Promise<void> {
        const step = workflow.steps.find(s => s.id === stepId);
        if (!step) {
            throw new Error(`Step ${stepId} not found in workflow ${workflow.id}`);
        }

        try {
            step.status = StepStatus.RUNNING;
            step.startedAt = new Date();

            if (await this.evaluateStepConditions(step, workflow)) {
                await this.executeAction(step.action, workflow);
                step.status = StepStatus.COMPLETED;
            } else {
                step.status = StepStatus.SKIPPED;
            }

            step.completedAt = new Date();
        } catch (error) {
            step.status = StepStatus.FAILED;
            step.error = error as Error;

            if (step.retryPolicy) {
                await this.handleStepRetry(step, workflow);
            } else {
                throw error;
            }
        }
    }

    private async evaluateStepConditions(
        step: WorkflowStep,
        workflow: Workflow
    ): Promise<boolean> {
        for (const condition of step.conditions) {
            if (!await this.evaluateCondition(condition, workflow)) {
                return false;
            }
        }
        return true;
    }

    private async evaluateCondition(
        condition: WorkflowCondition,
        workflow: Workflow
    ): Promise<boolean> {
        // Implement condition evaluation logic
        return true;
    }

    private async executeAction(
        action: WorkflowAction,
        workflow: Workflow
    ): Promise<void> {
        switch (action.type) {
            case ActionType.API_CALL:
                await this.executeApiCall(action);
                break;

            case ActionType.FUNCTION:
                await this.executeFunction(action);
                break;

            case ActionType.SCRIPT:
                await this.executeScript(action);
                break;

            case ActionType.EMAIL:
                await this.sendEmail(action);
                break;

            case ActionType.NOTIFICATION:
                await this.sendNotification(action);
                break;

            case ActionType.DATABASE:
                await this.executeDatabaseOperation(action);
                break;

            default:
                throw new Error(`Unknown action type: ${action.type}`);
        }
    }

    private async executeApiCall(action: WorkflowAction): Promise<void> {
        // Implement API call logic
    }

    private async executeFunction(action: WorkflowAction): Promise<void> {
        // Implement function execution logic
    }

    private async executeScript(action: WorkflowAction): Promise<void> {
        // Implement script execution logic
    }

    private async sendEmail(action: WorkflowAction): Promise<void> {
        await this.messageBus.sendMessage({
            type: 'SEND_COMMUNICATION',
            content: {
                type: 'EMAIL',
                ...action.parameters
            },
            recipient: 'communications',
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });
    }

    private async sendNotification(action: WorkflowAction): Promise<void> {
        await this.messageBus.sendMessage({
            type: 'SEND_COMMUNICATION',
            content: {
                type: 'NOTIFICATION',
                ...action.parameters
            },
            recipient: 'communications',
            priority: AgentPriority.HIGH,
            sender: this.config.id
        });
    }

    private async executeDatabaseOperation(action: WorkflowAction): Promise<void> {
        // Implement database operation logic
    }

    private async handleStepRetry(
        step: WorkflowStep,
        workflow: Workflow
    ): Promise<void> {
        const policy = step.retryPolicy as RetryPolicy;
        let attempt = 1;
        let delay = policy.initialInterval;

        while (attempt < policy.maxAttempts) {
            try {
                await new Promise(resolve => setTimeout(resolve, delay));
                await this.executeAction(step.action, workflow);
                step.status = StepStatus.COMPLETED;
                step.completedAt = new Date();
                return;
            } catch (error) {
                attempt++;
                step.error = error as Error;

                delay = this.calculateNextRetryDelay(
                    delay,
                    policy
                );
            }
        }

        throw step.error;
    }

    private calculateNextRetryDelay(
        currentDelay: number,
        policy: RetryPolicy
    ): number {
        let nextDelay: number;

        switch (policy.backoffType) {
            case BackoffType.FIXED:
                nextDelay = policy.initialInterval;
                break;

            case BackoffType.LINEAR:
                nextDelay = currentDelay + policy.initialInterval;
                break;

            case BackoffType.EXPONENTIAL:
                nextDelay = currentDelay * policy.multiplier;
                break;

            default:
                nextDelay = policy.initialInterval;
        }

        return Math.min(nextDelay, policy.maxInterval);
    }

    private async handleWorkflowEvent(eventData: any): Promise<void> {
        const eventTriggerWorkflows = Array.from(this.workflows.values())
            .filter(workflow =>
                workflow.status === WorkflowStatus.ACTIVE &&
                workflow.triggers.some(trigger =>
                    trigger.type === TriggerType.EVENT &&
                    trigger.event === eventData.type
                )
            );

        await Promise.all(
            eventTriggerWorkflows.map(workflow =>
                this.startWorkflow(workflow.id, eventData.variables)
            )
        );
    }

    private scheduleWorkflow(workflow: Workflow): void {
        const scheduleTrigger = workflow.triggers.find(
            trigger => trigger.type === TriggerType.SCHEDULE
        );

        if (scheduleTrigger?.schedule) {
            // Implement cron-like scheduling
            const timerId = setInterval(
                () => this.startWorkflow(workflow.id),
                this.parseSchedule(scheduleTrigger.schedule)
            );

            this.scheduledTasks.set(workflow.id, timerId);
        }
    }

    private unscheduleWorkflow(workflowId: string): void {
        const timerId = this.scheduledTasks.get(workflowId);
        if (timerId) {
            clearInterval(timerId);
            this.scheduledTasks.delete(workflowId);
        }
    }

    private parseSchedule(schedule: string): number {
        // Implement schedule parsing logic
        return 60000; // Default to 1 minute
    }

    private startScheduler(): void {
        // Initialize scheduled workflows
        for (const workflow of this.workflows.values()) {
            if (
                workflow.status === WorkflowStatus.ACTIVE &&
                workflow.type === WorkflowType.SCHEDULED
            ) {
                this.scheduleWorkflow(workflow);
            }
        }
    }

    private async sendWorkflowDetails(message: AgentMessage): Promise<void> {
        const workflowId = message.content.workflowId;
        const workflow = this.workflows.get(workflowId);

        await this.messageBus.sendMessage({
            type: 'WORKFLOW_DETAILS_RESPONSE',
            content: { workflow },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendWorkflowsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let workflows = Array.from(this.workflows.values());

        // Apply filters
        if (filters.type) {
            workflows = workflows.filter(
                workflow => workflow.type === filters.type
            );
        }
        if (filters.status) {
            workflows = workflows.filter(
                workflow => workflow.status === filters.status
            );
        }

        await this.messageBus.sendMessage({
            type: 'WORKFLOWS_LIST_RESPONSE',
            content: { workflows },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateWorkflowId(): string {
        return `workflow-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Workflow Automation Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        // Stop all active workflows
        for (const workflowId of this.activeWorkflows) {
            await this.stopWorkflow(workflowId);
        }

        // Clear all scheduled tasks
        for (const timerId of this.scheduledTasks.values()) {
            clearInterval(timerId);
        }
        this.scheduledTasks.clear();

        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getWorkflowCount(): number {
        return this.workflows.size;
    }

    public getActiveWorkflowCount(): number {
        return this.activeWorkflows.size;
    }

    public getWorkflowsByType(type: WorkflowType): Workflow[] {
        return Array.from(this.workflows.values())
            .filter(workflow => workflow.type === type);
    }

    public getWorkflowsByStatus(status: WorkflowStatus): Workflow[] {
        return Array.from(this.workflows.values())
            .filter(workflow => workflow.status === status);
    }
} 