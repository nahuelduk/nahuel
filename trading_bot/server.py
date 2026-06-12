"""
Web interface for Trading Bot — Flask app
"""
from flask import Flask, render_template, jsonify, request
import subprocess
import json
from pathlib import Path
import threading
import time

app = Flask(__name__)
bot_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    global bot_process
    state_file = Path('bot_state.json')
    state = {}

    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)

    return jsonify({
        'running': bot_process is not None and bot_process.poll() is None,
        'portfolio': state.get('portfolio', {}),
        'trades': state.get('trades', [])[-10:],
        'signals': state.get('signals', [])[-20:]
    })

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_process
    if bot_process and bot_process.poll() is None:
        return jsonify({'error': 'Bot already running'}), 400

    try:
        bot_process = subprocess.Popen(
            ['python', 'core/bot.py'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return jsonify({'status': 'Bot started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_process
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
        bot_process = None
    return jsonify({'status': 'Bot stopped'})

if __name__ == '__main__':
    print('🌐 Opening http://localhost:5000')
    app.run(debug=False, port=5000)
