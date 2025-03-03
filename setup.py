"""
Setup script for ATENA AI

This script helps users install and configure the ATENA AI project,
including dependency installation and environment setup.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import shutil

def check_python_version():
    """Check if Python version meets requirements."""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        print(f"Error: Python {required_version[0]}.{required_version[1]} or higher is required")
        print(f"Current version: {current_version[0]}.{current_version[1]}")
        sys.exit(1)

def create_directories():
    """Create necessary project directories."""
    directories = [
        "data",
        "logs",
        "models",
        "tests",
        "src/meta_agent",
        "src/input_processor",
        "src/nlu",
        "src/dialogue",
        "src/services",
        "src/executor",
        "src/knowledge",
        "src/logging",
        "src/utils"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def install_dependencies():
    """Install project dependencies."""
    print("Installing dependencies...")
    
    # Install Python dependencies
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Install spaCy model
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    
    print("Dependencies installed successfully")

def create_env_file():
    """Create .env file from template."""
    env_template = """
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_token_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Workspace Configuration (Optional)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=your_google_redirect_uri_here

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=logs

# System Configuration
MAX_CONTEXT_TURNS=10
IMPROVEMENT_THRESHOLD=0.7
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(env_template)
        print("Created .env file from template")
    else:
        print(".env file already exists")

def setup_database():
    """Initialize the knowledge base database."""
    from src.knowledge.knowledge_base import KnowledgeBase
    
    try:
        kb = KnowledgeBase()
        print("Knowledge base initialized successfully")
    except Exception as e:
        print(f"Error initializing knowledge base: {str(e)}")
        sys.exit(1)

def create_test_files():
    """Create basic test files."""
    test_template = """
import pytest
from src.meta_agent.meta_agent import MetaAgent

def test_meta_agent_initialization():
    agent = MetaAgent()
    assert agent is not None
"""
    
    test_path = Path("tests/test_meta_agent.py")
    if not test_path.exists():
        test_path.write_text(test_template)
        print("Created test file: test_meta_agent.py")

def main():
    """Main setup function."""
    print("Setting up ATENA AI...")
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    install_dependencies()
    
    # Create environment file
    create_env_file()
    
    # Setup database
    setup_database()
    
    # Create test files
    create_test_files()
    
    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Edit the .env file with your credentials")
    print("2. Run tests: python -m pytest")
    print("3. Start the application: python src/main.py")

if __name__ == "__main__":
    main() 