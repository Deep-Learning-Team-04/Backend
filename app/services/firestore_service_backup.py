from app.config import db

def create_user(data):
    users_ref = db.collection('users')
    users_ref.document(data['email']).set(data)

def get_user_by_email(email):
    return db.collection('users').document(email).get()
