# openclaw - Your Own Personal AI Assistant 🦞

Your own personal AI assistant. Any OS. Any Platform. The lobster way.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Visit http://localhost:5000 to see your AI assistant in action!

## Features

- **Multi-Session Support**: Create and manage multiple chat sessions
- **Claude API Integration**: Powered by Anthropic's Claude for intelligent responses
- **Streaming Responses**: Real-time streaming of AI responses
- **Session Management**: View, switch, and delete chat sessions
- **Markdown Rendering**: Support for code blocks and formatted responses
- **Configurable Settings**: Easy configuration via config.yaml

## Routes

- `/` - Home page
- `/chat` - Chat interface
- `/api/chat` - Chat API endpoint
- `/api/sessions` - Manage chat sessions (GET list, POST create)
- `/api/sessions/<id>` - Get or delete a specific session
- `/api/settings` - Get and update settings

## Configuration

Create a `config.yaml` file in the project root:

```yaml
anthropic:
  api_key: your-api-key-here
  model: claude-3-5-sonnet-20241022
  max_tokens: 4096
  temperature: 1.0

app:
  host: 0.0.0.0
  port: 5000
  debug: true
```

Or set environment variable `ANTHROPIC_API_KEY`.

## Requirements

See `requirements.txt` for dependencies.

作者: stlin256的openclaw
