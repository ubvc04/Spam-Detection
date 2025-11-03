"""Train Email Spam Detection Model using LSTM"""
import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, SpatialDropout1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')

from ml_utils import clean_text, save_tokenizer, texts_to_sequences

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / 'datasets' / 'unzipped'
MODELS_DIR = BASE / 'models'
MODELS_DIR.mkdir(exist_ok=True)

def load_email_data():
    """Load and combine email datasets from email-1 and email-2 folders"""
    print('Loading email datasets...')
    all_data = []
    
    # Search for CSV files in email-1 and email-2 folders
    for folder in ['email-1', 'email-2']:
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            print(f'Warning: {folder_path} not found')
            continue
        
        for file in folder_path.glob('**/*.csv'):
            print(f'  Reading {file.name}...')
            try:
                # Try different encodings - sample only 50% of large files for speed
                for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file, encoding=encoding, on_bad_lines='skip')
                        # Sample large datasets for faster training
                        if len(df) > 20000:
                            df = df.sample(n=20000, random_state=42)
                        break
                    except:
                        continue
                
                # Common column name patterns for email spam datasets
                # Try to identify text and label columns
                text_col = None
                label_col = None
                
                # Check for common column names
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(x in col_lower for x in ['text', 'message', 'email', 'body', 'content']):
                        text_col = col
                    if any(x in col_lower for x in ['label', 'class', 'spam', 'category', 'target']):
                        label_col = col
                
                # If not found, use first two columns (common format)
                if text_col is None or label_col is None:
                    cols = df.columns.tolist()
                    if len(cols) >= 2:
                        label_col = cols[0]
                        text_col = cols[1]
                
                if text_col and label_col:
                    temp_df = df[[label_col, text_col]].copy()
                    temp_df.columns = ['label', 'text']
                    all_data.append(temp_df)
                    print(f'    ✓ Loaded {len(temp_df)} emails')
                
            except Exception as e:
                print(f'    ✗ Error reading {file.name}: {e}')
    
    if not all_data:
        raise ValueError('No email data found! Make sure datasets are unzipped.')
    
    # Combine all data
    df = pd.concat(all_data, ignore_index=True)
    print(f'\nTotal emails loaded: {len(df)}')
    
    # Clean and encode labels
    df['text'] = df['text'].astype(str).apply(clean_text)
    df['label'] = df['label'].astype(str).str.lower()
    df['label'] = df['label'].map(lambda x: 1 if any(s in str(x) for s in ['spam', '1', 'true']) else 0)
    
    # Remove empty texts
    df = df[df['text'].str.len() > 5].reset_index(drop=True)
    
    print(f'After cleaning: {len(df)} emails')
    print(f'Spam: {df["label"].sum()}, Ham: {len(df) - df["label"].sum()}')
    
    return df

def build_email_model(vocab_size=15000, embed_dim=64, input_len=150):
    """Build optimized LSTM model for email classification"""
    model = Sequential([
        Embedding(vocab_size, embed_dim, input_length=input_len),
        SpatialDropout1D(0.3),
        LSTM(64, dropout=0.3, recurrent_dropout=0.3),
        Dense(32, activation='relu'),
        Dropout(0.4),
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
    print('EMAIL SPAM DETECTION - MODEL TRAINING')
    print('='*60)
    
    # Load data
    df = load_email_data()
    X = df['text'].tolist()
    y = df['label'].values
    
    # Sample dataset for faster training (use 30% of data)
    if len(X) > 30000:
        print(f'\nSampling dataset for faster training (using 30000 samples)...')
        indices = np.random.choice(len(X), 30000, replace=False)
        X = [X[i] for i in indices]
        y = y[indices]
    
    # Create tokenizer
    print('\nTokenizing texts...')
    tokenizer = Tokenizer(num_words=15000, oov_token='<OOV>')
    tokenizer.fit_on_texts(X)
    X_seq = texts_to_sequences(tokenizer, X, maxlen=150)
    
    print(f'Vocabulary size: {min(15000, len(tokenizer.word_index))}')
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_seq, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f'\nTrain samples: {len(X_train)}, Test samples: {len(X_test)}')
    
    # Build and train model
    print('\nBuilding model...')
    model = build_email_model(vocab_size=15000, input_len=150)
    model.summary()
    
    print('\nTraining model (optimized for speed)...')
    es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True, verbose=1)
    
    history = model.fit(
        X_train, y_train,
        validation_split=0.1,
        epochs=5,
        batch_size=128,
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
    
    print(f'\n📊 Email Spam Model Metrics:')
    print(f'   Accuracy:  {acc:.4f} ({acc*100:.2f}%)')
    print(f'   Precision: {prec:.4f}')
    print(f'   Recall:    {rec:.4f}')
    print(f'   F1 Score:  {f1:.4f}')
    
    print('\n' + classification_report(y_test, y_pred, target_names=['Ham', 'Spam']))
    
    # Save model and tokenizer
    model_path = MODELS_DIR / 'email_model.h5'
    tokenizer_path = MODELS_DIR / 'tokenizer_email.pkl'
    
    model.save(str(model_path))
    save_tokenizer(tokenizer, str(tokenizer_path))
    
    print(f'\n✓ Model saved to: {model_path}')
    print(f'✓ Tokenizer saved to: {tokenizer_path}')
    print('\n' + '='*60)

if __name__ == '__main__':
    main()
