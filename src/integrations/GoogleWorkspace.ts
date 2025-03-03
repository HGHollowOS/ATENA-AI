import { google, calendar_v3, docs_v1, gmail_v1, Auth, drive_v3 } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import { Email, Meeting, Task, Priority, TaskStatus, TaskCategory } from '../types';
import { config } from '../config/config';
import * as fs from 'fs';
import * as path from 'path';

export class GoogleWorkspaceIntegration {
    private gmail: gmail_v1.Gmail;
    private calendar: calendar_v3.Calendar;
    private drive: drive_v3.Drive;
    private docs: docs_v1.Docs;
    private auth: OAuth2Client;
    private tasksClient: any; // Using any temporarily until we have proper types
    private authorized: boolean = false;
    private folderId: string | null = null;

    constructor(credentials: {
        clientId: string;
        clientSecret: string;
        redirectUri: string;
        refreshToken: string;
    }) {
        this.auth = new OAuth2Client(
            credentials.clientId,
            credentials.clientSecret,
            credentials.redirectUri
        );
        this.auth.setCredentials({ refresh_token: credentials.refreshToken });

        this.gmail = google.gmail({ version: 'v1', auth: this.auth });
        this.calendar = google.calendar({ version: 'v3', auth: this.auth });
        this.drive = google.drive({ version: 'v3', auth: this.auth });
        this.docs = google.docs({ version: 'v1', auth: this.auth });
        this.tasksClient = google.tasks({ version: 'v1', auth: this.auth });

        this.initialize().catch(err => {
            console.error('Error initializing Google Workspace integration:', err);
        });
    }

    public async initialize(): Promise<void> {
        try {
            // Initialize Google Calendar API
            this.calendar = google.calendar({ version: 'v3', auth: this.auth });
            console.log('Google Calendar API initialized');

            // Initialize Google Drive API
            this.drive = google.drive({ version: 'v3', auth: this.auth });
            console.log('Google Drive API initialized');

            // Initialize Google Docs API
            this.docs = google.docs({ version: 'v1', auth: this.auth });
            console.log('Google Docs API initialized');

            // Initialize Google Tasks API
            this.tasksClient = google.tasks({ version: 'v1', auth: this.auth });
            console.log('Google Tasks API initialized');

            // Check if credentials file exists
            const credentialsPath = path.resolve(process.cwd(), config.googleWorkspace.credentials);

            if (!fs.existsSync(credentialsPath)) {
                console.warn('Google Workspace credentials file not found. Document creation will be simulated.');
                return;
            }

            // Verify authorization by making a test API call
            await this.calendar.calendarList.list();
            this.authorized = true;

            // Find or create the research folder
            await this.findOrCreateFolder();

            console.log('Google Workspace integration initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Google Workspace:', error);
        }
    }

    public async testGmailConnection(): Promise<boolean> {
        try {
            await this.gmail.users.getProfile({ userId: 'me' });
            return true;
        } catch (error) {
            console.error('Gmail connection test failed:', error);
            return false;
        }
    }

    public async testCalendarConnection(): Promise<boolean> {
        try {
            await this.calendar.calendarList.list();
            return true;
        } catch (error) {
            console.error('Calendar connection test failed:', error);
            return false;
        }
    }

    public async testDriveConnection(): Promise<boolean> {
        try {
            await this.drive.about.get({ fields: 'user' });
            return true;
        } catch (error) {
            console.error('Drive connection test failed:', error);
            return false;
        }
    }

    // Gmail Integration
    async sendEmail(email: Email): Promise<string> {
        try {
            const message = this.createEmailMessage(email);
            const response = await this.gmail.users.messages.send({
                userId: 'me',
                requestBody: {
                    raw: message
                }
            });

            return response.data.id || '';
        } catch (error) {
            console.error('Error sending email:', error);
            throw error;
        }
    }

