"""Unzip all dataset files from datasets/ into datasets/unzipped/"""
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATASETS_DIR = BASE / 'datasets'
OUT_DIR = DATASETS_DIR / 'unzipped'

OUT_DIR.mkdir(parents=True, exist_ok=True)

def unzip_all():
    zip_files = list(DATASETS_DIR.glob('*.zip'))
    if not zip_files:
        print('No ZIP files found in datasets/')
        return
    
    for z in zip_files:
        print(f'Unzipping {z.name}...')
        try:
            with zipfile.ZipFile(z, 'r') as zip_ref:
                dest = OUT_DIR / z.stem
                dest.mkdir(parents=True, exist_ok=True)
                zip_ref.extractall(dest)
                print(f'  ✓ Extracted to {dest}')
        except Exception as e:
            print(f'  ✗ Error: {e}')
    
    print(f'\nDone! All datasets extracted to {OUT_DIR}')

if __name__ == '__main__':
    unzip_all()
