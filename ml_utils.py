"""ML utilities for text preprocessing and tokenizer management"""
import re
import pickle

def clean_text(text: str) -> str:
    """Clean and normalize text data"""
    if not isinstance(text, str):
        return ''
    text = text.lower()
    # Replace URLs
    text = re.sub(r'http\S+|www\S+|https\S+', ' urltoken ', text)
    # Replace emails
    text = re.sub(r'\S+@\S+', ' emailtoken ', text)
    # Remove special characters but keep spaces
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_url(url: str) -> str:
    """Clean URL for feature extraction"""
    if not isinstance(url, str):
        return ''
    url = url.lower()
    # Extract domain and path features
    url = re.sub(r'https?://', '', url)
    # Keep dots, slashes, hyphens for URL structure
    url = re.sub(r'[^a-z0-9\.\-/]', '', url)
    return url

def save_tokenizer(tokenizer, path: str):
    """Save tokenizer to disk"""
    with open(path, 'wb') as f:
        pickle.dump(tokenizer, f)
    print(f'Tokenizer saved to {path}')

def load_tokenizer(path: str):
    """Load tokenizer from disk"""
    with open(path, 'rb') as f:
        return pickle.load(f)

def texts_to_sequences(tokenizer, texts, maxlen=200):
    """Convert texts to padded sequences - imports TensorFlow only when called"""
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    seq = tokenizer.texts_to_sequences(texts)
    return pad_sequences(seq, maxlen=maxlen, padding='post', truncating='post')
