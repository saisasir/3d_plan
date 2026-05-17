import zipfile
import os

print('Extracting Poppler...')
if not os.path.exists('poppler'):
    os.makedirs('poppler')

with zipfile.ZipFile('poppler.zip', 'r') as zip_ref:
    zip_ref.extractall('poppler')

print('Done.')
