"""Flask Web Application for Spam Detection System"""
import os
# Suppress TensorFlow warnings BEFORE importing TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF logs (0=all, 1=info, 2=warning, 3=error)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN warnings

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
from pathlib import Path
import numpy as np
from werkzeug.utils import secure_filename
import warnings
warnings.filterwarnings('ignore')

# Suppress TensorFlow deprecation warnings
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# Lazy import TensorFlow to avoid DLL issues on startup
def lazy_load_model(path):
    """Lazy load Keras model only when needed"""
    try:
        from tensorflow.keras.models import load_model
        return load_model(str(path))
    except Exception as e:
        print(f'Error loading model from {path}: {e}')
        return None

from ml_utils import clean_text, clean_url, load_tokenizer, texts_to_sequences
from openrouter_verifier import verify_with_openrouter
from file_extractor import extract_text_from_file
from database import (
    create_user, verify_user, get_user_by_id, 
    save_search, get_user_history, get_user_stats,
    delete_history_item, clear_user_history
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spam-detection-system-2025-secure-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Error handler for file too large
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'error': 'File too large. Maximum size is 16MB.',
        'success': False
    }), 413

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user"""
    if 'user_id' in session:
        return get_user_by_id(session['user_id'])
    return None

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / 'models'
UPLOAD_DIR = BASE / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf', 'docx', 'doc', 'txt', 'eml'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Global variables for models and tokenizers
email_model = None
email_tokenizer = None
sms_model = None
sms_tokenizer = None
url_model = None
url_tokenizer = None

# Model metrics (stored after training)
model_metrics = {
    'email': {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
    'sms': {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
    'url': {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
}

def load_models():
    """Load all trained models and tokenizers"""
    global email_model, email_tokenizer, sms_model, sms_tokenizer, url_model, url_tokenizer
    
    try:
        # Load Email model
        email_model_path = MODELS_DIR / 'email_model.h5'
        email_tok_path = MODELS_DIR / 'tokenizer_email.pkl'
        if email_model_path.exists() and email_tok_path.exists():
            email_model = lazy_load_model(email_model_path)
            email_tokenizer = load_tokenizer(str(email_tok_path))
            if email_model:
                print('✓ Email model loaded')
        
        # Load SMS model
        sms_model_path = MODELS_DIR / 'sms_model.h5'
        sms_tok_path = MODELS_DIR / 'tokenizer_sms.pkl'
        if sms_model_path.exists() and sms_tok_path.exists():
            sms_model = lazy_load_model(sms_model_path)
            sms_tokenizer = load_tokenizer(str(sms_tok_path))
            if sms_model:
                print('✓ SMS model loaded')
        
        # Load URL model
        url_model_path = MODELS_DIR / 'url_model.h5'
        url_tok_path = MODELS_DIR / 'tokenizer_url.pkl'
        if url_model_path.exists() and url_tok_path.exists():
            url_model = lazy_load_model(url_model_path)
            url_tokenizer = load_tokenizer(str(url_tok_path))
            if url_model:
                print('✓ URL model loaded')
        
    except Exception as e:
        print(f'Error loading models: {e}')
        print('\nTroubleshooting:')
        print('1. TensorFlow DLL issue detected')
        print('2. Try: pip install --upgrade tensorflow')
        print('3. Or install Microsoft Visual C++ Redistributable')
        print('4. Models are trained and saved, just need TensorFlow runtime fix')

# ========== AUTHENTICATION ROUTES ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter username and password', 'error')
            return render_template('login.html')
        
        result = verify_user(username, password)
        if result['success']:
            session['user_id'] = result['user']['id']
            session['username'] = result['user']['username']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash(result['error'], 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('signup.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        result = create_user(username, email, password)
        if result['success']:
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['error'], 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# ========== MAIN ROUTES ==========

@app.route('/')
@login_required
def index():
    """Home page with three detection options"""
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/email')
@login_required
def email_page():
    """Email spam detection page"""
    user = get_current_user()
    return render_template('email.html', user=user)

@app.route('/sms')
@login_required
def sms_page():
    """SMS spam detection page"""
    user = get_current_user()
    return render_template('sms.html', user=user)

@app.route('/url')
@login_required
def url_page():
    """URL phishing detection page"""
    user = get_current_user()
    return render_template('url.html', user=user)

@app.route('/stats')
@login_required
def stats_page():
    """Statistics and model comparison page"""
    user = get_current_user()
    return render_template('stats.html', metrics=model_metrics, user=user)

@app.route('/history')
@login_required
def history_page():
    """User search history page"""
    user = get_current_user()
    history = get_user_history(session['user_id'])
    stats = get_user_stats(session['user_id'])
    return render_template('history.html', user=user, history=history, stats=stats)

# ========== API ROUTES ==========

@app.route('/api/predict/email', methods=['POST'])
def predict_email():
    """Predict email spam - Combined ML + AI approach for real-world detection"""
    try:
        if email_model is None or email_tokenizer is None:
            return jsonify({
                'error': 'Email model not loaded. Please train the model first.',
                'success': False
            }), 503
        
        data = request.get_json()
        text = data.get('text', '')
        
        if not text or len(text.strip()) < 5:
            return jsonify({
                'error': 'Please enter a valid email text',
                'success': False
            }), 400
        
        # Preprocess
        cleaned = clean_text(text)
        seq = texts_to_sequences(email_tokenizer, [cleaned], maxlen=150)
        
        # Stage 1: Predict with ML model first (preliminary check)
        pred_prob = email_model.predict(seq, verbose=0)[0][0]
        model_says_spam = bool(pred_prob > 0.5)
        model_spam_prob = float(pred_prob)
        
        # Stage 2: ALWAYS send to OpenRouter AI for final verification
        ai_result = verify_with_openrouter(text, content_type="email")
        ai_says_spam = ai_result['is_spam']
        
        # Final decision is based on AI result
        if ai_says_spam:
            result = {
                'success': True,
                'is_spam': True,
                'confidence': ai_result['confidence'],
                'label': 'Spam',
                'type': 'email',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'Spam detected by AI'),
                'stage': 'Final: AI Verified Spam',
                'model_prediction': 'Spam' if model_says_spam else 'Legitimate',
                'model_confidence': round(model_spam_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        else:
            result = {
                'success': True,
                'is_spam': False,
                'confidence': ai_result['confidence'],
                'label': 'Legitimate',
                'type': 'email',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'Content verified as legitimate'),
                'stage': 'Final: AI Verified Legitimate',
                'model_prediction': 'Spam' if model_says_spam else 'Legitimate',
                'model_confidence': round((1 - model_spam_prob) * 100, 2) if not model_says_spam else round(model_spam_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        
        # Save to history if user is logged in
        if 'user_id' in session:
            save_search(session['user_id'], 'email', text, result['label'],
                       result['confidence'], result['verification'], result.get('reason'))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/predict/sms', methods=['POST'])
def predict_sms():
    """Predict SMS spam - Combined ML + AI approach for real-world detection"""
    try:
        if sms_model is None or sms_tokenizer is None:
            return jsonify({
                'error': 'SMS model not loaded. Please train the model first.',
                'success': False
            }), 503
        
        data = request.get_json()
        text = data.get('text', '')
        
        if not text or len(text.strip()) < 3:
            return jsonify({
                'error': 'Please enter a valid SMS message',
                'success': False
            }), 400
        
        # Preprocess
        cleaned = clean_text(text)
        seq = texts_to_sequences(sms_tokenizer, [cleaned], maxlen=100)
        
        # Stage 1: Predict with ML model first (preliminary check)
        pred_prob = sms_model.predict(seq, verbose=0)[0][0]
        model_says_spam = bool(pred_prob > 0.5)
        model_spam_prob = float(pred_prob)
        
        # Stage 2: ALWAYS send to OpenRouter AI for final verification
        ai_result = verify_with_openrouter(text, content_type="sms")
        ai_says_spam = ai_result['is_spam']
        
        # Final decision is based on AI result
        if ai_says_spam:
            result = {
                'success': True,
                'is_spam': True,
                'confidence': ai_result['confidence'],
                'label': 'Spam',
                'type': 'sms',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'Spam detected by AI'),
                'stage': 'Final: AI Verified Spam',
                'model_prediction': 'Spam' if model_says_spam else 'Legitimate',
                'model_confidence': round(model_spam_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        else:
            result = {
                'success': True,
                'is_spam': False,
                'confidence': ai_result['confidence'],
                'label': 'Legitimate',
                'type': 'sms',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'Content verified as legitimate'),
                'stage': 'Final: AI Verified Legitimate',
                'model_prediction': 'Spam' if model_says_spam else 'Legitimate',
                'model_confidence': round((1 - model_spam_prob) * 100, 2) if not model_says_spam else round(model_spam_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        
        if 'user_id' in session:
            save_search(session['user_id'], 'sms', text, result['label'],
                       result['confidence'], result['verification'], result.get('reason'))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/predict/url', methods=['POST'])
def predict_url():
    """Predict URL phishing"""
    try:
        if url_model is None or url_tokenizer is None:
            return jsonify({
                'error': 'URL model not loaded. Please train the model first.',
                'success': False
            }), 503
        
        data = request.get_json()
        url_text = data.get('text', '')
        
        if not url_text or len(url_text.strip()) < 5:
            return jsonify({
                'error': 'Please enter a valid URL',
                'success': False
            }), 400
        
        # Preprocess
        cleaned = clean_url(url_text)
        seq = texts_to_sequences(url_tokenizer, [cleaned], maxlen=80)
        
        # Stage 1: Predict with ML model first (preliminary check)
        pred_prob = url_model.predict(seq, verbose=0)[0][0]
        model_says_phishing = bool(pred_prob > 0.5)
        model_phishing_prob = float(pred_prob)
        
        # Stage 2: ALWAYS send to OpenRouter AI for final verification
        ai_result = verify_with_openrouter(url_text, content_type="url")
        ai_says_phishing = ai_result['is_spam']
        
        # Final decision is based on AI result
        if ai_says_phishing:
            result = {
                'success': True,
                'is_spam': True,
                'confidence': ai_result['confidence'],
                'label': 'Phishing',
                'type': 'url',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'Phishing detected by AI'),
                'stage': 'Final: AI Verified Phishing',
                'model_prediction': 'Phishing' if model_says_phishing else 'Legitimate',
                'model_confidence': round(model_phishing_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        else:
            result = {
                'success': True,
                'is_spam': False,
                'confidence': ai_result['confidence'],
                'label': 'Legitimate',
                'type': 'url',
                'verification': 'OpenRouter AI Verification',
                'reason': ai_result.get('reason', 'URL verified as legitimate'),
                'stage': 'Final: AI Verified Legitimate',
                'model_prediction': 'Phishing' if model_says_phishing else 'Legitimate',
                'model_confidence': round((1 - model_phishing_prob) * 100, 2) if not model_says_phishing else round(model_phishing_prob * 100, 2),
                'ai_confidence': ai_result['confidence']
            }
        
        if 'user_id' in session:
            save_search(session['user_id'], 'url', url_text, result['label'],
                       result['confidence'], result['verification'], result.get('reason'))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/metrics')
def get_metrics():
    """Return model metrics for stats page"""
    return jsonify(model_metrics)

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history(history_id):
    """Delete a single history item"""
    success = delete_history_item(session['user_id'], history_id)
    return jsonify({'success': success})

@app.route('/api/history/clear', methods=['DELETE'])
@login_required
def clear_history():
    """Clear all history for user"""
    clear_user_history(session['user_id'])
    return jsonify({'success': True})

@app.route('/api/upload/extract', methods=['POST'])
@login_required
def upload_and_extract():
    """Upload file and extract text"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded', 'success': False}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'File type not supported. Allowed: images, PDF, DOCX, TXT, EML',
                'success': False
            }), 400
        
        # Save file with unique name to avoid conflicts
        import uuid
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        filepath = os.path.join(UPLOAD_DIR, unique_filename)
        file.save(filepath)
        
        # Extract text
        extracted_text = extract_text_from_file(filepath)
        
        # Clean up file
        try:
            os.remove(filepath)
        except:
            pass
        
        # Check if extraction failed or returned error message
        if not extracted_text:
            return jsonify({
                'error': 'No text could be extracted from the file',
                'success': False
            }), 400
        
        if extracted_text.startswith('Error'):
            return jsonify({
                'error': extracted_text,
                'success': False
            }), 400
        
        if 'No text found' in extracted_text or 'not supported' in extracted_text:
            return jsonify({
                'error': extracted_text,
                'success': False
            }), 400
        
        return jsonify({
            'success': True,
            'text': extracted_text,
            'filename': original_filename
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

if __name__ == '__main__':
    print('='*60)
    print('SPAM DETECTION SYSTEM - Starting Flask App')
    print('='*60)
    load_models()
    print('='*60)
    print('Server running at: http://127.0.0.1:5000')
    print('Press CTRL+C to quit')
    print('='*60)
    app.run(debug=True, host='127.0.0.1', port=5000)
