// Task priority levels
export enum Priority {
    URGENT = 'URGENT',
    HIGH = 'HIGH',
    MEDIUM = 'MEDIUM',
    LOW = 'LOW',
}

// Task status
export enum TaskStatus {
    TODO = 'TODO',
    IN_PROGRESS = 'IN_PROGRESS',
    WAITING = 'WAITING',
    DONE = 'DONE',
    ARCHIVED = 'ARCHIVED',
}

// Task categories
export enum TaskCategory {
    BUSINESS = 'BUSINESS',
    PERSONAL = 'PERSONAL',
    MEETING = 'MEETING',
    EMAIL = 'EMAIL',
    DECISION = 'DECISION',
}

// Base task interface
export interface Task {
    id: string;
    title: string;
    description: string;
    priority: Priority;
    status: TaskStatus;
    category: TaskCategory;
    dueDate?: Date;
    createdAt: Date;
    updatedAt: Date;
    assignedTo?: string;
    context?: Record<string, any>;
    parentTaskId?: string;
    subtasks?: Task[];
}

// Meeting interface
export interface Meeting {
    id: string;
    title: string;
    description: string;
    startTime: Date;
    endTime: Date;
    attendees: string[];
    location?: string;
    notes?: string;
    agenda?: string[];
    decisions?: string[];
    actionItems?: Task[];
}

// Email interface
export interface Email {
    id: string;
    subject: string;
    from: string;
    to: string[];
    cc?: string[];
    bcc?: string[];
    body: string;
    attachments?: string[];
    priority: Priority;
    status: 'DRAFT' | 'SENT' | 'RECEIVED';
    threadId?: string;
    createdAt: Date;
    sentAt?: Date;
}

// Decision interface
export interface Decision {
    id: string;
    title: string;
    description: string;
    options: DecisionOption[];
    criteria: DecisionCriterion[];
    status: 'PENDING' | 'MADE' | 'IMPLEMENTED';
    madeBy?: string;
    madeAt?: Date;
    context?: Record<string, any>;
    relatedTasks?: Task[];
}

// Decision option interface
export interface DecisionOption {
    id: string;
    title: string;
    description: string;
    pros: string[];
    cons: string[];
    risks: Risk[];
    score?: number;
}

// Decision criterion interface
export interface DecisionCriterion {
    id: string;
    name: string;
    weight: number;
    description: string;
}

// Risk interface
export interface Risk {
    id: string;
    description: string;
    probability: number; // 0-1
    impact: number; // 1-10
    mitigationStrategy?: string;
}

// User preferences interface
export interface UserPreferences {
    workingHours: {
        start: string; // HH:mm format
        end: string; // HH:mm format
    };
    timezone: string;
    notificationPreferences: {
        email: boolean;
        discord: boolean;
        urgentOnly: boolean;
    };
    autoResponders: {
        enabled: boolean;
        templates: Record<string, string>;
    };
    priorityThresholds: {
        urgent: number;
        high: number;
        medium: number;
    };
}

// AI Assistant Context
export interface AssistantContext {
    currentUser: string;
    userPreferences: UserPreferences;
    activeTask?: Task;
    activeMeeting?: Meeting;
    recentDecisions: Decision[];
    upcomingDeadlines: Task[];
    unreadEmails: Email[];
} 