import os
import tempfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from google.cloud import storage
from app.services.firestore_service import (
    add_artist_data,
    get_all_artists,
    get_artist_by_id,
    get_songs_by_artist
)

artist_bp = Blueprint('artist', __name__)

GCS_BUCKET_NAME = 'model-deep-learning'

# Endpoint untuk upload artis
@artist_bp.route('/upload', methods=['POST'])
def upload_artist():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({'error': 'Gambar dan nama artis harus disertakan'}), 400

    image = request.files['image']
    name = request.form['name']

    filename = secure_filename(image.filename)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    image.save(temp_path)

    # Upload ke Cloud Storage
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f'artists/{filename}')
    blob.upload_from_filename(temp_path)
    public_url = blob.public_url

    # Simpan metadata ke Firestore
    artist_ref = add_artist_data({
        'name': name,
        'image_url': public_url
    })

    return jsonify({
        'message': 'Artis berhasil ditambahkan',
        'artist_id': artist_ref.id,
        'name': name,
        'image_url': public_url
    }), 201

# Endpoint untuk mengambil semua artis
@artist_bp.route('/', methods=['GET'])
def get_artists():
    artists = get_all_artists()
    return jsonify(artists), 200

#Endpoint untuk detail artis berdasarkan ID
@artist_bp.route('/<artist_id>', methods=['GET'])
def get_artist_detail(artist_id):
    artist = get_artist_by_id(artist_id)
    if not artist:
        return jsonify({'error': 'Artis tidak ditemukan'}), 404

    # Tambahkan lagu-lagu dari artis
    songs = get_songs_by_artist(artist_id)
    artist['songs'] = songs

    return jsonify(artist), 200
