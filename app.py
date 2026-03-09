import os
import json
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config():
    """Load configuration from config.yaml or environment variables"""
    config = {
        "anthropic": {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "temperature": 1.0
        },
        "app": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": True
        }
    }

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                if "anthropic" in file_config:
                    config["anthropic"].update(file_config["anthropic"])
                if "app" in file_config:
                    config["app"].update(file_config["app"])

    return config

config = load_config()

# In-memory storage
sessions = {}  # {session_id: {"messages": [], "created_at": "", "updated_at": ""}}
current_session_id = None

# Claude client (lazy initialization)
_claude_client = None

def get_claude_client():
    """Get or create Claude API client"""
    global _claude_client
    if _claude_client is None:
        api_key = config["anthropic"].get("api_key")
        if not api_key:
            return None
        try:
            from anthropic import Anthropic
            _claude_client = Anthropic(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Claude client: {e}")
            return None
    return _claude_client


def get_or_create_session():
    """Get current session or create a new one"""
    global current_session_id
    if current_session_id is None or current_session_id not in sessions:
        current_session_id = str(uuid.uuid4())[:8]
        sessions[current_session_id] = {
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    return current_session_id


@app.route('/')
def home():
    """Home page - displays welcome message"""
    return render_template('index.html')


@app.route('/chat')
def chat():
    """Chat interface page"""
    return render_template('chat.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat messages with Claude integration"""
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    session_id = data.get('session_id') or get_or_create_session()
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    user_message = data['message']
    use_stream = data.get('stream', False)

    # Add user message to history
    sessions[session_id]["messages"].append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.now().isoformat()
    })
    sessions[session_id]["updated_at"] = datetime.now().isoformat()

    # Get Claude response
    client = get_claude_client()
    if not client:
        # Fallback response if no API key
        response = "⚠️ Please configure your Anthropic API key in config.yaml or set ANTHROPIC_API_KEY environment variable."
        sessions[session_id]["messages"].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        return jsonify({
            'response': response,
            'history': sessions[session_id]["messages"],
            'session_id': session_id,
            'streaming': False
        })

    try:
        # Convert session messages to Claude format
        claude_messages = []
        for msg in sessions[session_id]["messages"]:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        if use_stream:
            # Streaming response
            def generate():
                full_response = ""
                try:
                    stream = client.messages.stream(
                        model=config["anthropic"]["model"],
                        max_tokens=config["anthropic"]["max_tokens"],
                        temperature=config["anthropic"]["temperature"],
                        messages=claude_messages
                    )
                    for chunk in stream:
                        if chunk.type == "content_block_delta":
                            if hasattr(chunk.delta, 'text'):
                                text = chunk.delta.text
                                full_response += text
                                yield f"data: {json.dumps({'text': text, 'done': False})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                    return

                # Save complete response
                sessions[session_id]["messages"].append({
                    'role': 'assistant',
                    'content': full_response,
                    'timestamp': datetime.now().isoformat()
                })
                yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming response
            message = client.messages.create(
                model=config["anthropic"]["model"],
                max_tokens=config["anthropic"]["max_tokens"],
                temperature=config["anthropic"]["temperature"],
                messages=claude_messages
            )
            response = message.content[0].text

            # Add assistant response to history
            sessions[session_id]["messages"].append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })

            return jsonify({
                'response': response,
                'history': sessions[session_id]["messages"],
                'session_id': session_id,
                'streaming': False
            })

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return jsonify({'error': error_msg}), 500


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions"""
    sessions_list = []
    for sid, data in sessions.items():
        preview = data["messages"][0]["content"][:50] if data["messages"] else "Empty"
        sessions_list.append({
            'id': sid,
            'preview': preview,
            'message_count': len(data["messages"]),
            'created_at': data["created_at"],
            'updated_at': data["updated_at"]
        })
    # Sort by updated_at descending
    sessions_list.sort(key=lambda x: x['updated_at'], reverse=True)
    return jsonify({'sessions': sessions_list})


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new chat session"""
    new_id = str(uuid.uuid4())[:8]
    sessions[new_id] = {
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    global current_session_id
    current_session_id = new_id
    return jsonify({'session_id': new_id})


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session history"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({
        'history': sessions[session_id]["messages"],
        'session_id': session_id,
        'created_at': sessions[session_id]["created_at"],
        'updated_at': sessions[session_id]["updated_at"]
    })


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        global current_session_id
        if current_session_id == session_id:
            current_session_id = None
    return jsonify({'message': 'Session deleted'})


@app.route('/api/sessions/<session_id>', methods=['PUT'])
def switch_session(session_id):
    """Switch to a specific session"""
    global current_session_id
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    current_session_id = session_id
    return jsonify({'session_id': session_id, 'history': sessions[session_id]["messages"]})


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get current session chat history"""
    sid = get_or_create_session()
    return jsonify({
        'history': sessions.get(sid, {}).get("messages", []),
        'session_id': sid
    })


@app.route('/api/history', methods=['DELETE'])
def clear_history():
    """Clear current session chat history"""
    sid = get_or_create_session()
    if sid in sessions:
        sessions[sid]["messages"].clear()
        sessions[sid]["updated_at"] = datetime.now().isoformat()
    return jsonify({'message': 'Chat history cleared'})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings (without exposing API key)"""
    return jsonify({
        'model': config["anthropic"]["model"],
        'max_tokens': config["anthropic"]["max_tokens"],
        'temperature': config["anthropic"]["temperature"],
        'api_key_configured': bool(config["anthropic"].get("api_key"))
    })


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update settings"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'model' in data:
        config["anthropic"]["model"] = data['model']
    if 'max_tokens' in data:
        config["anthropic"]["max_tokens"] = data['max_tokens']
    if 'temperature' in data:
        config["anthropic"]["temperature"] = data['temperature']

    return jsonify({'message': 'Settings updated', 'settings': {
        'model': config["anthropic"]["model"],
        'max_tokens': config["anthropic"]["max_tokens"],
        'temperature': config["anthropic"]["temperature"]
    }})


if __name__ == '__main__':
    app.run(
        host=config["app"]["host"],
        port=config["app"]["port"],
        debug=config["app"]["debug"]
    )
