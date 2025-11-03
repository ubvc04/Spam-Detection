"""Test the retrained URL model"""
from tensorflow.keras.models import load_model
from ml_utils import load_tokenizer, texts_to_sequences, clean_url

# Load model
model = load_model('models/url_model.h5')
tokenizer = load_tokenizer('models/tokenizer_url.pkl')

test_cases = [
    ('http://security-alert.example/login?dkim=false', 'PHISHING'),
    ('http://paypal-verify.tk/login.php', 'PHISHING'),
    ('https://www.google.com', 'LEGITIMATE'),
    ('https://www.amazon.com/products', 'LEGITIMATE'),
    ('http://apple-id-verify.ru/signin', 'PHISHING'),
]

print('='*70)
print('URL MODEL TEST RESULTS')
print('='*70)

for url, expected in test_cases:
    cleaned = clean_url(url)
    seq = texts_to_sequences(tokenizer, [cleaned], maxlen=80)
    pred = model.predict(seq, verbose=0)[0][0]
    
    is_phishing = pred > 0.5
    classification = 'PHISHING' if is_phishing else 'LEGITIMATE'
    confidence = pred * 100 if is_phishing else (1 - pred) * 100
    
    status = '✓' if classification == expected else '✗'
    
    print(f'\n{status} {url}')
    print(f'   Prediction: {pred:.4f}')
    print(f'   Result: {classification} ({confidence:.2f}% confidence)')
    print(f'   Expected: {expected}')