    public async getUnreadEmails(): Promise<Email[]> {
        try {
            const response = await this.gmail.users.messages.list({
                userId: 'me',
                q: 'is:unread'
            });

            const emails: Email[] = [];
            const messages = response.data.messages || [];

            for (const message of messages) {
                if (!message.id) continue;

                const details = await this.gmail.users.messages.get({
                    userId: 'me',
                    id: message.id
                });

                if (!details.data || !details.data.payload) continue;

                const headers = details.data.payload.headers || [];
                const subject = headers.find(h => h.name === 'Subject')?.value || '';
                const from = headers.find(h => h.name === 'From')?.value || '';
                const to = headers.find(h => h.name === 'To')?.value?.split(',') || [];

                emails.push({
                    id: message.id,
                    subject,
                    from,
                    to,
                    body: this.extractEmailBody(details.data),
                    priority: this.determinePriority(details.data),
                    status: 'UNREAD',
                    createdAt: new Date(parseInt(details.data.internalDate || '0'))
                });
            }

            return emails;
        } catch (error) {
            console.error('Error fetching unread emails:', error);
            return [];
        }
    }

    // Calendar Integration
    public async scheduleMeeting(meeting: Meeting): Promise<void> {
        try {
            await this.calendar.events.insert({
                calendarId: 'primary',
                requestBody: {
                    summary: meeting.title,
                    description: meeting.description,
                    start: {
                        dateTime: meeting.startTime.toISOString(),
                        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    },
                    end: {
                        dateTime: meeting.endTime.toISOString(),
                        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    },
                    attendees: meeting.attendees.map(email => ({ email })),
                    reminders: {
                        useDefault: true
                    }
                }
            });
        } catch (error) {
            console.error('Error scheduling meeting:', error);
            throw error;
        }
    }

    public async getUpcomingMeetings(): Promise<Meeting[]> {
        try {
            const now = new Date();
            const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

            const response = await this.calendar.events.list({
                calendarId: 'primary',
                timeMin: now.toISOString(),
                timeMax: tomorrow.toISOString(),
                singleEvents: true,
                orderBy: 'startTime'
            });

            const events = response.data.items || [];
            return events.map((event: calendar_v3.Schema$Event) => {
                const attendeeEmails = event.attendees?.map(a => a.email)
                    .filter((email): email is string => typeof email === 'string' && email.length > 0) || [];

                const description = event.description === null ? undefined : event.description;

                return {
                    id: event.id || '',
                    title: event.summary || '',
                    description: description || '',
                    startTime: new Date(event.start?.dateTime || event.start?.date || Date.now()),
                    endTime: new Date(event.end?.dateTime || event.end?.date || Date.now()),
                    attendees: attendeeEmails,
                    agenda: this.parseAgenda(description),
                    decisions: [],
                    actionItems: []
                };
            });
        } catch (error) {
            console.error('Error fetching upcoming meetings:', error);
            return [];
        }
    }

    // Google Docs Integration
    async createDocument(title: string, content: string): Promise<string> {
        if (!this.authorized) {
            console.log('Google Workspace not authorized. Simulating document creation.');
            return `simulated-doc-${Date.now()}`;
        }

        try {
            // Create the document
            const createResponse = await this.docs.documents.create({
                requestBody: {
                    title
                }
            });

            const documentId = createResponse.data.documentId;

            if (!documentId) {
                throw new Error('Failed to create document: No document ID returned');
            }

            // Update the document content
            await this.docs.documents.batchUpdate({
                documentId,
                requestBody: {
                    requests: [
                        {
                            insertText: {
                                location: {
                                    index: 1
                                },
                                text: content
                            }
                        }
                    ]
                }
            });

            // Move the document to the research folder if we have a folder ID
            if (this.folderId) {
                await this.drive.files.update({
                    fileId: documentId,
                    addParents: this.folderId,
                    fields: 'id, parents'
                });
            }

            console.log(`Created document with ID: ${documentId}`);
            return documentId;
        } catch (error) {
            console.error('Error creating document:', error);
            throw new Error(`Failed to create document: ${(error as Error).message}`);
        }
    }

