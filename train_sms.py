"""Train SMS Spam Detection Model using LSTM"""
import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, SpatialDropout1D, Bidirectional
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')

from ml_utils import clean_text, save_tokenizer, texts_to_sequences

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / 'datasets' / 'unzipped'
MODELS_DIR = BASE / 'models'
MODELS_DIR.mkdir(exist_ok=True)

def load_sms_data():
    """Load SMS spam dataset"""
    print('Loading SMS dataset...')
    
    sms_folder = DATA_DIR / 'sms'
    if not sms_folder.exists():
        raise ValueError(f'SMS dataset folder not found: {sms_folder}')
    
    all_data = []
    
    # Search for CSV/TSV/TXT files
    for file in sms_folder.glob('**/*'):
        if file.suffix.lower() in ['.csv', '.tsv', '.txt']:
            print(f'  Reading {file.name}...')
            try:
                # Try different delimiters and encodings
                for sep in ['\t', ',', '|']:
                    for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                        try:
                            df = pd.read_csv(file, sep=sep, encoding=encoding, on_bad_lines='skip', header=None)
                            if len(df.columns) >= 2 and len(df) > 10:
                                # Assume first column is label, second is text
                                temp_df = df.iloc[:, [0, 1]].copy()
                                temp_df.columns = ['label', 'text']
                                all_data.append(temp_df)
                                print(f'    ✓ Loaded {len(temp_df)} messages')
                                break
                        except:
                            continue
                    if all_data and len(all_data[-1]) > 10:
                        break
            except Exception as e:
                print(f'    ✗ Error: {e}')
    
    if not all_data:
        raise ValueError('No SMS data found!')
    
    df = pd.concat(all_data, ignore_index=True)
    print(f'\nTotal SMS messages: {len(df)}')
    
    # Clean data
    df['text'] = df['text'].astype(str).apply(clean_text)
    df['label'] = df['label'].astype(str).str.lower()
    df['label'] = df['label'].map(lambda x: 1 if any(s in str(x) for s in ['spam', '1', 'true']) else 0)
    
    df = df[df['text'].str.len() > 3].reset_index(drop=True)
    
    print(f'After cleaning: {len(df)} messages')
    print(f'Spam: {df["label"].sum()}, Ham: {len(df) - df["label"].sum()}')
    
    return df

def build_sms_model(vocab_size=8000, embed_dim=64, input_len=100):
    """Build optimized BiLSTM model for SMS classification"""
    model = Sequential([
        Embedding(vocab_size, embed_dim, input_length=input_len),
        SpatialDropout1D(0.3),
        Bidirectional(LSTM(32, dropout=0.3, recurrent_dropout=0.3)),
        Dense(16, activation='relu'),
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
    print('SMS SPAM DETECTION - MODEL TRAINING')
    print('='*60)
    
    # Load data
    df = load_sms_data()
    X = df['text'].tolist()
    y = df['label'].values
    
    # Tokenize
    print('\nTokenizing texts...')
    tokenizer = Tokenizer(num_words=8000, oov_token='<OOV>')
    tokenizer.fit_on_texts(X)
    X_seq = texts_to_sequences(tokenizer, X, maxlen=100)
    
    print(f'Vocabulary size: {min(8000, len(tokenizer.word_index))}')
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_seq, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f'\nTrain samples: {len(X_train)}, Test samples: {len(X_test)}')
    
    # Build model
    print('\nBuilding model...')
    model = build_sms_model(vocab_size=8000, input_len=100)
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
    
    print(f'\n📊 SMS Spam Model Metrics:')
    print(f'   Accuracy:  {acc:.4f} ({acc*100:.2f}%)')
    print(f'   Precision: {prec:.4f}')
    print(f'   Recall:    {rec:.4f}')
    print(f'   F1 Score:  {f1:.4f}')
    
    print('\n' + classification_report(y_test, y_pred, target_names=['Ham', 'Spam']))
    
    # Save
    model_path = MODELS_DIR / 'sms_model.h5'
    tokenizer_path = MODELS_DIR / 'tokenizer_sms.pkl'
    
    model.save(str(model_path))
    save_tokenizer(tokenizer, str(tokenizer_path))
    
    print(f'\n✓ Model saved to: {model_path}')
    print(f'✓ Tokenizer saved to: {tokenizer_path}')
    print('\n' + '='*60)

if __name__ == '__main__':
    main()
