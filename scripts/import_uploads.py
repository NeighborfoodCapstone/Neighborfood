"""Optional: upload existing local images; filenames and DB references are preserved."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.config
from app import storage
from app.db.auth_db import get_conn

parser=argparse.ArgumentParser()
parser.add_argument('directory',help='Existing uploads directory')
args=parser.parse_args()
folder=Path(args.directory).resolve()
if not folder.is_dir(): raise SystemExit('Upload directory not found')
if not storage.enabled(): raise SystemExit('Storage environment settings required')
with get_conn() as db:
    receipts={r['image_path'] for r in db.execute('SELECT image_path FROM receipts WHERE image_path IS NOT NULL')}
for file in sorted(folder.iterdir()):
    if not file.is_file(): continue
    bucket='receipts' if file.name in receipts or file.name.startswith('receipt_') else 'food-images'
    storage.save(bucket,file.name,file.read_bytes())
    print(f'{bucket}/{file.name}')
print('Finished. Existing objects are not overwritten; duplicate uploads fail safely.')
