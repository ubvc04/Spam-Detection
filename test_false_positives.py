"""Test why passport URL is showing as phishing"""
from tensorflow.keras.models import load_model
from ml_utils import load_tokenizer, texts_to_sequences, clean_url

# Load URL model
model = load_model('models/url_model.h5')
tokenizer = load_tokenizer('models/tokenizer_url.pkl')

# Test URLs
test_urls = [
    ('https://www.passportindia.gov.in/psp', 'LEGITIMATE (Official Govt)'),
    ('https://www.google.com', 'LEGITIMATE'),
    ('https://www.amazon.com', 'LEGITIMATE'),
    ('http://paypal-verify.tk/login', 'PHISHING'),
    ('http://secure-bank-login.ru', 'PHISHING'),
]

print("="*70)
print("URL MODEL TESTING - Finding False Positives")
print("="*70)

for url, expected in test_urls:
    cleaned = clean_url(url)
    seq = texts_to_sequences(tokenizer, [cleaned], maxlen=80)
    pred = model.predict(seq, verbose=0)[0][0]
    
    is_phishing = pred > 0.5
    result = 'PHISHING' if is_phishing else 'LEGITIMATE'
    confidence = pred * 100 if is_phishing else (1 - pred) * 100
    
    status = '✓' if result in expected else '✗ FALSE POSITIVE!'
    
    print(f"\n{status} URL: {url}")
    print(f"   Cleaned: {cleaned}")
    print(f"   Prediction: {pred:.4f}")
    print(f"   Result: {result} ({confidence:.2f}%)")
    print(f"   Expected: {expected}")
