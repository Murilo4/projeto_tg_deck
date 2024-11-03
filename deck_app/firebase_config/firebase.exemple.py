import firebase_admin
from firebase_admin import credentials, storage

# Inicialize o Firebase Admin SDK
cred = credentials.Certificate('caminho/para/seu/arquivo/firebase_key.json')  # Altere para o caminho correto
firebase_admin.initialize_app(cred, {
    'storageBucket': 'seu-bucket.appspot.com'  # Substitua pelo seu bucket
})

bucket = storage.bucket()
