export enum Priority {
    URGENT = 'URGENT',
    HIGH = 'HIGH',
    MEDIUM = 'MEDIUM',
    LOW = 'LOW'
}

export enum TaskStatus {
    TODO = 'TODO',
    IN_PROGRESS = 'IN_PROGRESS',
    DONE = 'DONE'
}

export enum TaskCategory {
    WORK = 'WORK',
    PERSONAL = 'PERSONAL',
    MEETING = 'MEETING',
    EMAIL = 'EMAIL'
}

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
}

export interface Meeting {
    id: string;
    title: string;
    description: string;
    startTime: Date;
    endTime: Date;
    attendees: string[];
    location?: string;
    agenda: string[];
    decisions: Decision[];
    actionItems: Task[];
}

export interface Email {
    id: string;
    subject: string;
    from: string;
    to: string[];
    body: string;
    priority: Priority;
    status: string;
    createdAt: Date;
}

export interface Decision {
    id: string;
    title: string;
    description: string;
    createdAt: Date;
    context: string;
    outcome: string;
    stakeholders: string[];
}

export interface UserPreferences {
    workingHours: {
        start: string;
        end: string;
    };
    timezone: string;
    notificationPreferences: {
        email: boolean;
        discord: boolean;
        urgentOnly: boolean;
    };
    autoResponders: {
        enabled: boolean;
        templates: {
            outOfOffice: string;
            busy: string;
            default: string;
        };
    };
    priorityThresholds: {
        urgent: number;
        high: number;
        medium: number;
    };
}

export interface AssistantContext {
    currentUser: string;
    userPreferences: UserPreferences;
    recentDecisions: Decision[];
    upcomingDeadlines: Task[];
    unreadEmails: Email[];
    lastChecked: {
        emails: Date;
        calendar: Date;
        linkedin: Date;
        news: Date;
    };
    relevantNews: NewsArticle[];
}

export interface LinkedInPost {
    authorId: string;
    content: string;
    mediaUrls?: string[];
}

export interface LinkedInNotification {
    id: string;
    type: string;
    timestamp: Date;
    message: string;
    actor?: {
        id: string;
        name?: string;
    };
    entity?: {
        id: string;
        type: string;
    };
}

export interface NewsArticle {
    id: string;
    title: string;
    description: string;
    url: string;
    publishedAt: Date;
    relevanceScore: number;
    relatedTopics: string[];
} 