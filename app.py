from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# In-memory sessions storage: {session_id: [{role, content}]}
sessions = {}
# Default session
current_session_id = None

def get_or_create_session():
    """Get current session or create a new one"""
    global current_session_id
    if current_session_id is None or current_session_id not in sessions:
        import uuid
        current_session_id = str(uuid.uuid4())[:8]
        sessions[current_session_id] = []
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
    """API endpoint for chat messages"""
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    session_id = data.get('session_id') or get_or_create_session()
    if session_id not in sessions:
        sessions[session_id] = []

    user_message = data['message']

    # Add user message to history
    sessions[session_id].append({'role': 'user', 'content': user_message})

    # Simple echo response (replace with AI logic as needed)
    response = f"You said: {user_message}. I'm your personal AI assistant!"

    # Add assistant response to history
    sessions[session_id].append({'role': 'assistant', 'content': response})

    return jsonify({
        'response': response,
        'history': sessions[session_id],
        'session_id': session_id
    })


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions"""
    return jsonify({
        'sessions': [{'id': sid, 'preview': sessions[sid][0]['content'][:50] if sessions[sid] else 'Empty'} for sid in sessions]
    })


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new chat session"""
    import uuid
    new_id = str(uuid.uuid4())[:8]
    sessions[new_id] = []
    return jsonify({'session_id': new_id})


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session history"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({'history': sessions[session_id], 'session_id': session_id})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({'message': 'Session deleted'})


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get current session chat history"""
    sid = get_or_create_session()
    return jsonify({'history': sessions.get(sid, []), 'session_id': sid})


@app.route('/api/history', methods=['DELETE'])
def clear_history():
    """Clear current session chat history"""
    sid = get_or_create_session()
    if sid in sessions:
        sessions[sid].clear()
    return jsonify({'message': 'Chat history cleared'})


if __name__ == '__main__':
    app.run(debug=True)
