# Configuration Management Guide

This document explains how to properly manage configurations for different environments in the Japanese Law AI Agent project.

## Overview

Our configuration system separates public configuration parameters from sensitive information using environment variables. This ensures that sensitive data like passwords and API keys are never committed to the repository.

The configuration system uses:
1. A [config.toml](./app/core/config/config.toml) file that defines how settings are structured and provides default values with environment variable placeholders
2. A [config.toml.example](../config.toml.example) file that serves as a template showing the structure of the config file
3. A local [.env](.env) file (not committed) with actual values that replaces the environment variable placeholders

## Configuration Files

### `config.toml`
Located at [app/core/config/config.toml](./app/core/config/config.toml), this file defines the configuration structure and uses placeholders for environment variables with default values. It is committed to the repository and includes example values in comments. 

### `config.toml.example`
Located at the root of the project, this file is a copy of the config.toml structure and serves as an additional reference for the configuration format.

### `.env` (Local only)
This is your local configuration file containing actual values. **This file is excluded from Git commits by `.gitignore`.**

## Setting Up Your Local Environment

1. Create an environment file from the template provided in the config.toml comments:
   ```bash
   # Copy the example section from config.toml and place in a .env file
   # Or create the file directly:
   touch .env
   ```

2. Add the required environment variables to your `.env` file:
   ```bash
   POSTGRES_PASSWORD=your_actual_password
   OPENAI_API_KEY=your_actual_api_key
   MILVUS_PASSWORD=your_milvus_password
   ```

## Production Deployment

For production deployments, set environment variables through your deployment platform (Docker, Kubernetes, cloud provider, etc.) without creating a physical `.env` file.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_SERVER` | PostgreSQL server address | No (default: localhost) |
| `POSTGRES_USER` | PostgreSQL username | No (default: postgres) |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes |
| `POSTGRES_DB` | PostgreSQL database name | No (default: japaneselaw) |
| `MILVUS_HOST` | Milvus server address | No (default: milvus) |
| `MILVUS_PORT` | Milvus server port | No (default: 19530) |
| `MILVUS_USER` | Milvus username | No |
| `MILVUS_PASSWORD` | Milvus password | No |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `MODEL_NAME` | LLM model name | No (default: gpt-3.5-turbo) |
| `DEBUG` | Debug mode | No (default: false) |

## Docker Deployment

When deploying with Docker, you can pass environment variables using a file:

```bash
docker run -d --env-file ./production.env your-app-image
```

## Security Best Practices

- Never commit `.env` files to the repository
- Use strong, unique passwords for all services
- Rotate API keys and passwords regularly
- Use different credentials for development and production
- Limit access to production configuration files