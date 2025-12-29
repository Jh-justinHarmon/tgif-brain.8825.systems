#!/usr/bin/env python3
"""
Jh Brain Service - Persistent System Memory
"""

from flask import Flask, request, jsonify
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CAPABILITY_MAP_PATH = Path(__file__).parent.parent.parent / "brain/capability_map.json"
USAGE_LOG_PATH = Path.home() / ".8825" / "jh_brain_usage.jsonl"

# Ensure log directory exists
USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load capability map
with open(CAPABILITY_MAP_PATH) as f:
    CAPABILITY_MAP = json.load(f)

# In-memory usage stats (also persisted to JSONL)
USAGE_STATS = {}

@app.route('/query', methods=['POST'])
def query_system():
    """Map needs to tools"""
    data = request.get_json()
    need = data.get('need', '').lower()
    
    if not need:
        return jsonify({'error': 'Need parameter is required'}), 400
    
    # Find best matching capability
    best_match = None
    best_score = 0
    
    for cap_id, cap_info in CAPABILITY_MAP['capabilities'].items():
        score = sum(1 for kw in cap_info['keywords'] if kw.lower() in need)
        
        if score > best_score:
            best_score = score
            best_match = {
                'capability': cap_id,
                'description': cap_info['description'],
                'tool_id': cap_info['tool_id']
            }
    
    if best_match:
        tool_info = CAPABILITY_MAP['tools'][best_match['tool_id']]
        return jsonify({
            'match': best_match,
            'tool': tool_info,
            'confidence': 'high' if best_score >= 2 else 'medium'
        })
    
    return jsonify({'error': 'No tool found for this need'}), 404


@app.route('/log_use', methods=['POST'])
def log_use():
    """Log tool usage for learning. Both Cascade and Goose call this."""
    data = request.get_json()
    tool_id = data.get('tool_id', 'unknown')
    need = data.get('need', '')
    success = data.get('success', True)
    source = data.get('source', 'unknown')  # 'cascade' or 'goose'
    notes = data.get('notes', '')
    
    # Update in-memory stats
    if tool_id not in USAGE_STATS:
        USAGE_STATS[tool_id] = {'success': 0, 'failure': 0, 'total': 0}
    USAGE_STATS[tool_id]['total'] += 1
    if success:
        USAGE_STATS[tool_id]['success'] += 1
    else:
        USAGE_STATS[tool_id]['failure'] += 1
    
    # Persist to JSONL
    entry = {
        'ts': datetime.now().isoformat(),
        'tool_id': tool_id,
        'need': need,
        'success': success,
        'source': source,
        'notes': notes
    }
    try:
        with open(USAGE_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass
    
    return jsonify({'status': 'logged', 'tool_id': tool_id, 'source': source})


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get usage statistics."""
    return jsonify(USAGE_STATS)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'tools': len(USAGE_STATS)})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5160)
