"""Flask Web Application for Spam Detection System"""
from flask import Flask, render_template, request, jsonify
from pathlib import Path
import numpy as np
import os
from werkzeug.utils import secure_filename
import warnings
warnings.filterwarnings('ignore')

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
from gemini_verifier import verify_with_gemini
from file_extractor import extract_text_from_file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spam-detection-system-2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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

@app.route('/')
def index():
    """Home page with three detection options"""
    return render_template('index.html')

@app.route('/email')
def email_page():
    """Email spam detection page"""
    return render_template('email.html')

@app.route('/sms')
def sms_page():
    """SMS spam detection page"""
    return render_template('sms.html')

@app.route('/url')
def url_page():
    """URL phishing detection page"""
    return render_template('url.html')

@app.route('/stats')
def stats_page():
    """Statistics and model comparison page"""
    return render_template('stats.html', metrics=model_metrics)

@app.route('/api/predict/email', methods=['POST'])
def predict_email():
    """Predict email spam"""
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
        
        # Stage 1: Predict with trained model
        pred_prob = email_model.predict(seq, verbose=0)[0][0]
        is_spam = bool(pred_prob > 0.5)
        
        # Calculate confidence correctly
        # pred_prob is the probability of being SPAM
        if is_spam:
            model_confidence = float(pred_prob)  # Confidence in SPAM prediction
        else:
            model_confidence = float(1 - pred_prob)  # Confidence in LEGITIMATE prediction
        
        # Stage 2: Two-stage verification
        # If model says SPAM -> trust it and show result
        # If model says LEGITIMATE -> verify with Gemini AI
        if is_spam:
            # Model detected SPAM - trust the model
            return jsonify({
                'success': True,
                'is_spam': True,
                'confidence': round(model_confidence * 100, 2),
                'label': 'Spam',
                'type': 'email',
                'verification': 'Model Detection',
                'stage': 'Stage 1: Deep Learning Model'
            })
        else:
            # Model says LEGITIMATE - verify with Gemini AI
            gemini_result = verify_with_gemini(text, content_type="email")
            
            # If Gemini also says legitimate, show legitimate
            # If Gemini says spam, show spam with Gemini's confidence
            if gemini_result['is_spam']:
                # Gemini detected SPAM (model missed it)
                return jsonify({
                    'success': True,
                    'is_spam': True,
                    'confidence': gemini_result['confidence'],
                    'label': 'Spam',
                    'type': 'email',
                    'verification': 'Gemini AI (Model missed this)',
                    'reason': gemini_result['reason'],
                    'stage': 'Stage 2: AI Verification',
                    'model_confidence': round(model_confidence * 100, 2)
                })
            else:
                # Both model and Gemini say LEGITIMATE
                return jsonify({
                    'success': True,
                    'is_spam': False,
                    'confidence': gemini_result['confidence'],
                    'label': 'Legitimate',
                    'type': 'email',
                    'verification': 'Verified by Gemini AI',
                    'reason': gemini_result['reason'],
                    'stage': 'Stage 2: AI Verification',
                    'model_confidence': round(model_confidence * 100, 2)
                })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/predict/sms', methods=['POST'])
def predict_sms():
    """Predict SMS spam"""
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
        
        # Stage 1: Predict with trained model
        pred_prob = sms_model.predict(seq, verbose=0)[0][0]
        is_spam = bool(pred_prob > 0.5)
        
        # Calculate confidence correctly
        if is_spam:
            model_confidence = float(pred_prob)
        else:
            model_confidence = float(1 - pred_prob)
        
        # Stage 2: Two-stage verification
        if is_spam:
            # Model detected SPAM - trust it
            return jsonify({
                'success': True,
                'is_spam': True,
                'confidence': round(model_confidence * 100, 2),
                'label': 'Spam',
                'type': 'sms',
                'verification': 'Model Detection',
                'stage': 'Stage 1: Deep Learning Model'
            })
        else:
            # Model says LEGITIMATE - verify with Gemini AI
            gemini_result = verify_with_gemini(text, content_type="sms")
            
            if gemini_result['is_spam']:
                # Gemini detected SPAM (model missed it)
                return jsonify({
                    'success': True,
                    'is_spam': True,
                    'confidence': gemini_result['confidence'],
                    'label': 'Spam',
                    'type': 'sms',
                    'verification': 'Gemini AI (Model missed this)',
                    'reason': gemini_result['reason'],
                    'stage': 'Stage 2: AI Verification',
                    'model_confidence': round(model_confidence * 100, 2)
                })
            else:
                # Both model and Gemini say LEGITIMATE
                return jsonify({
                    'success': True,
                    'is_spam': False,
                    'confidence': gemini_result['confidence'],
                    'label': 'Legitimate',
                    'type': 'sms',
                    'verification': 'Verified by Gemini AI',
                    'reason': gemini_result['reason'],
                    'stage': 'Stage 2: AI Verification',
                    'model_confidence': round(model_confidence * 100, 2)
                })
        
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
        
        # Stage 1: Predict with trained model
        pred_prob = url_model.predict(seq, verbose=0)[0][0]
        is_phishing = bool(pred_prob > 0.5)
        
        # Calculate confidence correctly
        if is_phishing:
            model_confidence = float(pred_prob)
        else:
            model_confidence = float(1 - pred_prob)
        
        # Stage 2: ALWAYS verify with Gemini AI (model is unreliable)
        # Gemini AI makes the final decision
        gemini_result = verify_with_gemini(url_text, content_type="url")
        
        if gemini_result['is_spam']:
            # Gemini detected PHISHING
            return jsonify({
                'success': True,
                'is_spam': True,
                'confidence': gemini_result['confidence'],
                'label': 'Phishing',
                'type': 'url',
                'verification': 'Gemini AI',
                'reason': gemini_result['reason'],
                'stage': 'AI Verification',
                'model_said': 'Phishing' if is_phishing else 'Legitimate',
                'model_confidence': round(model_confidence * 100, 2)
            })
        else:
            # Gemini says LEGITIMATE
            return jsonify({
                'success': True,
                'is_spam': False,
                'confidence': gemini_result['confidence'],
                'label': 'Legitimate',
                'type': 'url',
                'verification': 'Verified by Gemini AI',
                'reason': gemini_result['reason'],
                'stage': 'AI Verification',
                'model_said': 'Phishing' if is_phishing else 'Legitimate',
                'model_confidence': round(model_confidence * 100, 2)
            })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/metrics')
def get_metrics():
    """Return model metrics for stats page"""
    return jsonify(model_metrics)

@app.route('/api/upload/extract', methods=['POST'])
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
                'error': 'File type not supported. Allowed: images, PDF, DOCX, TXT',
                'success': False
            }), 400
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)
        
        # Extract text
        extracted_text = extract_text_from_file(filepath)
        
        # Clean up file
        try:
            os.remove(filepath)
        except:
            pass
        
        if not extracted_text or extracted_text.startswith('Error'):
            return jsonify({
                'error': extracted_text or 'No text could be extracted',
                'success': False
            }), 400
        
        return jsonify({
            'success': True,
            'text': extracted_text,
            'filename': filename
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
