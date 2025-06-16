import os
from google.cloud import firestore

db = None

def init_firestore():
    global db
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    db = firestore.Client()
