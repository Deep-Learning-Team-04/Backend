import os
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

db = None

def init_firestore():
    global db

    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not credential_path:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS belum dikonfigurasi."
        )

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credential_path

    db = firestore.Client()