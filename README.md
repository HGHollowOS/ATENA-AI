# ATENA-AI

ATENA-AI is an advanced AI-powered Discord bot designed to support company tasks through natural conversation and autonomous business intelligence capabilities. It combines proactive monitoring, natural language processing, and self-improvement systems to provide valuable insights and automate business workflows.

## Features

### Core Capabilities
- **Proactive Business Intelligence**: Monitors market trends, company performance, and industry developments in real-time
- **Natural Discord Interaction**: Responds to both slash commands and natural language queries
- **Self-Improvement System**: Continuously learns and adapts based on interactions and performance metrics
- **Business Workflow Automation**: Streamlines common business tasks and research processes

### Command Reference

#### Slash Commands
- `/research [topic] [depth]`
  - Conducts in-depth research on companies or industries
  - **Parameters**:
    - `topic`: Company name or industry (min. 3 characters)
    - `depth`: Research depth ("quick", "normal", "deep")
  - **Example**: `/research topic:"Tesla" depth:"deep"`

- `/monitor [target] [metric] [threshold]`
  - Sets up monitoring for business metrics
  - **Parameters**:
    - `target`: Metric to monitor (e.g., "Market Share", "Revenue")
    - `metric`: Type of measurement ("percentage", "value", "growth_rate")
    - `threshold`: Alert threshold value
  - **Example**: `/monitor target:"Revenue" metric:"growth_rate" threshold:10.0`

- `/analyze [metric] [timeframe]`
  - Analyzes business performance metrics
  - **Parameters**:
    - `metric`: Metric to analyze
    - `timeframe`: Analysis period ("1d", "1w", "1m", "3m", "1y")
  - **Example**: `/analyze metric:"Profit Margin" timeframe:"1m"`

- `/report [report_type] [timeframe]`
  - Generates business intelligence reports
  - **Parameters**:
    - `report_type`: Type of report ("performance", "market", "competitor", "trend")
    - `timeframe`: Report period ("1w", "1m", "3m", "1y")
  - **Example**: `/report report_type:"market" timeframe:"1m"`

#### Text Commands
- `!atena help`
  - Displays comprehensive help information
  - Lists all available commands and their usage

- Natural Language Queries
  - Example: "How is Tesla performing this quarter?"
  - Example: "Monitor SpaceX's market share"
  - Example: "Generate a competitor analysis report"

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
# Create .env file
DISCORD_TOKEN=your_discord_token
OPENAI_API_KEY=your_openai_api_key
```

4. Run the bot:
```bash
python src/main.py
```

## Project Structure
```
ATENA-AI/
├── src/
│   ├── business_intelligence/
│   │   ├── business_intelligence.py
│   │   └── market_analysis.py
│   ├── discord_bot/
│   │   ├── cogs/
│   │   │   ├── commands.py
│   │   │   └── business_intelligence.py
│   │   └── bot.py
│   ├── meta_agent/
│   │   ├── meta_agent.py
│   │   └── self_improvement.py
│   └── main.py
├── tests/
│   ├── business_intelligence/
│   ├── discord_bot/
│   └── meta_agent/
├── requirements.txt
└── README.md
```

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run specific test categories:
```bash
python -m pytest tests/business_intelligence/ -v
python -m pytest tests/discord_bot/ -v
python -m pytest tests/meta_agent/ -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- Discord.py team for the Discord API wrapper
- All contributors who have helped shape ATENA-AI

## Support

For support, please:
1. Check the [documentation](docs/)
2. Open an issue
3. Join our [Discord server](https://discord.gg/your-server) 