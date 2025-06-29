# app/routes/song.py

import os
import tempfile
import librosa
import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from google.cloud import storage
from tensorflow.keras.models import load_model
from app.config import db, download_model

song_bp = Blueprint('song', __name__)
GCS_BUCKET_NAME = 'model-deep-learning'

# Ambil model dari file lokal
model_path = download_model()
model = load_model(model_path)

def extract_features(audio_path):
    y, sr = librosa.load(audio_path, sr=22050)
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=128)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    mel_spec_db = mel_spec_db.T

    if mel_spec_db.shape[0] < 1000:
        pad_width = 1000 - mel_spec_db.shape[0]
        mel_spec_db = np.pad(mel_spec_db, ((0, pad_width), (0, 0)), mode='constant')
    else:
        mel_spec_db = mel_spec_db[:1000, :]

    return mel_spec_db.reshape(1, 1000, 128, 1)

@song_bp.route('/upload', methods=['POST'])
def upload_song():
    if 'file' not in request.files:
        return jsonify({'error': 'File audio tidak ditemukan'}), 400

    file = request.files['file']
    genre = request.form.get('genre')
    song_name = request.form.get('song_name')
    artist_id = request.form.get('artist_id')  # PERBAIKI INI

    filename = secure_filename(file.filename)
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    file.save(temp_path)

    # Upload ke GCS
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f'songs/{filename}')
    blob.upload_from_filename(temp_path)
    public_url = blob.public_url

    try:
        features = extract_features(temp_path)
        prediction = model.predict(features)
        predicted_mood = np.argmax(prediction[0])
    except Exception as e:
        return jsonify({'error': f'Gagal klasifikasi: {str(e)}'}), 500

    mood_labels = ['Happy', 'Sad', 'Tense', 'Relax']
    mood = mood_labels[predicted_mood] if predicted_mood < len(mood_labels) else "Unknown"

    return jsonify({
        'message': 'Lagu berhasil diupload dan diproses',
        'song_name': song_name,
        'genre': genre,
        'artist': artist_id,  # PERBAIKI INI
        'predicted_mood': mood
    }), 200


@song_bp.route("/list", methods=["GET"])
def list_songs():
    songs = []
    for doc in db.collection("songs").stream():
        data       = doc.to_dict()
        data["id"] = doc.id
        art_doc = db.collection("artists").document(data["artist_id"]).get()
        if art_doc.exists:
            art = art_doc.to_dict()
            data.update(artist_name=art.get("name"), artist_image=art.get("image_url"))
        songs.append(data)
    return jsonify(songs), 200

@song_bp.route("/artist/<artist_id>", methods=["GET"])
def list_by_artist(artist_id):
    songs = [
        {**d.to_dict(), "id": d.id}
        for d in db.collection("songs").where("artist_id", "==", artist_id).stream()
    ]
    return jsonify(songs), 200
