# ATENA-AI - Proactive Business Assistant on Discord

ATENA-AI is an intelligent business assistant that operates proactively on Discord, supporting your company's tasks through natural conversation and autonomous research capabilities. It combines advanced AI with business intelligence to provide real-time insights and automate routine tasks.

## Features

### Core Capabilities
- 🤖 Proactive Business Intelligence
- 💬 Natural Discord Interaction
- 🔄 Self-Improvement System
- 🔗 Business Workflow Automation

### Business Commands
ATENA-AI provides several powerful commands for business operations:

#### Research Command
Research companies or industries with varying levels of depth:
```bash
/research topic:"Tesla" depth:"deep"
/research topic:"AI Industry" depth:"quick"
```

#### Monitor Command
Set up monitoring alerts for business metrics:
```bash
/monitor target:"Market Share" metric:"percentage" threshold:75.0
/monitor target:"Revenue" metric:"growth_rate" threshold:10.0
```

#### Analyze Command
Analyze business performance metrics over different timeframes:
```bash
/analyze metric:"Profit Margin" timeframe:"1w"
/analyze metric:"Customer Acquisition" timeframe:"1m"
```

#### Report Command
Generate comprehensive business reports:
```bash
/report report_type:"Performance" timeframe:"1w"
/report report_type:"Market Analysis" timeframe:"1m"
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ATENA-AI.git
cd ATENA-AI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
BUSINESS_API_KEY=your_business_data_api_key
MONGODB_URI=your_mongodb_connection_string
```

4. Run the bot:
```bash
python src/main.py
```

## Project Structure

```
ATENA-AI/
├── src/
│   ├── discord_bot/
│   │   ├── cogs/
│   │   │   ├── commands.py      # Business commands
│   │   │   ├── conversation.py  # Natural language processing
│   │   │   └── notifications.py # Alert system
│   │   └── discord_bot.py       # Main bot implementation
│   ├── business_intelligence/
│   │   └── business_intelligence.py  # Business logic
│   ├── meta_agent/
│   │   ├── meta_agent.py        # Performance monitoring
│   │   └── self_improvement.py  # System optimization
│   └── utils/
│       ├── logger.py            # Logging system
│       └── error_handler.py     # Error management
├── tests/
│   ├── discord_bot/
│   │   └── test_commands.py     # Command tests
│   └── meta_agent/
│       ├── test_meta_agent.py   # Meta-agent tests
│       └── test_integration.py  # Integration tests
├── requirements.txt
├── requirements-test.txt
└── README.md
```

## Testing

Run the test suite:
```bash
pip install -r requirements-test.txt
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- Discord.py team
- Contributors and maintainers

## Support

For support, please:
1. Check the [documentation](docs/)
2. Open an issue
3. Join our [Discord server](https://discord.gg/your-server) 