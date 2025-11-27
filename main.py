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
        import ssl
        
        # Парсим URL вручную для pg8000
        url = urlparse(DATABASE_URL)
        
        # Извлекаем компоненты
        database = url.path[1:]  # убираем первый слеш
        user = url.username
        password = url.password
        host = url.hostname
        port = url.port or 5432  # стандартный порт PostgreSQL
        
        # Создаем SSL контекст без проверки сертификата
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        conn = pg8000.connect(
            database=database,
            user=user,
            password=password,
            host=host,
            port=port,
            ssl_context=ssl_context
        )
        print("✅ Database connected successfully!")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
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
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()
    return jsonify({"status": "OK", "database": db_status})

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


@app.route('/save', methods=['POST'])
def save_message():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (text) VALUES (%s) RETURNING id",
            (data['message'],)  # используем 'message' вместо 'text'
        )
        message_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": data['message'],  # возвращаем оригинальное сообщение
            "status": "saved"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Инициализируем БД при запуске
init_db()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)