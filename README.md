# ATENA AI

ATENA AI is an intelligent Discord bot that provides comprehensive research capabilities, task management, and conversation analysis. It integrates with various services including Google Workspace, LinkedIn, and OpenAI to deliver powerful features.

## Features

- 🔍 **Advanced Research Capabilities**
  - Multi-perspective analysis
  - Conversation context analysis
  - Sentiment analysis
  - Agreement/disagreement identification
  - Comprehensive research document generation

- 📅 **Task & Calendar Management**
  - Task creation and tracking
  - Meeting scheduling
  - Calendar integration
  - Reminder system

- 🤖 **Intelligent Conversation Analysis**
  - Context-aware responses
  - Participant role analysis
  - Topic extraction
  - Pattern recognition

- 📊 **Document Management**
  - Google Docs integration
  - Research document generation
  - Document organization

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Discord Bot Token
- OpenAI API Key
- Google Workspace API credentials
- LinkedIn API credentials (optional)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/atena-ai.git
   cd atena-ai
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=your_google_redirect_uri
   LINKEDIN_CLIENT_ID=your_linkedin_client_id
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
   LINKEDIN_REDIRECT_URI=your_linkedin_redirect_uri
   ```

4. Set up Google Workspace API:
   - Go to the Google Cloud Console
   - Create a new project
   - Enable the necessary APIs (Gmail, Calendar, Drive, Docs)
   - Create credentials and download the `credentials.json` file
   - Place the file in the project root

5. Start the bot:
   ```bash
   npm run dev
   ```

## Usage

### Discord Commands

- `!atena research <topic>` - Start a comprehensive research task
- `!atena status [research]` - Check status of research tasks or system
- `!atena task <action> <details>` - Manage tasks
- `!atena meeting <action> <details>` - Manage meetings
- `!atena help [command]` - Get help on commands
- `!atena quiet` - Toggle quiet mode
- `!atena test` - Test system functionality

### Research Features

The bot can analyze conversations and provide:
- Multi-perspective analysis (business, technical, legal, market)
- Sentiment analysis
- Key points extraction
- Agreement/disagreement identification
- Comprehensive research documents

## Development

### Project Structure

```
src/
├── agents/         # AI agents and research logic
├── core/          # Core functionality
├── integrations/  # External service integrations
├── services/      # Internal services
├── types/         # TypeScript type definitions
└── config/        # Configuration files
```

### Building

```bash
npm run build
```

### Testing

```bash
npm test
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT-4 API
- Discord.js for Discord bot framework
- Google Workspace API
- All contributors and users of ATENA AI 