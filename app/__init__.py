import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.config import init_firestore

def create_app():
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = os.getenv("SECRET_KEY")

    CORS(app)
    JWTManager(app)
    init_firestore()

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
