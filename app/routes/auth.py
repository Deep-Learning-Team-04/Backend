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
    password = data.get('password')
    username = data.get('username')

    if not email or not password or not username:
        return jsonify({"message": "Semua kolom harus diisi"}), 400

    if get_user_by_email(email).exists:
        return jsonify({"message": "Akun sudah terdaftar"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    create_user({
        'email': email,
        'password': hashed_password,
        'username': username
    })

    return jsonify({"message": "Registrasi berhasil"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email dan kata sandi wajib diisi"}), 400

    user_ref = get_user_by_email(email)

    if not user_ref.exists:
        return jsonify({"message": "Akun tidak ditemukan"}), 404

    user_data = user_ref.to_dict()
    if not bcrypt.check_password_hash(user_data['password'], password):
        return jsonify({"message": "Kata sandi salah"}), 401

    token = create_access_token(identity=user_data['email'])

    return jsonify({
        "token": token,
        "username": user_data['username'],
        "message": "Berhasil login"
    }), 200
