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
    from app.routes.user import user_bp
    from app.routes.artist import artist_bp
    from app.routes.playlist import playlist_bp
    from app.routes.song import song_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp)
    app.register_blueprint(artist_bp, url_prefix='/artists')
    app.register_blueprint(playlist_bp, url_prefix='/playlists')
    app.register_blueprint(song_bp, url_prefix='/songs')
    
    return app
