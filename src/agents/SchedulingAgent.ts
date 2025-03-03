import { BaseAgent, AgentMessage, AgentConfig, AgentStatus, AgentPriority } from '../core/types/Agent';
import { MessageBus } from '../core/MessageBus';

export interface CalendarEvent {
    id: string;
    title: string;
    description: string;
    startTime: Date;
    endTime: Date;
    location?: string;
    attendees: Attendee[];
    organizer: string;
    status: EventStatus;
    type: EventType;
    recurrence?: RecurrenceRule;
    conferenceDetails?: ConferenceDetails;
    reminders: Reminder[];
    metadata: Record<string, any>;
    createdAt: Date;
    updatedAt: Date;
}

export interface Attendee {
    email: string;
    name?: string;
    status: AttendeeStatus;
    optional?: boolean;
    responseTime?: Date;
}

export interface ConferenceDetails {
    type: ConferenceType;
    url: string;
    id: string;
    password?: string;
    provider: string;
    metadata: Record<string, any>;
}

export interface RecurrenceRule {
    frequency: RecurrenceFrequency;
    interval: number;
    until?: Date;
    count?: number;
    byDay?: string[];
    byMonth?: number[];
    byMonthDay?: number[];
    excludeDates?: Date[];
}

export interface Reminder {
    type: ReminderType;
    minutes: number;
    status: ReminderStatus;
}

export enum EventStatus {
    TENTATIVE = 'TENTATIVE',
    CONFIRMED = 'CONFIRMED',
    CANCELLED = 'CANCELLED'
}

export enum EventType {
    MEETING = 'MEETING',
    APPOINTMENT = 'APPOINTMENT',
    TASK = 'TASK',
    OUT_OF_OFFICE = 'OUT_OF_OFFICE',
    HOLIDAY = 'HOLIDAY'
}

export enum AttendeeStatus {
    NEEDS_ACTION = 'NEEDS_ACTION',
    ACCEPTED = 'ACCEPTED',
    TENTATIVE = 'TENTATIVE',
    DECLINED = 'DECLINED'
}

export enum ConferenceType {
    MEET = 'MEET',
    ZOOM = 'ZOOM',
    TEAMS = 'TEAMS',
    WEBEX = 'WEBEX'
}

export enum RecurrenceFrequency {
    DAILY = 'DAILY',
    WEEKLY = 'WEEKLY',
    MONTHLY = 'MONTHLY',
    YEARLY = 'YEARLY'
}

export enum ReminderType {
    EMAIL = 'EMAIL',
    NOTIFICATION = 'NOTIFICATION',
    SMS = 'SMS'
}

export enum ReminderStatus {
    PENDING = 'PENDING',
    SENT = 'SENT',
    FAILED = 'FAILED'
}

export class SchedulingAgent extends BaseAgent {
    private events: Map<string, CalendarEvent>;
    private messageBus: MessageBus;
    private reminderTimers: Map<string, NodeJS.Timeout>;

    constructor() {
        const config: AgentConfig = {
            id: 'scheduler',
            name: 'Scheduling Agent',
            description: 'Manages calendar events and meeting coordination',
            capabilities: [
                'calendar_management',
                'meeting_scheduling',
                'availability_checking',
                'reminder_management',
                'recurrence_handling',
                'conference_coordination'
            ],
            dependencies: []
        };

        super(config);
        this.events = new Map();
        this.messageBus = MessageBus.getInstance();
        this.reminderTimers = new Map();
    }

    public initialize(): Promise<void> {
        return new Promise((resolve) => {
            this.messageBus.registerAgent(this);
            this.startReminderCheck();
            this.updateState({ status: AgentStatus.IDLE });
            resolve();
        });
    }

    public async processMessage(message: AgentMessage): Promise<void> {
        switch (message.type) {
            case 'CREATE_EVENT':
                await this.createEvent(message.content);
                break;

            case 'UPDATE_EVENT':
                await this.updateEvent(
                    message.content.eventId,
                    message.content.updates
                );
                break;

            case 'DELETE_EVENT':
                await this.deleteEvent(message.content.eventId);
                break;

            case 'GET_EVENT':
                await this.sendEventDetails(message);
                break;

            case 'LIST_EVENTS':
                await this.sendEventsList(message);
                break;

            case 'CHECK_AVAILABILITY':
                await this.checkAvailability(message);
                break;

            case 'UPDATE_ATTENDEE_STATUS':
                await this.updateAttendeeStatus(
                    message.content.eventId,
                    message.content.attendee
                );
                break;

            default:
                console.warn(`Unknown message type: ${message.type}`);
        }
    }

