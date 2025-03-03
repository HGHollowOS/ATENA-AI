# ATENA-AI - Proactive Business Assistant on Discord

ATENA-AI is an intelligent business assistant that operates proactively on Discord, supporting company tasks through natural conversation and autonomous research capabilities. The system combines advanced natural language processing with business intelligence to provide valuable insights and automate routine tasks.

## Core Features

### 1. Proactive Business Intelligence
- Autonomous research of business opportunities
- Partnership lead identification and analysis
- Market trend monitoring and reporting
- Automated email draft generation
- Proactive notifications for important findings

### 2. Natural Discord Interaction
- Conversational interface with @mentions
- Smart filtering of team chatter
- Command-based operations
- Context-aware responses
- Multi-turn dialogue support

### 3. Self-Improvement Capabilities
- Performance monitoring and optimization
- Chain-of-thought evaluation
- Autonomous parameter adjustments
- Learning from interaction outcomes
- Proactive system updates

### 4. Business Workflow Automation
- Partnership research and analysis
- Email draft generation
- Report creation
- Task scheduling and tracking
- Meeting preparation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/HGHollowOS/ATENA-AI.git
cd ATENA-AI
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Discord bot token and other configurations
```

## How to Use

### 1. Discord Integration

#### Basic Commands
```python
# Start the Discord bot
python src/discord_bot.py

# The bot will now listen for:
# - Direct mentions (@ATENA-AI)
# - Command prefixes (!)
# - Proactive notifications
```

#### Natural Conversation
```
User: @ATENA-AI, did you find any interesting partnerships?
ATENA-AI: I've been researching potential partnerships in the tech sector. I found three promising leads:
1. TechCorp - AI solutions provider
2. DataFlow - Data analytics platform
3. CloudScale - Cloud infrastructure

Would you like me to investigate any of these further?
```

#### Proactive Notifications
```
ATENA-AI: I've identified a potential partnership opportunity with InnovateTech. 
They're expanding into our market and have complementary products. 
Would you like me to draft an outreach email?
```

### 2. Business Intelligence

#### Partnership Research
```python
from src.business.business_module import BusinessModule

# Initialize business module
business = BusinessModule()

# Research partnerships
partnerships = await business.research_partnerships(
    industry="AI",
    region="North America",
    criteria={
        "min_revenue": "10M",
        "tech_stack": ["Python", "AI/ML"]
    }
)
```

#### Email Generation
```python
# Generate outreach email
email = await business.generate_email(
    company="TechCorp",
    purpose="partnership",
    tone="professional",
    key_points=["AI expertise", "market expansion"]
)
```

### 3. Self-Improvement

```python
from src.meta_agent import MetaAgent
from src.self_improvement import SelfImprovement

# Initialize components
meta_agent = MetaAgent()
self_improvement = SelfImprovement()

# Monitor performance
metrics = await meta_agent.get_metrics()

# Trigger self-improvement if needed
if await self_improvement.evaluate_performance(metrics):
    await self_improvement.trigger_auto_update()
```

### 4. Configuration

Configure the system through environment variables:

```env
# Discord Configuration
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_GUILD_IDS=your_guild_ids

# Business Intelligence
PARTNERSHIP_CRITERIA={"industry": "AI", "min_revenue": "10M"}
RESEARCH_INTERVAL=3600  # seconds
NOTIFICATION_THRESHOLD=0.8

# Email Configuration
EMAIL_TEMPLATE_DIR=templates/email
SMTP_SERVER=smtp.example.com
SMTP_PORT=587

# Self-Improvement
LEARNING_RATE=0.1
UPDATE_THRESHOLD=0.7
```

## Project Structure

```
ATENA-AI/
├── src/
│   ├── discord_bot/      # Discord integration
│   ├── meta_agent/       # System monitoring
│   ├── self_improvement/ # Self-improvement logic
│   ├── business/         # Business intelligence
│   ├── dialogue/         # Conversation management
│   ├── knowledge/        # Knowledge base
│   └── logging/          # Logging system
├── tests/                # Test files
├── templates/            # Email templates
├── docs/                # Documentation
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
The project follows PEP 8 guidelines. To check code style:
```bash
flake8 src/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors
- Built with modern Python technologies
- Inspired by the need for intelligent business assistance 