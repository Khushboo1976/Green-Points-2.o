import os
import io
import time
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8501"])  # Enable CORS for frontend integration

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# Config
FASTAPI_ANALYZE_URL = os.getenv("FASTAPI_ANALYZE_URL", "http://127.0.0.1:8000/analyze")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5MB limit
ALLOWED_MIME = {"image/jpeg", "image/png"}

# SQLite database path
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / os.getenv("DB_PATH", "green_points.db")

# Ensure database exists
if not DB_PATH.exists():
    print(f"Database not found at {DB_PATH}. Creating...")
    from setup_sqlite import setup_database
    setup_database(DB_PATH.name)

def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn

from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if user exists
        cur.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cur.fetchone():
            return jsonify({'error': 'Username or email already exists'}), 409
        
        password_hash = generate_password_hash(password)
        cur.execute(
            'INSERT INTO users (username, email, password_hash, is_email_verified) VALUES (?, ?, ?, 1)',
            (username, email, password_hash)
        )
        conn.commit()
        return jsonify({'message': 'Signup successful'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, username, email, password_hash FROM users WHERE email = ?', (email,))
        user_row = cur.fetchone()
        if not user_row:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user_id, username, _, password_hash = user_row
        
        if not check_password_hash(password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        conn.close()
        return jsonify({
            'user': {'id': user_id, 'username': username, 'email': email},
            'message': 'Login successful'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()



def dict_factory(cursor, row):
    """Convert row to dict."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@app.post("/analyze_post")
def analyze_post():
    """Accepts multipart/form-data: file, text, username.
    Forwards to FastAPI /analyze. If allow=True, updates user points and saves post.
    Returns JSON with updated points or error.
    """
    file = request.files.get("file")
    text = request.form.get("text", "").strip()
    username = request.form.get("username", "").strip()

    if not file or not text or not username:
        return jsonify({"error": "Missing file, text, or username"}), 400

    # Basic validation: size and MIME type
    # Validate MIME
    if file.mimetype not in ALLOWED_MIME:
        return jsonify({"error": "Unsupported file type"}), 400

    # Validate file size (<= 5MB)
    try:
        current_pos = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size_bytes = file.stream.tell()
        file.stream.seek(0)
    except Exception:
        size_bytes = 0
    if size_bytes > MAX_FILE_BYTES:
        return jsonify({"error": "File too large (max 5MB)"}), 413

    # Save uploaded image to shared uploads directory
    filename = secure_filename(file.filename or f"upload_{int(time.time())}.jpg")
    save_path = os.path.join(UPLOAD_DIR, filename)
    file_path = None
    try:
        file.stream.seek(0)
        file.save(save_path)
        file_path = save_path
    except Exception:
        return jsonify({"error": "Failed to save file"}), 500

    # Forward to FastAPI /analyze
    try:
        with open(save_path, "rb") as f:
            files = {"file": (filename, f, file.mimetype or "image/jpeg")}
            data = {"text": text, "username": username}
            resp = requests.post(FASTAPI_ANALYZE_URL, files=files, data=data, timeout=120)
        analyze_json = resp.json()
    except Exception:
        # AI service unavailable
        # Cleanup saved file
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return jsonify({"error": "AI service unavailable"}), 503

    allow = bool(analyze_json.get("allow"))
    points_awarded = int(analyze_json.get("points", 0))
    category = analyze_json.get("category", "Other")

    if not allow:
        # Do not retain rejected content
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return jsonify({"error": "Content violates community policy"}), 400

    # Persist: increment user points and insert post
    conn = None
    image_rel_path = f"uploads/{filename}"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update points and insert post in a single transaction
        # First, get or create user
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cur.fetchone()
        if not user_row:
            # Create user if doesn't exist
            cur.execute(
                "INSERT INTO users (username, email, password_hash, is_email_verified) VALUES (?, ?, ?, ?)",
                (username, f"{username}@example.com", "temp_hash", 1)
            )
            user_id = cur.lastrowid
        else:
            user_id = user_row[0]
        
        # Update points in leaderboard table (SQLite upsert)
        cur.execute("SELECT points FROM leaderboard WHERE user_id = ?", (user_id,))
        leaderboard_row = cur.fetchone()
        if leaderboard_row:
            new_points = leaderboard_row[0] + points_awarded
            cur.execute(
                "UPDATE leaderboard SET points = ?, last_update = CURRENT_TIMESTAMP WHERE user_id = ?",
                (new_points, user_id)
            )
        else:
            cur.execute(
                "INSERT INTO leaderboard (user_id, points) VALUES (?, ?)",
                (user_id, points_awarded)
            )
            new_points = points_awarded

        # Insert post
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO posts (user_id, post_text, status, created_at) VALUES (?, ?, ?, ?)",
            (user_id, text, "approved", created_at)
        )
        post_id = cur.lastrowid

        # Insert post image
        cur.execute(
            "INSERT INTO post_images (post_id, image_url, created_at) VALUES (?, ?, ?)",
            (post_id, image_rel_path, created_at)
        )

        # Insert points transaction
        cur.execute(
            "INSERT INTO points_transactions (user_id, post_id, points, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, post_id, points_awarded, f"Post approved: {category}", created_at)
        )

        conn.commit()
        updated_points = new_points

    except Exception as e:
        if conn:
            conn.rollback()
        # Cleanup saved file because DB persistence failed
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({
        "message": "Post published and points awarded",
        "updatedPoints": updated_points if updated_points is not None else None,
        "awardedPoints": points_awarded,
        "category": category,
        "imagePath": image_rel_path,
    }), 200


@app.get("/api/community")
def get_community_posts():
    """Get all approved posts for community feed."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                p.id AS post_id,
                p.user_id AS user_id,
                u.username AS username,
                u.email AS email,
                pr.profile_image_url AS profile_image_url,
                p.title AS title,
                p.description AS description,
                p.post_text AS post_text,
                p.external_url AS external_url,
                p.created_at AS created_at,
                p.updated_at AS updated_at,
                pi.id AS image_id,
                pi.image_url AS image_url,
                pi.phash AS phash,
                pi.width AS width,
                pi.height AS height
            FROM posts p
            INNER JOIN users u ON u.id = p.user_id
            LEFT JOIN profiles pr ON pr.user_id = p.user_id
            LEFT JOIN post_images pi ON pi.post_id = p.id
            WHERE p.status = 'approved'
            ORDER BY p.created_at DESC, pi.id ASC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        # Aggregate images per post
        post_dict = {}
        for row in rows:
            post_id = row[0]
            if post_id not in post_dict:
                post_dict[post_id] = {
                    "id": post_id,
                    "userId": row[1],
                    "username": row[2],
                    "email": row[3],
                    "profileImageUrl": row[4],
                    "title": row[5],
                    "description": row[6],
                    "postText": row[7],
                    "externalUrl": row[8],
                    "createdAt": row[9],
                    "updatedAt": row[10],
                    "images": []
                }
            if row[11]:  # image_id
                post_dict[post_id]["images"].append({
                    "id": row[11],
                    "url": row[12],
                    "phash": row[13],
                    "width": row[14],
                    "height": row[15]
                })
        
        return jsonify({"posts": list(post_dict.values())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/user/<username>/points")
def get_user_points(username):
    """Get user's total points."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        if not user:
            conn.close()
            return jsonify({"points": 0}), 200
        
        user_id = user[0]
        cur.execute("SELECT points FROM leaderboard WHERE user_id = ?", (user_id,))
        leaderboard = cur.fetchone()
        conn.close()
        
        points = leaderboard[0] if leaderboard else 0
        return jsonify({"points": points})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "7000"))
    print(f"🚀 Flask API starting on port {port}")
    print(f"📁 Database: {DB_PATH}")
    app.run(host="0.0.0.0", port=port, debug=True)


