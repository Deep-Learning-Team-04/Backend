import os
import uuid

from flask import Blueprint, request, jsonify, url_for
from werkzeug.utils import secure_filename

from app.services.firestore_service import (
    add_artist_data,
    get_all_artists,
    get_artist_by_id,
    get_songs_by_artist
)

artist_bp = Blueprint('artist', __name__)

# Folder penyimpanan gambar artist
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'static',
    'artists'
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# UPLOAD ARTIST
# =========================

@artist_bp.route('/upload', methods=['POST'])
def upload_artist():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({
            'error': 'Gambar dan nama artis harus disertakan'
        }), 400

    image = request.files['image']
    name = request.form['name']

    if image.filename == '':
        return jsonify({
            'error': 'File gambar tidak dipilih'
        }), 400

    # Amankan nama file
    original_filename = secure_filename(image.filename)

    # Buat nama unik agar tidak bentrok
    extension = os.path.splitext(original_filename)[1]
    filename = f"{uuid.uuid4().hex}{extension}"

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    # Simpan gambar secara lokal
    image.save(file_path)

    # URL gambar yang dapat diakses melalui Flask
    image_url = url_for(
        'static',
        filename=f'artists/{filename}',
        _external=True
    )

    # Simpan metadata ke Firestore
    artist_ref = add_artist_data({
        'name': name,
        'image_url': image_url
    })

    return jsonify({
        'message': 'Artis berhasil ditambahkan',
        'artist_id': artist_ref.id,
        'name': name,
        'image_url': image_url
    }), 201


# =========================
# GET ALL ARTISTS
# =========================

@artist_bp.route('/', methods=['GET'])
def get_artists():
    artists = get_all_artists()
    return jsonify(artists), 200


# =========================
# GET ARTIST DETAIL
# =========================

@artist_bp.route('/<artist_id>', methods=['GET'])
def get_artist_detail(artist_id):
    artist = get_artist_by_id(artist_id)

    if not artist:
        return jsonify({
            'error': 'Artis tidak ditemukan'
        }), 404

    songs = get_songs_by_artist(artist_id)
    artist['songs'] = songs

    return jsonify(artist), 200