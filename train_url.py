"""Train URL Phishing Detection Model using CNN"""
import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')

from ml_utils import clean_url, save_tokenizer, texts_to_sequences

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / 'datasets' / 'unzipped'
MODELS_DIR = BASE / 'models'
MODELS_DIR.mkdir(exist_ok=True)

def load_url_data():
    """Load and combine URL phishing datasets from url-1 and url-2 folders"""
    print('Loading URL datasets...')
    all_data = []
    
    for folder in ['url-1', 'url-2']:
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            print(f'Warning: {folder_path} not found')
            continue
        
        for file in folder_path.glob('**/*.csv'):
            print(f'  Reading {file.name}...')
            try:
                for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file, encoding=encoding, on_bad_lines='skip')
                        # Sample large datasets for speed
                        if len(df) > 30000:
                            df = df.sample(n=30000, random_state=42)
                        break
                    except:
                        continue
                
                # Find URL and label columns
                url_col = None
                label_col = None
                
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(x in col_lower for x in ['url', 'link', 'website', 'domain']):
                        url_col = col
                    if any(x in col_lower for x in ['label', 'class', 'phish', 'malicious', 'target', 'type']):
                        label_col = col
                
                # Fallback: use first two columns
                if url_col is None or label_col is None:
                    cols = df.columns.tolist()
                    if len(cols) >= 2:
                        url_col = cols[0]
                        label_col = cols[1]
                
                if url_col and label_col:
                    temp_df = df[[url_col, label_col]].copy()
                    temp_df.columns = ['url', 'label']
                    all_data.append(temp_df)
                    print(f'    ✓ Loaded {len(temp_df)} URLs')
                
            except Exception as e:
                print(f'    ✗ Error: {e}')
    
    if not all_data:
        raise ValueError('No URL data found!')
    
    df = pd.concat(all_data, ignore_index=True)
    print(f'\nTotal URLs loaded: {len(df)}')
    
    # Clean
    df['url'] = df['url'].astype(str).apply(clean_url)
    df['label'] = df['label'].astype(str).str.lower()
    
    # Encode label: CORRECT MAPPING
    # phishing/malicious/bad = 1 (SPAM), legitimate/good/benign = 0 (NOT SPAM)
    def encode_label(x):
        x = str(x).lower()
        if any(s in x for s in ['phish', 'bad', 'malicious', '1', 'true']):
            return 1  # Phishing = 1 (SPAM)
        return 0  # Legitimate = 0 (NOT SPAM)
    
    df['label'] = df['label'].map(encode_label)
    df = df[df['url'].str.len() > 5].reset_index(drop=True)
    
    print(f'After cleaning: {len(df)} URLs')
    print(f'Phishing: {df["label"].sum()}, Legitimate: {len(df) - df["label"].sum()}')
    
    return df

def build_url_model(vocab_size=5000, embed_dim=32, input_len=80):
    """Build optimized CNN model for URL classification"""
    model = Sequential([
        Embedding(vocab_size, embed_dim, input_length=input_len),
        Conv1D(64, 3, activation='relu'),
        GlobalMaxPooling1D(),
        Dense(32, activation='relu'),
        Dropout(0.4),
        Dense(16, activation='relu'),
        Dropout(0.3),
        Dense(1, activation='sigmoid')
    ])
    model.compile(
        loss='binary_crossentropy',
        optimizer='adam',
        metrics=['accuracy']
    )
    return model

def main():
    print('='*60)
    print('URL PHISHING DETECTION - MODEL TRAINING')
    print('='*60)
    
    # Load data
    df = load_url_data()
    X = df['url'].tolist()
    y = df['label'].values
    
    # Tokenize (character-level for URLs)
    print('\nTokenizing URLs...')
    tokenizer = Tokenizer(num_words=5000, char_level=True, oov_token='<OOV>')
    tokenizer.fit_on_texts(X)
    X_seq = texts_to_sequences(tokenizer, X, maxlen=80)
    
    print(f'Character vocabulary size: {min(5000, len(tokenizer.word_index))}')
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_seq, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f'\nTrain samples: {len(X_train)}, Test samples: {len(X_test)}')
    
    # Build model
    print('\nBuilding model...')
    model = build_url_model(vocab_size=5000, input_len=80)
    model.summary()
    
    print('\nTraining model (optimized for speed)...')
    es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True, verbose=1)
    
    history = model.fit(
        X_train, y_train,
        validation_split=0.1,
        epochs=5,
        batch_size=256,
        callbacks=[es],
        verbose=1
    )
    
    # Evaluate
    print('\n' + '='*60)
    print('EVALUATION RESULTS')
    print('='*60)
    
    y_pred_prob = model.predict(X_test, verbose=0)
    y_pred = (y_pred_prob > 0.5).astype(int).flatten()
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    print(f'\n📊 URL Phishing Model Metrics:')
    print(f'   Accuracy:  {acc:.4f} ({acc*100:.2f}%)')
    print(f'   Precision: {prec:.4f}')
    print(f'   Recall:    {rec:.4f}')
    print(f'   F1 Score:  {f1:.4f}')
    
    print('\n' + classification_report(y_test, y_pred, target_names=['Legitimate', 'Phishing']))
    
    # Save
    model_path = MODELS_DIR / 'url_model.h5'
    tokenizer_path = MODELS_DIR / 'tokenizer_url.pkl'
    
    model.save(str(model_path))
    save_tokenizer(tokenizer, str(tokenizer_path))
    
    print(f'\n✓ Model saved to: {model_path}')
    print(f'✓ Tokenizer saved to: {tokenizer_path}')
    print('\n' + '='*60)

if __name__ == '__main__':
    main()
