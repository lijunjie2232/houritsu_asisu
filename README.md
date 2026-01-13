# Japanese Law AI Agent

A sophisticated AI-powered application for querying and understanding Japanese law, built with Python, FastAPI, LangChain, and vector databases.

## Architecture

The system uses a split data architecture:
- Application data (user accounts, conversation history) is stored in PostgreSQL
- Legal documents and RAG data is stored in Milvus vector database
- FastAPI provides the REST API layer
- LangChain powers the AI agent functionality

## Configuration Management

This project follows best practices for configuration management to ensure sensitive data is never exposed:

1. Configuration structure is defined in [app/core/config/config.toml](./app/core/config/config.toml) with environment variable placeholders
2. A [config.toml.example](config.toml.example) file provides an additional reference for the configuration format
3. Actual environment files (.env) are excluded from Git via [.gitignore](.gitignore)
4. Sensitive values are injected at runtime via environment variables

### Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd houritu_asisu
   ```

2. Create an environment file with your actual values:
   ```bash
   # Create .env file with required values based on examples in config.toml
   touch .env
   # Add the required environment variables to your .env file
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the database services:
   ```bash
   cd docker
   docker-compose up -d
   ```

5. Run the application:
   ```bash
   python main.py
   ```

## Security Considerations

- Never commit `.env` files to version control
- Use different credentials for development and production
- Regularly rotate API keys and database passwords
- Review the [.gitignore](.gitignore) file to ensure sensitive files are excluded

## Project Structure

- `app/agents/` - AI agent implementations
- `app/api/` - FastAPI route definitions
- `app/core/config/` - Configuration and settings (including [config.toml](./app/core/config/config.toml))
- `app/core/db/` - Database models and connection logic
- `app/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic schemas for API validation
- `app/services/` - Business logic
- `app/tools/` - LangChain tools (RAG, web search)
- `docker/` - Docker configuration for PostgreSQL and Milvus
- `requirements.txt` - Python dependencies
- `config.toml.example` - Example configuration file
- `.gitignore` - Files excluded from Git

## Configuration Guide

See [CONFIGURATION.md](CONFIGURATION.md) for detailed information about managing configurations across different environments.