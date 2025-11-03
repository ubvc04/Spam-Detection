"""Gemini AI Verification Module for Spam Detection"""
import os
from google import genai

# Set API key
GEMINI_API_KEY = "AIzaSyB4BymL2yAtfvHI6WWAlBiA_v3UIsfr2bQ"
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

def verify_with_gemini(content, content_type="text"):
    """
    Verify content with Gemini AI for spam/phishing detection
    
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
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Create type-specific prompt
        if content_type == "email":
            prompt = f"""Analyze this email and determine if it's SPAM or LEGITIMATE.
            
Email Content:
{content}

Respond in this exact format:
CLASSIFICATION: [SPAM or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

Consider these spam indicators:
- Suspicious sender addresses
- Urgent/threatening language
- Requests for personal information
- Poor grammar/spelling
- Phishing attempts
- Unsolicited offers
- Suspicious links"""

        elif content_type == "sms":
            prompt = f"""Analyze this SMS message and determine if it's SPAM or LEGITIMATE.
            
SMS Content:
{content}

Respond in this exact format:
CLASSIFICATION: [SPAM or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

Consider these spam indicators:
- Prize/lottery notifications
- Click bait links
- Requests for personal info
- Urgent action required
- Unknown sender offering deals
- Phishing attempts"""

        else:  # url
            prompt = f"""Analyze this URL and determine if it's PHISHING or LEGITIMATE.
            
URL:
{content}

Respond in this exact format:
CLASSIFICATION: [PHISHING or LEGITIMATE]
CONFIDENCE: [0-100]
REASON: [Brief explanation in one sentence]

Consider these phishing indicators:
- Suspicious domain names (typosquatting)
- Non-HTTPS for sensitive sites
- Unusual TLDs (.tk, .ml, .ru, etc.)
- IP addresses instead of domains
- Suspicious subdomains
- URL shorteners
- Misspelled brand names"""

        # Get Gemini response
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        # Parse response
        result_text = response.text.strip()
        
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
        
        return {
            'is_spam': is_spam,
            'confidence': min(100.0, max(0.0, confidence)),
            'reason': reason,
            'verified_by': 'Gemini AI'
        }
        
    except Exception as e:
        print(f"Gemini verification error: {e}")
        # Fallback: assume legitimate if verification fails
        return {
            'is_spam': False,
            'confidence': 50.0,
            'reason': f"Verification service unavailable: {str(e)}",
            'verified_by': 'Gemini AI (Error)'
        }


def test_gemini():
    """Test Gemini API connection"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Respond with: OK"
        )
        print("✓ Gemini API connection successful")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"✗ Gemini API error: {e}")
        return False


if __name__ == "__main__":
    # Test the API
    print("Testing Gemini API...")
    test_gemini()
    
    # Test verification
    print("\n" + "="*60)
    print("Testing spam verification...")
    test_email = "CONGRATULATIONS! You've won $1,000,000! Click here now to claim your prize!"
    result = verify_with_gemini(test_email, "email")
    print(f"Result: {result}")
