"""
Train All Models - Email, SMS, and URL Detection
This script trains all three models sequentially with optimized settings for speed.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

def run_training(script_name):
    """Run a training script and display results"""
    print('\n' + '='*70)
    print(f'STARTING: {script_name}')
    print('='*70 + '\n')
    
    result = subprocess.run([sys.executable, script_name], cwd=BASE)
    
    if result.returncode != 0:
        print(f'\n❌ ERROR: {script_name} failed with exit code {result.returncode}')
        return False
    
    print(f'\n✅ SUCCESS: {script_name} completed')
    return True

def main():
    print('='*70)
    print('SPAM DETECTION SYSTEM - TRAINING ALL MODELS')
    print('='*70)
    print('\nThis will train 3 models with optimized settings:')
    print('  1. Email Spam Detection (LSTM)')
    print('  2. SMS Spam Detection (BiLSTM)')
    print('  3. URL Phishing Detection (CNN)')
    print('\nOptimizations applied:')
    print('  - Reduced model complexity for faster training')
    print('  - Smaller batch sizes and fewer epochs')
    print('  - Dataset sampling for large files')
    print('  - Early stopping to prevent overtraining')
    print('='*70)
    
    scripts = [
        ('train_email.py', 'Email Spam Model'),
        ('train_sms.py', 'SMS Spam Model'),
        ('train_url.py', 'URL Phishing Model')
    ]
    
    results = {}
    
    for script, name in scripts:
        success = run_training(script)
        results[name] = success
        
        if not success:
            print(f'\n⚠️  Warning: {name} training failed. Continuing with next model...')
    
    # Summary
    print('\n' + '='*70)
    print('TRAINING SUMMARY')
    print('='*70)
    
    for name, success in results.items():
        status = '✅ SUCCESS' if success else '❌ FAILED'
        print(f'{name:.<50} {status}')
    
    successful = sum(results.values())
    total = len(results)
    
    print(f'\nCompleted: {successful}/{total} models trained successfully')
    
    if successful == total:
        print('\n🎉 All models trained successfully!')
        print('\nNext steps:')
        print('  1. Run the Flask app: python app.py')
        print('  2. Open browser: http://127.0.0.1:5000')
        print('  3. Test the spam detection system!')
    else:
        print('\n⚠️  Some models failed. Check the error messages above.')
    
    print('='*70)

if __name__ == '__main__':
    main()
