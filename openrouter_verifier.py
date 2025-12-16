"""OpenRouter AI Verification Module for Spam Detection"""
import os
import requests

# OpenRouter API Configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def verify_with_openrouter(content, content_type="text"):
    """
    Verify content with OpenRouter AI for spam/phishing detection
    
    Args:
        content: The text/email/URL to verify
        content_type: Type of content - 'email', 'sms', or 'url'
    
    Returns:
        dict: {
            'is_spam': bool,
            'confidence': float (0-100),
            'reason': str
        }
    """
    try:
        print(f"🤖 OpenRouter AI: Verifying {content_type} content...")
        
        # OpenRouter API headers
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create type-specific prompt with comprehensive spam detection
        if content_type == "email":
            prompt = f"""You are an expert spam detection system. Analyze this email and determine if it's SPAM or LEGITIMATE.

Email Content:
---
{content}
---

IMPORTANT: Be BALANCED in your analysis. Only classify as SPAM if there are clear spam indicators. Normal business emails, personal communications, and routine messages should be classified as LEGITIMATE.

Respond in this exact format:
CLASSIFICATION: [SPAM or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

SPAM indicators (classify as SPAM only if these are present):
- Unsolicited commercial content or advertisements
- Prize/lottery/winner notifications you didn't enter
- Requests for personal info (passwords, SSN, bank details, OTP)
- Urgency/threatening language ("act now", "account suspended", "verify immediately")
- Too-good-to-be-true offers (free money, inheritance, lottery)
- Phishing attempts (fake login pages, brand impersonation)
- Poor grammar/spelling (often intentional to bypass filters)
- Cryptocurrency/investment schemes
- Fake job offers requiring fees
- Romance scams from strangers
- Tech support scams
- Donation requests from unknown sources
- Suspicious links
- "You've won" or "Congratulations" from unknown sources
- Requests to transfer money or gift cards
- Fake invoices or receipts
- Account verification requests you didn't initiate

LEGITIMATE indicators (classify as LEGITIMATE if these apply):
- Normal business communications
- Personal messages from known contacts
- Meeting invitations and calendar events
- Project updates and work discussions
- Newsletter subscriptions user opted into
- Order confirmations from known retailers
- Password reset requests user initiated
- Normal social media notifications"""

        elif content_type == "sms":
            prompt = f"""You are an expert spam detection system. Analyze this SMS message and determine if it's SPAM or LEGITIMATE.

SMS Content:
---
{content}
---

IMPORTANT: Be BALANCED in your analysis. Only classify as SPAM if there are clear spam indicators. Normal personal messages and legitimate notifications should be classified as LEGITIMATE.

Respond in this exact format:
CLASSIFICATION: [SPAM or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

SPAM indicators (classify as SPAM only if these are present):
- Prize/lottery/winner notifications
- Shortened links from unknown numbers requesting action
- Requests for personal info or OTP codes you didn't initiate
- Urgent action required with threats
- Bank/account verification requests you didn't initiate
- Package delivery scams (unexpected delivery with payment required)
- Free gift or offer messages from unknown numbers
- Loan/credit card offers from unknown numbers
- Job offers via SMS requiring payment
- Investment or crypto opportunities
- Government impersonation (IRS, SSA scams)
- Fake delivery notifications requiring payment
- Messages claiming your account is compromised

LEGITIMATE indicators (classify as LEGITIMATE if these apply):
- Messages from known contacts
- Appointment reminders from businesses you use
- Delivery notifications from expected orders
- Two-factor authentication codes you requested
- Bank alerts for transactions you made
- Service notifications from subscribed services"""

        else:  # url
            prompt = f"""You are an expert phishing detection system. Analyze this URL and determine if it's PHISHING/MALICIOUS or LEGITIMATE.

URL:
---
{content}
---

IMPORTANT: Be BALANCED in your analysis. Only classify as PHISHING if there are clear malicious indicators. Well-known domains and legitimate websites should be classified as LEGITIMATE.

Respond in this exact format:
CLASSIFICATION: [PHISHING or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

PHISHING indicators to check (if ANY apply, likely PHISHING):
- Typosquatting (misspelled domains: paypa1.com, amaz0n.com, g00gle.com)
- Suspicious TLDs (.tk, .ml, .ga, .cf, .gq, .xyz, .top, .work, .click)
- IP addresses instead of domain names
- Excessive subdomains (login.secure.bank.suspicious.com)
- Brand names in subdomain (paypal.malicious-site.com)
- URL shorteners for sensitive actions (bit.ly, tinyurl for login)
- Non-HTTPS for login/payment pages
- Random string domains (abc123xyz.com)
- Lookalike characters (using 0 for o, 1 for l, rn for m)
- Suspicious keywords in URL (secure-login, verify-account, update-info)
- Very long URLs with hidden domains
- Domains registered recently (often used for attacks)
- Free hosting domains (*.000webhostapp.com, *.herokuapp.com for phishing)
- Known malicious patterns
- URLs that don't match the claimed brand
- Login pages on unusual domains"""

        # OpenRouter API - using AI models via OpenRouter
        models_to_try = ["google/gemini-2.0-flash-001", "google/gemini-2.0-flash-lite-001", "google/gemini-2.5-flash-preview"]
        
        response = None
        last_error = None
        for model_name in models_to_try:
            try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
                
                api_response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if api_response.status_code == 200:
                    response = api_response.json()
                    break  # Success, exit loop
                elif api_response.status_code == 429:
                    continue  # Rate limited, try next model
                else:
                    api_response.raise_for_status()
                    
            except Exception as model_error:
                last_error = model_error
                if "429" in str(model_error) or "rate" in str(model_error).lower():
                    continue  # Try next model
                else:
                    continue  # Try next model for any error
        
        if response is None:
            raise last_error if last_error else Exception("All models exhausted quota")
        
        # Parse OpenRouter response
        result_text = response['choices'][0]['message']['content'].strip()
        
        # Extract classification
        classification_line = [line for line in result_text.split('\n') if 'CLASSIFICATION:' in line]
        confidence_line = [line for line in result_text.split('\n') if 'CONFIDENCE:' in line]
        reason_line = [line for line in result_text.split('\n') if 'REASON:' in line]
        
        if not classification_line or not confidence_line:
            # Fallback parsing
            is_spam = any(word in result_text.upper() for word in ['SPAM', 'PHISHING'])
            confidence = 75.0  # Default confidence
            reason = "AI analysis completed"
        else:
            classification = classification_line[0].split(':', 1)[1].strip().upper()
            is_spam = 'SPAM' in classification or 'PHISHING' in classification
            
            try:
                confidence_str = confidence_line[0].split(':', 1)[1].strip()
                confidence = float(''.join(filter(str.isdigit, confidence_str)))
            except:
                confidence = 75.0
            
            reason = reason_line[0].split(':', 1)[1].strip() if reason_line else "AI analysis completed"
        
        print(f"✅ OpenRouter AI Result: {'SPAM' if is_spam else 'LEGITIMATE'} (Confidence: {confidence}%)")
        
        return {
            'is_spam': is_spam,
            'confidence': min(100.0, max(0.0, confidence)),
            'reason': reason,
            'verified_by': 'OpenRouter AI'
        }
        
    except Exception as e:
        print(f"❌ OpenRouter verification error: {e}")
        # Fallback: assume legitimate if verification fails
        return {
            'is_spam': False,
            'confidence': 50.0,
            'reason': f"Verification service unavailable: {str(e)}",
            'verified_by': 'OpenRouter AI (Error)'
        }


def test_openrouter():
    """Test OpenRouter API connection"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "user", "content": "Respond with: OK"}
            ]
        }
        
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ OpenRouter API connection successful")
            print(f"Response: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"✗ OpenRouter API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ OpenRouter API error: {e}")
        return False


if __name__ == "__main__":
    # Test the API
    print("Testing OpenRouter API...")
    test_openrouter()
    
    # Test verification
    print("\n" + "="*60)
    print("Testing spam verification...")
    test_email = "CONGRATULATIONS! You've won $1,000,000! Click here now to claim your prize!"
    result = verify_with_openrouter(test_email, "email")
    print(f"Result: {result}")
