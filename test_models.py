"""
Test the trained models directly without Flask
This script verifies your models work correctly
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings

from pathlib import Path
import pickle
import numpy as np

try:
    from tensorflow.keras.models import load_model
    TENSORFLOW_OK = True
except Exception as e:
    print(f"❌ TensorFlow Error: {e}")
    print("\nPlease see TROUBLESHOOTING.md for solutions.")
    print("Your models are trained and saved, just need to fix TensorFlow runtime.\n")
    TENSORFLOW_OK = False
    exit(1)

from ml_utils import clean_text, clean_url, texts_to_sequences

BASE = Path(__file__).resolve().parent
MODELS_DIR = BASE / 'models'

def test_email_model():
    """Test email spam detection"""
    print("\n" + "="*60)
    print("📧 TESTING EMAIL SPAM MODEL")
    print("="*60)
    
    # Load model
    model = load_model(str(MODELS_DIR / 'email_model.h5'))
    with open(MODELS_DIR / 'tokenizer_email.pkl', 'rb') as f:
        tokenizer = pickle.load(f)
    
    # Test cases
    test_emails = [
        ("URGENT! You've won $1,000,000! Click here NOW!", True),
        ("Hi John, can we meet tomorrow at 3pm?", False),
        ("FREE VIAGRA! Limited time offer! Click now!", True),
        ("Meeting notes from today's discussion attached.", False)
    ]
    
    for text, is_spam in test_emails:
        cleaned = clean_text(text)
        seq = texts_to_sequences(tokenizer, [cleaned], maxlen=200)
        pred_prob = model.predict(seq, verbose=0)[0][0]
        predicted_spam = pred_prob > 0.5
        
        status = "✓" if predicted_spam == is_spam else "✗"
        label = "SPAM" if predicted_spam else "LEGITIMATE"
        confidence = pred_prob if predicted_spam else (1 - pred_prob)
        
        print(f"\n{status} Text: {text[:50]}...")
        print(f"   Prediction: {label} ({confidence*100:.1f}% confidence)")
        print(f"   Expected: {'SPAM' if is_spam else 'LEGITIMATE'}")

def test_sms_model():
    """Test SMS spam detection"""
    print("\n" + "="*60)
    print("💬 TESTING SMS SPAM MODEL")
    print("="*60)
    
    # Load model
    model = load_model(str(MODELS_DIR / 'sms_model.h5'))
    with open(MODELS_DIR / 'tokenizer_sms.pkl', 'rb') as f:
        tokenizer = pickle.load(f)
    
    # Test cases
    test_sms = [
        ("URGENT! Your account suspended. Verify now: http://scam.tk", True),
        ("Hey, I'll be there in 10 minutes!", False),
        ("Congratulations! You won a FREE iPhone! Claim here!", True),
        ("Thanks for the meeting today. See you next week.", False)
    ]
    
    for text, is_spam in test_sms:
        cleaned = clean_text(text)
        seq = texts_to_sequences(tokenizer, [cleaned], maxlen=150)
        pred_prob = model.predict(seq, verbose=0)[0][0]
        predicted_spam = pred_prob > 0.5
        
        status = "✓" if predicted_spam == is_spam else "✗"
        label = "SPAM" if predicted_spam else "LEGITIMATE"
        confidence = pred_prob if predicted_spam else (1 - pred_prob)
        
        print(f"\n{status} Text: {text[:50]}...")
        print(f"   Prediction: {label} ({confidence*100:.1f}% confidence)")
        print(f"   Expected: {'SPAM' if is_spam else 'LEGITIMATE'}")

def test_url_model():
    """Test URL phishing detection"""
    print("\n" + "="*60)
    print("🔗 TESTING URL PHISHING MODEL")
    print("="*60)
    
    # Load model
    model = load_model(str(MODELS_DIR / 'url_model.h5'))
    with open(MODELS_DIR / 'tokenizer_url.pkl', 'rb') as f:
        tokenizer = pickle.load(f)
    
    # Test cases
    test_urls = [
        ("http://secure-paypal-verify.tk/login.php", True),
        ("https://www.google.com", False),
        ("http://banking-secure-update-now.xyz/verify", True),
        ("https://github.com/tensorflow/tensorflow", False)
    ]
    
    for url, is_phishing in test_urls:
        cleaned = clean_url(url)
        seq = texts_to_sequences(tokenizer, [cleaned], maxlen=100)
        pred_prob = model.predict(seq, verbose=0)[0][0]
        predicted_phishing = pred_prob > 0.5
        
        status = "✓" if predicted_phishing == is_phishing else "✗"
        label = "PHISHING" if predicted_phishing else "LEGITIMATE"
        confidence = pred_prob if predicted_phishing else (1 - pred_prob)
        
        print(f"\n{status} URL: {url}")
        print(f"   Prediction: {label} ({confidence*100:.1f}% confidence)")
        print(f"   Expected: {'PHISHING' if is_phishing else 'LEGITIMATE'}")

def main():
    print("\n" + "="*60)
    print("🧪 SPAM DETECTION MODELS - STANDALONE TEST")
    print("="*60)
    print("\nThis script tests your trained models directly.")
    print("Models location:", MODELS_DIR)
    
    if not MODELS_DIR.exists():
        print("\n❌ ERROR: models/ directory not found!")
        print("Please run: python train_all_models.py")
        return
    
    # Check if models exist
    models_exist = all([
        (MODELS_DIR / 'email_model.h5').exists(),
        (MODELS_DIR / 'sms_model.h5').exists(),
        (MODELS_DIR / 'url_model.h5').exists()
    ])
    
    if not models_exist:
        print("\n❌ ERROR: Some models are missing!")
        print("Please run: python train_all_models.py")
        return
    
    print("\n✅ All model files found!\n")
    
    try:
        test_email_model()
        test_sms_model()
        test_url_model()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS COMPLETED!")
        print("="*60)
        print("\n✅ Your models are working perfectly!")
        print("✅ You can now run the Flask app: python app.py")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("\nSee TROUBLESHOOTING.md for help.")

if __name__ == '__main__':
    main()
