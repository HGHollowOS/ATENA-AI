# ATENA-AI

ATENA-AI is an advanced business intelligence and research assistant that leverages AI to help companies make data-driven decisions. Through natural conversation and autonomous research capabilities, ATENA-AI provides valuable insights and automates business workflows.

## Features

- 🤖 **Intelligent Business Research**: Conducts in-depth research on companies, industries, and market trends
- 📊 **Performance Monitoring**: Tracks and analyzes business metrics in real-time
- 📈 **Market Analysis**: Provides comprehensive market insights and competitor analysis
- 🔄 **Self-Improvement**: Continuously learns and adapts to improve performance
- 🤝 **Natural Interaction**: Communicates through Discord with natural language understanding
- 📱 **Multi-Platform**: Accessible through Discord and other integration points

## Discord Commands

### Research Command
Research companies or industries with varying levels of depth.
```
/research [topic] [depth]
```
- `topic`: Company or industry to research
- `depth`: Research depth (quick/medium/deep)

Examples:
```
/research topic:"Tesla" depth:"deep"
/research topic:"AI Industry" depth:"quick"
```

### Monitor Command
Set up monitoring for business metrics with customizable alerts.
```
/monitor [target] [metric] [threshold]
```
- `target`: Metric target to monitor
- `metric`: Type of metric
- `threshold`: Alert threshold value

Examples:
```
/monitor target:"Market Share" metric:"percentage" threshold:75.0
/monitor target:"Revenue" metric:"growth_rate" threshold:10.0
```

### Analyze Command
Analyze business performance metrics over time.
```
/analyze [metric] [timeframe]
```
- `metric`: Metric to analyze
- `timeframe`: Analysis period (1d/1w/1m)

Examples:
```
/analyze metric:"Profit Margin" timeframe:"1w"
/analyze metric:"Customer Acquisition" timeframe:"1m"
```

### Report Command
Generate comprehensive business intelligence reports.
```
/report [type] [timeframe]
```
- `type`: Report type (performance/market/competitor)
- `timeframe`: Report period (1d/1w/1m)

Examples:
```
/report type:"performance" timeframe:"1w"
/report type:"market" timeframe:"1m"
```

### Help Command
Display help information about available commands.
```
!atena help
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

4. Run the bot:
```bash
python src/main.py
```

## Project Structure

```
ATENA-AI/
├── src/
│   ├── business_intelligence/    # Business logic and analysis
│   ├── discord_bot/             # Discord bot implementation
│   ├── meta_agent/              # Self-improvement system
│   └── main.py                  # Application entry point
├── tests/                       # Test suites
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Run specific test modules:
```bash
python -m pytest tests/meta_agent/
python -m pytest tests/discord_bot/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for AI capabilities
- Discord.py team for the Discord integration
- All contributors who have helped shape ATENA-AI 