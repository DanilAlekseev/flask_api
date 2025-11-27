from flask import Flask, request, jsonify
import pg8000
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Подключение к БД
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("DATABASE_URL environment variable is not set")
        return None
    
    try:
        url = urlparse(DATABASE_URL)
        conn = pg8000.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Создаем таблицу если её нет
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")

@app.route('/')
def hello():
    return jsonify({
        "message": "Hello, Serverless!",
        "status": "success"
    })

@app.route('/health')
def health():
    return jsonify({"status": "OK", "database": "connected"})

@app.route('/messages', methods=['GET'])
def get_messages():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, created_at FROM messages ORDER BY created_at DESC")
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for msg in messages:
            result.append({
                "id": msg[0],
                "text": msg[1],
                "created_at": msg[2].isoformat() if msg[2] else None
            })
        
        return jsonify({"messages": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/messages', methods=['POST'])
def add_message():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Text is required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (text) VALUES (%s) RETURNING id",
            (data['text'],)
        )
        message_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Message added successfully",
            "id": message_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/echo', methods=['POST'])
def echo():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    return jsonify({
        "received_data": data,
        "data_length": len(str(data)),
        "status": "processed"
    })

# Инициализируем БД при запуске
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)