    private async createEvent(eventData: Partial<CalendarEvent>): Promise<void> {
        const eventId = this.generateEventId();
        const now = new Date();

        const event: CalendarEvent = {
            id: eventId,
            title: eventData.title || '',
            description: eventData.description || '',
            startTime: eventData.startTime || now,
            endTime: eventData.endTime || new Date(now.getTime() + 3600000), // Default 1 hour
            attendees: eventData.attendees || [],
            organizer: eventData.organizer || 'system',
            status: EventStatus.TENTATIVE,
            type: eventData.type || EventType.MEETING,
            reminders: eventData.reminders || [],
            metadata: eventData.metadata || {},
            createdAt: now,
            updatedAt: now,
            ...eventData
        };

        this.events.set(eventId, event);
        this.setupEventReminders(event);

        await this.messageBus.broadcast({
            type: 'EVENT_CREATED',
            content: { event },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateEvent(
        eventId: string,
        updates: Partial<CalendarEvent>
    ): Promise<void> {
        const event = this.events.get(eventId);
        if (!event) {
            throw new Error(`Event ${eventId} not found`);
        }

        const updatedEvent: CalendarEvent = {
            ...event,
            ...updates,
            updatedAt: new Date()
        };

        this.events.set(eventId, updatedEvent);
        this.setupEventReminders(updatedEvent);

        await this.messageBus.broadcast({
            type: 'EVENT_UPDATED',
            content: { event: updatedEvent },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async deleteEvent(eventId: string): Promise<void> {
        const event = this.events.get(eventId);
        if (!event) {
            throw new Error(`Event ${eventId} not found`);
        }

        this.events.delete(eventId);
        this.clearEventReminders(eventId);

        await this.messageBus.broadcast({
            type: 'EVENT_DELETED',
            content: { eventId },
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async updateAttendeeStatus(
        eventId: string,
        attendeeUpdate: Partial<Attendee>
    ): Promise<void> {
        const event = this.events.get(eventId);
        if (!event) {
            throw new Error(`Event ${eventId} not found`);
        }

        const attendeeIndex = event.attendees.findIndex(
            a => a.email === attendeeUpdate.email
        );

        if (attendeeIndex === -1) {
            throw new Error(`Attendee ${attendeeUpdate.email} not found in event ${eventId}`);
        }

        const updatedAttendees = [...event.attendees];
        updatedAttendees[attendeeIndex] = {
            ...updatedAttendees[attendeeIndex],
            ...attendeeUpdate,
            responseTime: new Date()
        };

        await this.updateEvent(eventId, { attendees: updatedAttendees });
    }

    private async sendEventDetails(message: AgentMessage): Promise<void> {
        const eventId = message.content.eventId;
        const event = this.events.get(eventId);

        await this.messageBus.sendMessage({
            type: 'EVENT_DETAILS_RESPONSE',
            content: { event },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async sendEventsList(message: AgentMessage): Promise<void> {
        const filters = message.content.filters || {};
        let events = Array.from(this.events.values());

        // Apply filters
        if (filters.startTime) {
            events = events.filter(event => event.startTime >= filters.startTime);
        }
        if (filters.endTime) {
            events = events.filter(event => event.endTime <= filters.endTime);
        }
        if (filters.type) {
            events = events.filter(event => event.type === filters.type);
        }
        if (filters.status) {
            events = events.filter(event => event.status === filters.status);
        }
        if (filters.attendee) {
            events = events.filter(event =>
                event.attendees.some(a => a.email === filters.attendee)
            );
        }

        await this.messageBus.sendMessage({
            type: 'EVENTS_LIST_RESPONSE',
            content: { events },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private async checkAvailability(message: AgentMessage): Promise<void> {
        const { startTime, endTime, attendees } = message.content;
        const conflicts = new Map<string, CalendarEvent[]>();

        for (const attendee of attendees) {
            const attendeeEvents = Array.from(this.events.values()).filter(event =>
                event.attendees.some(a => a.email === attendee) &&
                event.status !== EventStatus.CANCELLED &&
                this.eventsOverlap(event, startTime, endTime)
            );

            if (attendeeEvents.length > 0) {
                conflicts.set(attendee, attendeeEvents);
            }
        }

        await this.messageBus.sendMessage({
            type: 'AVAILABILITY_RESPONSE',
            content: {
                available: conflicts.size === 0,
                conflicts: Object.fromEntries(conflicts)
            },
            recipient: message.sender,
            correlationId: message.id,
            priority: AgentPriority.MEDIUM,
            sender: this.config.id
        });
    }

    private eventsOverlap(
        event: CalendarEvent,
        startTime: Date,
        endTime: Date
    ): boolean {
        return (
            (event.startTime <= startTime && event.endTime > startTime) ||
            (event.startTime < endTime && event.endTime >= endTime) ||
            (event.startTime >= startTime && event.endTime <= endTime)
        );
    }

    private setupEventReminders(event: CalendarEvent): void {
        // Clear existing reminders for this event
        this.clearEventReminders(event.id);

        // Setup new reminders
        for (const reminder of event.reminders) {
            if (reminder.status === ReminderStatus.PENDING) {
                const reminderTime = new Date(
                    event.startTime.getTime() - reminder.minutes * 60000
                );

                if (reminderTime > new Date()) {
                    const timerId = setTimeout(async () => {
                        await this.sendReminder(event, reminder);
                    }, reminderTime.getTime() - Date.now());

                    this.reminderTimers.set(
                        `${event.id}-${reminder.type}-${reminder.minutes}`,
                        timerId
                    );
                }
            }
        }
    }

    private clearEventReminders(eventId: string): void {
        for (const [key, timerId] of this.reminderTimers.entries()) {
            if (key.startsWith(eventId)) {
                clearTimeout(timerId);
                this.reminderTimers.delete(key);
            }
        }
    }

    private async sendReminder(event: CalendarEvent, reminder: Reminder): Promise<void> {
        try {
            await this.messageBus.sendMessage({
                type: 'SEND_COMMUNICATION',
                content: {
                    type: reminder.type,
                    recipients: event.attendees.map(a => a.email),
                    subject: `Reminder: ${event.title}`,
                    content: `Your event "${event.title}" starts in ${reminder.minutes} minutes.`,
                    metadata: {
                        eventId: event.id,
                        reminderType: reminder.type
                    }
                },
                priority: AgentPriority.HIGH,
                sender: this.config.id,
                recipient: 'communications'
            });

            // Update reminder status
            const updatedReminders = event.reminders.map(r =>
                r === reminder ? { ...r, status: ReminderStatus.SENT } : r
            );

            await this.updateEvent(event.id, { reminders: updatedReminders });
        } catch (error) {
            console.error(`Failed to send reminder for event ${event.id}:`, error);

            // Update reminder status to failed
            const updatedReminders = event.reminders.map(r =>
                r === reminder ? { ...r, status: ReminderStatus.FAILED } : r
            );

            await this.updateEvent(event.id, { reminders: updatedReminders });
        }
    }

    private startReminderCheck(): void {
        // Check for missed reminders every minute
        setInterval(() => {
            const now = new Date();
            for (const event of this.events.values()) {
                for (const reminder of event.reminders) {
                    if (reminder.status === ReminderStatus.PENDING) {
                        const reminderTime = new Date(
                            event.startTime.getTime() - reminder.minutes * 60000
                        );

                        if (reminderTime <= now && reminderTime > new Date(now.getTime() - 300000)) {
                            // Send reminder if it's due and not more than 5 minutes late
                            this.sendReminder(event, reminder)
                                .catch(error => console.error('Failed to send reminder:', error));
                        }
                    }
                }
            }
        }, 60000);
    }

    private generateEventId(): string {
        return `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    public async handleError(error: Error): Promise<void> {
        console.error('Scheduling Agent error:', error);
        await this.updateState({
            status: AgentStatus.ERROR,
            errorCount: this.state.errorCount + 1
        });
    }

    public async shutdown(): Promise<void> {
        // Clear all reminder timers
        for (const timerId of this.reminderTimers.values()) {
            clearTimeout(timerId);
        }
        this.reminderTimers.clear();

        this.messageBus.unregisterAgent(this.config.id);
        await this.updateState({ status: AgentStatus.TERMINATED });
    }

    public getEventCount(): number {
        return this.events.size;
    }

    public getUpcomingEvents(limit: number = 10): CalendarEvent[] {
        const now = new Date();
        return Array.from(this.events.values())
            .filter(event => event.startTime > now)
            .sort((a, b) => a.startTime.getTime() - b.startTime.getTime())
            .slice(0, limit);
    }

    public getEventsByTimeRange(startTime: Date, endTime: Date): CalendarEvent[] {
        return Array.from(this.events.values())
            .filter(event =>
                event.startTime >= startTime &&
                event.endTime <= endTime
            );
    }
} 