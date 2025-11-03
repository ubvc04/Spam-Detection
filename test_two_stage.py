"""Test Two-Stage Verification System"""
import requests
import json

API_URL = "http://127.0.0.1:5000/api/predict"

def test_email(text, description):
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Input: {text[:100]}...")
    
    response = requests.post(f"{API_URL}/email", json={"text": text})
    data = response.json()
    
    if data['success']:
        print(f"\n✓ Result: {data['label']}")
        print(f"  Confidence: {data['confidence']}%")
        print(f"  Verification: {data.get('verification', 'N/A')}")
        print(f"  Stage: {data.get('stage', 'N/A')}")
        if 'reason' in data:
            print(f"  Reason: {data['reason']}")
        if 'model_confidence' in data:
            print(f"  Model Confidence: {data['model_confidence']}%")
    else:
        print(f"✗ Error: {data['error']}")

def test_sms(text, description):
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Input: {text}")
    
    response = requests.post(f"{API_URL}/sms", json={"text": text})
    data = response.json()
    
    if data['success']:
        print(f"\n✓ Result: {data['label']}")
        print(f"  Confidence: {data['confidence']}%")
        print(f"  Verification: {data.get('verification', 'N/A')}")
        print(f"  Stage: {data.get('stage', 'N/A')}")
        if 'reason' in data:
            print(f"  Reason: {data['reason']}")
        if 'model_confidence' in data:
            print(f"  Model Confidence: {data['model_confidence']}%")
    else:
        print(f"✗ Error: {data['error']}")

def test_url(url, description):
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Input: {url}")
    
    response = requests.post(f"{API_URL}/url", json={"text": url})
    data = response.json()
    
    if data['success']:
        print(f"\n✓ Result: {data['label']}")
        print(f"  Confidence: {data['confidence']}%")
        print(f"  Verification: {data.get('verification', 'N/A')}")
        print(f"  Stage: {data.get('stage', 'N/A')}")
        if 'reason' in data:
            print(f"  Reason: {data['reason']}")
        if 'model_confidence' in data:
            print(f"  Model Confidence: {data['model_confidence']}%")
    else:
        print(f"✗ Error: {data['error']}")

print("\n" + "="*70)
print("TWO-STAGE VERIFICATION SYSTEM TEST")
print("="*70)
print("\nStage 1: Deep Learning Model detects spam → Shows result immediately")
print("Stage 2: If model says legitimate → Gemini AI verifies")
print("="*70)

# Test 1: Obvious spam (should be caught by model in Stage 1)
test_email(
    "CONGRATULATIONS! You've won $1,000,000! Click here now: http://scam.tk",
    "Obvious spam email (Stage 1 detection expected)"
)

# Test 2: Legitimate-looking email (should go to Stage 2)
test_email(
    "Hi, this is a reminder about our team meeting tomorrow at 2 PM. Please bring your reports.",
    "Legitimate professional email (Stage 2 verification expected)"
)

# Test 3: Subtle spam that model might miss (Stage 2 should catch)
test_email(
    "Dear valued customer, your account has unusual activity. Please verify your identity by logging in here.",
    "Subtle phishing attempt (Model might miss, Gemini should catch)"
)

# Test 4: Obvious SMS spam
test_sms(
    "WIN A FREE IPHONE! Text WINNER to 12345 NOW!",
    "Obvious SMS spam (Stage 1 expected)"
)

# Test 5: Legitimate SMS
test_sms(
    "Your package from Amazon has been delivered. Thank you for shopping with us!",
    "Legitimate delivery notification (Stage 2 verification expected)"
)

# Test 6: Phishing URL (should be caught by model)
test_url(
    "http://paypal-verify.tk/login.php",
    "Obvious phishing URL (Stage 1 expected)"
)

# Test 7: Legitimate URL
test_url(
    "https://www.google.com",
    "Legitimate URL (Stage 2 verification expected)"
)

# Test 8: Subtle phishing URL
test_url(
    "http://secure-account-verification.example.com/update",
    "Subtle phishing attempt (Model might miss, Gemini should catch)"
)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
