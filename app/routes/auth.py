from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from app.services.firestore_service import create_user, get_user_by_email

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    username = data.get('username')

    if get_user_by_email(email).exists:
        return jsonify({"message": "User already exists"}), 400

    create_user({
        'email': email,
        'password': password,
        'username': username
    })

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_ref = get_user_by_email(data['email'])

    if not user_ref.exists:
        return jsonify({"message": "User not found"}), 404

    user_data = user_ref.to_dict()
    if not bcrypt.check_password_hash(user_data['password'], data['password']):
        return jsonify({"message": "Incorrect password"}), 401

    token = create_access_token(identity=user_data['email'])
    return jsonify({"token": token, "username": user_data['username']})
