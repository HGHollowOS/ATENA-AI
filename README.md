# ATENAAI - Advanced Task Execution and Natural Language Assistant AI

ATENAAI is a sophisticated AI assistant system that combines natural language processing, task execution, and self-improvement capabilities. The system is designed to be modular, extensible, and efficient.

## Features

### Core Components
- **Meta-Agent**: System performance monitoring and self-improvement
- **Input Processor**: Text and voice input handling
- **Natural Language Understanding**: Intent analysis and entity extraction
- **Dialogue Manager**: Conversation context and state management
- **Knowledge Base**: Data storage and retrieval
- **Task Executor**: Task scheduling and execution
- **External Services**: API integration and service management

### Key Features
- Self-improvement through meta-agent
- Comprehensive logging and monitoring
- Modular architecture for easy extension
- Support for text and voice input
- Integration with external services
- Task scheduling and prioritization

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ATENAAI.git
cd ATENAAI
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
# Edit .env with your configuration
```

## Usage

1. Start the application:
```bash
python src/main.py
```

2. The system will initialize all components and start listening for input.

## Project Structure

```
ATENAAI/
├── src/
│   ├── meta_agent/      # System monitoring and self-improvement
│   ├── input_processor/ # Input handling
│   ├── nlu/            # Natural language understanding
│   ├── dialogue/       # Dialogue management
│   ├── knowledge/      # Knowledge base
│   ├── executor/       # Task execution
│   ├── services/       # External services
│   └── logging/        # Logging system
├── tests/              # Test files
├── docs/              # Documentation
├── requirements.txt   # Dependencies
└── README.md         # This file
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
- Inspired by the need for intelligent task management 