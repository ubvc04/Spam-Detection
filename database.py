"""Database models for User Authentication and Search History"""
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / 'spam_detection.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Search history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_type TEXT NOT NULL,
            input_text TEXT NOT NULL,
            result TEXT NOT NULL,
            confidence REAL,
            verification TEXT,
            reason TEXT,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print('✓ Database initialized')

# User functions
def create_user(username, email, password):
    """Create a new user"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {'success': True, 'user_id': user_id}
    except sqlite3.IntegrityError as e:
        conn.close()
        if 'username' in str(e):
            return {'success': False, 'error': 'Username already exists'}
        elif 'email' in str(e):
            return {'success': False, 'error': 'Email already registered'}
        return {'success': False, 'error': 'Registration failed'}

def verify_user(username, password):
    """Verify user credentials"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return {'success': True, 'user': dict(user)}
    return {'success': False, 'error': 'Invalid username or password'}

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# Search history functions
def save_search(user_id, search_type, input_text, result, confidence, verification=None, reason=None):
    """Save a search to history"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO search_history (user_id, search_type, input_text, result, confidence, verification, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, search_type, input_text[:500], result, confidence, verification, reason))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=50):
    """Get search history for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM search_history 
        WHERE user_id = ? 
        ORDER BY searched_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    history = cursor.fetchall()
    conn.close()
    return [dict(row) for row in history]

def get_user_stats(user_id):
    """Get statistics for a user"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total searches
    cursor.execute('SELECT COUNT(*) as total FROM search_history WHERE user_id = ?', (user_id,))
    total = cursor.fetchone()['total']
    
    # Searches by type
    cursor.execute('''
        SELECT search_type, COUNT(*) as count 
        FROM search_history 
        WHERE user_id = ? 
        GROUP BY search_type
    ''', (user_id,))
    by_type = {row['search_type']: row['count'] for row in cursor.fetchall()}
    
    # Spam vs Legitimate
    cursor.execute('''
        SELECT result, COUNT(*) as count 
        FROM search_history 
        WHERE user_id = ? 
        GROUP BY result
    ''', (user_id,))
    by_result = {row['result']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return {
        'total': total,
        'by_type': by_type,
        'by_result': by_result
    }

def delete_history_item(user_id, history_id):
    """Delete a single history item"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM search_history WHERE id = ? AND user_id = ?', (history_id, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def clear_user_history(user_id):
    """Clear all history for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM search_history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Initialize database on import
init_db()
