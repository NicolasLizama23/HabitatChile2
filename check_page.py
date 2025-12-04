import os
import sys

# usar mismo settings que manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pjrEjemplo.settings')

import django
from django.test import Client

django.setup()

client = Client()
resp = client.get('/')
print('STATUS:', resp.status_code)
# si hay contenido HTML grande, imprime encabezado y primeros 4000 caracteres
content = resp.content.decode('utf-8', errors='replace')
print('\n--- CONTENT START (first 4000 chars) ---\n')
print(content[:4000])
print('\n--- CONTENT END ---')

# si la respuesta contiene la página de debug (500), guardarla en un archivo para inspección
if resp.status_code == 500:
    with open('debug_500.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('\nSaved debug HTML to debug_500.html')
