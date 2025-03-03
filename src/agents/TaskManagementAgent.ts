import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface Task {
    id: string;
    title: string;
    description: string;
    status: TaskStatus;
    priority: TaskPriority;
    dueDate?: Date;
    assignedTo?: string;
    dependencies?: string[];
    tags: string[];
    createdAt: Date;
    updatedAt: Date;
    completedAt?: Date;
    metadata: Record<string, any>;
}

export enum TaskStatus {
    PENDING = 'PENDING',
    IN_PROGRESS = 'IN_PROGRESS',
    BLOCKED = 'BLOCKED',
    COMPLETED = 'COMPLETED',
    CANCELLED = 'CANCELLED'
}

export enum TaskPriority {
    LOW = 'LOW',
    MEDIUM = 'MEDIUM',
    HIGH = 'HIGH',
    URGENT = 'URGENT'
}

export class TaskManagementAgent extends BaseAgent {
    private tasks: Map<string, Task>;
    private messageBus: MessageBus;

    constructor() {
        const config: AgentConfig = {
            id: 'task_manager',
            name: 'Task Management Agent',
            description: 'Manages tasks, workflows, and their lifecycle',
            capabilities: [
                'task_creation',
                'task_assignment',
                'task_prioritization',
                'workflow_management',
                'dependency_tracking',
                'status_updates'
            ],
            dependencies: []
        };

        super(config);
        this.tasks = new Map();
        this.messageBus = MessageBus.getInstance();
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
            case 'CREATE_TASK':
                await this.createTask(message.content);
                break;

            case 'UPDATE_TASK':
                await this.updateTask(message.content.taskId, message.content.updates);
                break;

            case 'DELETE_TASK':
                await this.deleteTask(message.content.taskId);
                break;

            case 'GET_TASK':
                await this.sendTaskDetails(message);
                break;

            case 'LIST_TASKS':
                await this.sendTaskList(message);
                break;

            case 'ASSIGN_TASK':
                await this.assignTask(message.content.taskId, message.content.assignee);
                break;

            case 'COMPLETE_TASK':
                await this.completeTask(message.content.taskId);
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createTask(taskData: Partial<Task>): Promise<void> {
        const taskId = this.generateTaskId();
        const now = new Date();

        const task: Task = {
            id: taskId,
            title: taskData.title || '',
            description: taskData.description || '',
            status: TaskStatus.PENDING,
            priority: taskData.priority || TaskPriority.MEDIUM,
            tags: taskData.tags || [],
            createdAt: now,
            updatedAt: now,
            metadata: taskData.metadata || {},
            ...taskData
        };

        this.tasks.set(taskId, task);

        await this.messageBus.broadcast({
            type: 'TASK_CREATED',
            content: { task },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateTask(taskId: string, updates: Partial<Task>): Promise<void> {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }

        const updatedTask: Task = {
            ...task,
            ...updates,
            updatedAt: new Date()
        };

        this.tasks.set(taskId, updatedTask);

        await this.messageBus.broadcast({
            type: 'TASK_UPDATED',
            content: { task: updatedTask },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async deleteTask(taskId: string): Promise<void> {
        if (!this.tasks.has(taskId)) {
            throw new Error(`Task ${taskId} not found`);
        }

        this.tasks.delete(taskId);

        await this.messageBus.broadcast({
            type: 'TASK_DELETED',
            content: { taskId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async assignTask(taskId: string, assignee: string): Promise<void> {
        await this.updateTask(taskId, {
            assignedTo: assignee,
            status: TaskStatus.IN_PROGRESS
        });
    }

    private async completeTask(taskId: string): Promise<void> {
        await this.updateTask(taskId, {
            status: TaskStatus.COMPLETED,
            completedAt: new Date()
        });

        // Check and update dependent tasks
        await this.updateDependentTasks(taskId);
    }

    private async updateDependentTasks(completedTaskId: string): Promise<void> {
        for (const task of this.tasks.values()) {
            if (task.dependencies?.includes(completedTaskId)) {
                const remainingDependencies = task.dependencies.filter(
                    depId => depId !== completedTaskId &&
                        this.tasks.get(depId)?.status !== TaskStatus.COMPLETED
                );

                if (remainingDependencies.length === 0) {
                    await this.updateTask(task.id, {
                        status: TaskStatus.PENDING,
                        dependencies: remainingDependencies
                    });
                }
            }
        }
    }

    private async sendTaskDetails(message: AgentMessage): Promise<void> {
        const taskId = message.content.taskId;
        const task = this.tasks.get(taskId);

        await this.messageBus.sendMessage({
            type: 'TASK_DETAILS_RESPONSE',
            content: { task },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendTaskList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let tasks = Array.from(this.tasks.values());

        // Apply filters
        if (filters.status) {
            tasks = tasks.filter(task => task.status === filters.status);
        }
        if (filters.assignee) {
            tasks = tasks.filter(task => task.assignedTo === filters.assignee);
        }
        if (filters.priority) {
            tasks = tasks.filter(task => task.priority === filters.priority);
        }
        if (filters.tags) {
            tasks = tasks.filter(task =>
                filters.tags.some((tag: string) => task.tags.includes(tag))
            );
        }

        await this.messageBus.sendMessage({
            type: 'TASK_LIST_RESPONSE',
            content: { tasks },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private generateTaskId(): string {
        return `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Task Management Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getTaskCount(): number {
        return this.tasks.size;
    }

    public getTasksByStatus(status: TaskStatus): Task[] {
        return Array.from(this.tasks.values())
            .filter(task => task.status === status);
    }

    public getTasksByAssignee(assignee: string): Task[] {
        return Array.from(this.tasks.values())
            .filter(task => task.assignedTo === assignee);
    }
} 