from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        date TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/api/search')
def search_events():
    query = request.args.get('q', '')
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events WHERE title LIKE ? OR description LIKE ?',
                         (f'%{query}%', f'%{query}%')).fetchall()
    conn.close()
    results = [dict(e) for e in events]
    return jsonify({'results': results})

@app.route('/api/events', methods=['GET'])
def events():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return jsonify([dict(e) for e in events])

@app.route('/api/events/create', methods=['POST'])
def create_event():
    conn = get_db_connection()
    data = request.json
    try:
        conn.execute('INSERT INTO events (title, description, date) VALUES (?, ?, ?)',
                     (data['title'], data.get('description', ''), data.get('date', '')))
        conn.commit()
        return jsonify({'status': 'SUCCESS'}), 201
    except Exception as e:
        return jsonify({'status': 'Event was not created', 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/events/delete/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    try:
        conn = get_db_connection()
        cur = conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        deleted = cur.rowcount
        conn.close()
        if deleted:
            return jsonify({'status': 'SUCCESS', 'id': event_id})
        else:
            return jsonify({'status': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'status': 'Error', 'error': str(e)}), 500

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
