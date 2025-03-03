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

## How to Use

### 1. Basic Setup

First, initialize the system with your configuration:

```python
from src.main import ATENAAI
from src.logging.logger import Logger

# Initialize logger
logger = Logger()

# Create ATENAAI instance
atenai = ATENAAI(logger)

# Start the system
await atenai.start()
```

### 2. Task Management

#### Creating Tasks
```python
from src.executor.task_executor import TaskExecutor

# Create a task
task = await task_executor.create_task(
    title="Process Data",
    description="Process and analyze the dataset",
    priority="HIGH",
    deadline="2024-03-20"
)

# Add subtasks
subtask = await task_executor.add_subtask(
    parent_task_id=task.id,
    title="Data Cleaning",
    description="Clean and preprocess the data"
)
```

#### Managing Tasks
```python
# Update task status
await task_executor.update_status(task.id, "IN_PROGRESS")

# Add task notes
await task_executor.add_note(task.id, "Data validation completed")

# Set task priority
await task_executor.set_priority(task.id, "HIGH")
```

### 3. Natural Language Interaction

#### Text Input
```python
from src.input_processor import InputProcessor

# Process text input
response = await input_processor.process_text(
    "Schedule a meeting with John tomorrow at 2 PM"
)
```

#### Voice Input
```python
# Process voice input
response = await input_processor.process_voice(
    audio_file="meeting_request.wav"
)
```

### 4. Knowledge Base Operations

```python
from src.knowledge.knowledge_base import KnowledgeBase

# Store information
await knowledge_base.store(
    key="user_preferences",
    value={"theme": "dark", "language": "en"}
)

# Retrieve information
preferences = await knowledge_base.retrieve("user_preferences")

# Update information
await knowledge_base.update(
    key="user_preferences",
    value={"theme": "light"}
)
```

### 5. External Service Integration

```python
from src.services.external_services import ExternalServices

# Register external service
external_services.register_service(
    name="email_service",
    service_type="EMAIL",
    config={
        "smtp_server": "smtp.example.com",
        "port": 587
    }
)

# Use external service
await external_services.send_email(
    to="user@example.com",
    subject="Task Update",
    body="Your task has been completed"
)
```

### 6. Error Handling

```python
from src.utils.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

# Handle errors with retry mechanism
try:
    result = await some_operation()
except Exception as e:
    await error_handler.handle_error(
        error=e,
        component="my_component",
        operation="some_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM,
        retry=True
    )
```

### 7. Monitoring and Logging

```python
# Get system metrics
metrics = await meta_agent.get_metrics()

# Check system health
health_status = await meta_agent.check_health()

# Get performance statistics
performance_stats = await meta_agent.get_performance_stats()
```

### 8. Configuration

The system can be configured through environment variables:

```env
# Core Settings
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=development

# API Keys
OPENAI_API_KEY=your_openai_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token

# Service Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Error Handling
MAX_RETRY_ATTEMPTS=3
CIRCUIT_BREAKER_THRESHOLD=5
```

### 9. Best Practices

1. **Error Handling**
   - Always use appropriate error severity levels
   - Implement retry mechanisms for transient failures
   - Use circuit breakers for external services

2. **Task Management**
   - Break down complex tasks into subtasks
   - Set realistic deadlines
   - Use appropriate priority levels

3. **Resource Management**
   - Clean up resources after use
   - Monitor system performance
   - Implement proper logging

4. **Security**
   - Never commit sensitive information
   - Use environment variables for secrets
   - Implement proper authentication

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

# ATENAAI Error Handling System

A comprehensive error handling system with retry mechanisms, circuit breakers, and recovery strategies.

## Features

- **Error Management**
  - Custom exception classes
  - Error categorization
  - Error tracking
  - Error reporting

- **Recovery Mechanisms**
  - Retry strategies with exponential backoff
  - Circuit breakers for external services
  - Fallback mechanisms
  - State recovery

- **Monitoring**
  - Error metrics collection
  - Error pattern analysis
  - Circuit breaker status
  - Recovery statistics

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HGHollowOS/ATENA-AI.git
   cd ATENA-AI
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Error Handling

```python
from src.utils.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory
from src.logging.logger import Logger

# Create instances
logger = Logger()
error_handler = ErrorHandler(logger)

# Handle errors
try:
    result = some_operation()
except Exception as e:
    await error_handler.handle_error(
        error=e,
        component="my_component",
        operation="some_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM
    )
```

### Circuit Breaker Pattern

```python
# Register circuit breaker
error_handler.register_circuit_breaker(
    component="external_service",
    failure_threshold=5,
    reset_timeout=60
)

# Use circuit breaker
try:
    result = await external_service_call()
except Exception as e:
    await error_handler.handle_error(
        error=e,
        component="external_service",
        operation="external_service_call",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.EXTERNAL
    )
```

### Retry Strategy

```python
# Register retry strategy
error_handler.register_retry_strategy(
    component="database",
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0
)

# Use retry mechanism
try:
    result = await database_query()
except Exception as e:
    await error_handler.handle_error(
        error=e,
        component="database",
        operation="database_query",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.DATABASE,
        retry=True
    )
```

### Error Handler Decorator

```python
from src.utils.error_handler import handle_errors

@handle_errors(
    component="api",
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.SYSTEM,
    retry=True
)
async def api_call(error_handler=None):
    response = await make_api_request()
    return response
```

### Error Monitoring

```python
# Get error metrics
metrics = await error_handler.get_error_metrics()

# Check circuit breaker status
circuit_status = metrics["circuit_breakers"]["external_service"]["state"]

# Check recovery statistics
recovery_stats = metrics["recovery_stats"]
```

## Error Categories and Severities

### Error Severities
- `LOW`: Minor issues that don't affect core functionality
- `MEDIUM`: Moderate issues that may affect some features
- `HIGH`: Serious issues that affect core functionality
- `CRITICAL`: Critical issues that require immediate attention

### Error Categories
- `SYSTEM`: System-level errors
- `NETWORK`: Network-related errors
- `DATABASE`: Database errors
- `VALIDATION`: Validation errors
- `SECURITY`: Security-related errors
- `BUSINESS`: Business logic errors
- `EXTERNAL`: External service errors

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Configuration

The error handling system can be configured through environment variables:

```env
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Error Handling
MAX_RETRY_ATTEMPTS=3
BASE_RETRY_DELAY=1.0
MAX_RETRY_DELAY=10.0

# Circuit Breaker
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 