    async updateDocument(documentId: string, content: string): Promise<void> {
        try {
            await this.docs.documents.batchUpdate({
                documentId,
                requestBody: {
                    requests: [{
                        insertText: {
                            location: {
                                index: 1
                            },
                            text: content
                        }
                    }]
                }
            });
        } catch (error) {
            console.error('Error updating document:', error);
            throw error;
        }
    }

    // Helper methods
    private createEmailMessage(email: Email): string {
        // Implementation to create RFC 2822 formatted email
        const message = [
            'From: ' + email.from,
            'To: ' + email.to.join(', '),
            'Subject: ' + email.subject,
            '',
            email.body
        ].join('\n');

        return Buffer.from(message).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
    }

    private extractEmailBody(message: gmail_v1.Schema$Message): string {
        let body = '';
        if (message.payload?.parts) {
            for (const part of message.payload.parts) {
                if (part.mimeType === 'text/plain' && part.body?.data) {
                    body = Buffer.from(part.body.data, 'base64').toString();
                    break;
                }
            }
        } else if (message.payload?.body?.data) {
            body = Buffer.from(message.payload.body.data, 'base64').toString();
        }
        return body;
    }

    private determinePriority(message: gmail_v1.Schema$Message): Priority {
        const headers = message.payload?.headers || [];
        const importance = headers.find(h => h.name === 'Importance')?.value || '';
        const priority = headers.find(h => h.name === 'X-Priority')?.value || '';

        if (importance.toLowerCase() === 'high' || priority === '1') {
            return Priority.HIGH;
        } else if (importance.toLowerCase() === 'low' || priority === '5') {
            return Priority.LOW;
        }
        return Priority.MEDIUM;
    }

    private parseAgenda(description: string | undefined): string[] {
        if (!description) return [];

        const agendaMatch = description.match(/Agenda:([\s\S]*?)(?:\n\n|$)/i);
        if (!agendaMatch) return [];

        return agendaMatch[1]
            .split('\n')
            .map(item => item.trim())
            .filter(item => item.length > 0);
    }

    public async getTasks(): Promise<Task[]> {
        try {
            // Get tasks from Google Tasks API
            const response = await this.tasksClient.tasks.list({
                tasklist: '@default',
                showCompleted: true,
                maxResults: 100
            });

            interface GoogleTask {
                id?: string;
                title?: string;
                notes?: string;
                due?: string;
                status?: string;
                updated?: string;
            }

            return (response.data.items || []).map((item: GoogleTask) => ({
                id: item.id || '',
                title: item.title || 'Untitled Task',
                description: item.notes || '',
                priority: this.getPriorityFromDueDate(item.due),
                status: this.getTaskStatus(item.status || 'needsAction'),
                category: this.getTaskCategory(item.title || ''),
                dueDate: item.due ? new Date(item.due) : undefined,
                createdAt: new Date(item.updated || new Date().toISOString()),
                updatedAt: new Date(item.updated || new Date().toISOString())
            }));
        } catch (error) {
            console.error('Error fetching tasks:', error);
            return [];
        }
    }

    public async updateTaskStatus(taskId: string, newStatus: TaskStatus): Promise<Task> {
        try {
            const response = await this.tasksClient.tasks.patch({
                tasklist: '@default',
                task: taskId,
                requestBody: {
                    status: this.getGoogleTaskStatus(newStatus)
                }
            });

            const item = response.data;
            return {
                id: item.id!,
                title: item.title!,
                description: item.notes || '',
                priority: this.getPriorityFromDueDate(item.due),
                status: newStatus,
                category: this.getTaskCategory(item.title!),
                dueDate: item.due ? new Date(item.due) : undefined,
                createdAt: new Date(item.updated!),
                updatedAt: new Date(item.updated!)
            };
        } catch (error) {
            console.error('Error updating task status:', error);
            throw new Error('Failed to update task status');
        }
    }

    private getPriorityFromDueDate(due?: string): Priority {
        if (!due) return Priority.LOW;
        const dueDate = new Date(due);
        const now = new Date();
        const diffDays = Math.ceil((dueDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

        if (diffDays <= 1) return Priority.URGENT;
        if (diffDays <= 3) return Priority.HIGH;
        if (diffDays <= 7) return Priority.MEDIUM;
        return Priority.LOW;
    }

    private getTaskStatus(googleStatus: string): TaskStatus {
        switch (googleStatus.toLowerCase()) {
            case 'completed':
                return TaskStatus.DONE;
            case 'needsAction':
                return TaskStatus.TODO;
            default:
                return TaskStatus.IN_PROGRESS;
        }
    }

    private getGoogleTaskStatus(status: TaskStatus): string {
        switch (status) {
            case TaskStatus.DONE:
                return 'completed';
            case TaskStatus.TODO:
                return 'needsAction';
            case TaskStatus.IN_PROGRESS:
                return 'needsAction'; // Google Tasks doesn't have an in-progress status
            default:
                return 'needsAction';
        }
    }

    private getTaskCategory(title: string): TaskCategory {
        // Simple categorization based on keywords in the title
        const lowerTitle = title.toLowerCase();
        if (lowerTitle.includes('meeting') || lowerTitle.includes('call') || lowerTitle.includes('conference')) {
            return TaskCategory.MEETING;
        } else if (lowerTitle.includes('email') || lowerTitle.includes('message') || lowerTitle.includes('reply')) {
            return TaskCategory.EMAIL;
        } else if (lowerTitle.includes('personal') || lowerTitle.includes('home') || lowerTitle.includes('family')) {
            return TaskCategory.PERSONAL;
        }
        return TaskCategory.WORK;
    }

    /**
     * Lists documents from Google Drive
     * @returns Array of documents with their content
     */
    public async listDocuments(): Promise<Array<{ id: string, name: string, content: string }>> {
        if (!this.authorized || !this.folderId) {
            console.log('Google Workspace not authorized or no folder ID. Returning empty document list.');
            return [];
        }

        try {
            const response = await this.drive.files.list({
                q: `'${this.folderId}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false`,
                fields: 'files(id, name)',
                orderBy: 'createdTime desc'
            });

            const files = response.data.files || [];

            // Get content for each document
            const documents = await Promise.all(
                files.map(async (file) => {
                    try {
                        if (!file.id) return null;

                        const doc = await this.docs.documents.get({
                            documentId: file.id
                        });

                        // Extract text content from document
                        let content = '';
                        if (doc.data.body && doc.data.body.content) {
                            content = doc.data.body.content
                                .filter(item => item.paragraph)
                                .map(item => {
                                    if (!item.paragraph || !item.paragraph.elements) return '';
                                    return item.paragraph.elements
                                        .map(element => element.textRun?.content || '')
                                        .join('');
                                })
                                .join('\n');
                        }

                        return {
                            id: file.id,
                            name: file.name || 'Untitled Document',
                            content
                        };
                    } catch (error) {
                        console.error(`Error fetching document ${file.id}:`, error);
                        return null;
                    }
                })
            );

            return documents.filter(doc => doc !== null) as Array<{ id: string, name: string, content: string }>;
        } catch (error) {
            console.error('Error listing documents:', error);
            return [];
        }
    }

    /**
     * Find or create the research folder in Google Drive
     */
    private async findOrCreateFolder(): Promise<void> {
        if (!this.authorized) return;

        try {
            // Search for the folder
            const response = await this.drive.files.list({
                q: `name='${config.googleWorkspace.folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
                fields: 'files(id, name)'
            });

            if (response.data.files && response.data.files.length > 0) {
                this.folderId = response.data.files[0].id || null;
                console.log(`Found research folder with ID: ${this.folderId}`);
            } else {
                // Create the folder if it doesn't exist
                const folderResponse = await this.drive.files.create({
                    requestBody: {
                        name: config.googleWorkspace.folderName,
                        mimeType: 'application/vnd.google-apps.folder'
                    },
                    fields: 'id'
                });

                this.folderId = folderResponse.data.id || null;
                console.log(`Created research folder with ID: ${this.folderId}`);
            }
        } catch (error) {
            console.error('Error finding or creating research folder:', error);
            this.folderId = null;
        }
    }
} 