from flask import Blueprint, request, jsonify
from app.services.firestore_service import get_user_mood
from google.cloud import firestore
from app.services.firestore_service import (
    log_user_song_play,
    get_user_favorite_genres,
    add_user_favorite_artist,
    get_user_favorite_artists
)
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

user_bp = Blueprint('user_bp', __name__)
db = firestore.Client()

@user_bp.route('/songs/play', methods=['POST'])
def play_song():
    data = request.get_json()
    user_id = data.get('user_id')
    song_id = data.get('song_id')

    if not user_id or not song_id:
        return jsonify({'error': 'user_id and song_id are required'}), 400

    log_user_song_play(user_id, song_id)
    return jsonify({'message': f'Song {song_id} played by user {user_id}'}), 200

@user_bp.route('/users/<user_id>/mood', methods=['POST'])
def save_user_mood(user_id):
    data = request.get_json()
    mood = data.get('mood')

    if not mood:
        return jsonify({'error': 'Mood is required'}), 400

    db.collection('moods').document(user_id).set({'mood': mood})
    return jsonify({'message': f'Mood {mood} saved for user {user_id}'}), 200

@user_bp.route('/users/<user_id>/mood', methods=['GET'])
def get_user_daily_mood(user_id):
    mood = get_user_mood(user_id)
    if not mood:
        return jsonify({'message': f'Mood harian untuk user {user_id} belum diset'}), 404

    return jsonify({'user_id': user_id, 'mood': mood}), 200

@user_bp.route('/users/<user_id>/favorite-artist', methods=['POST'])
def add_favorite_artist(user_id):
    data = request.get_json()
    artist_id = data.get('artist_id')

    if not artist_id:
        return jsonify({'error': 'artist_id is required'}), 400

    add_user_favorite_artist(user_id, artist_id)
    return jsonify({'message': f'Artist {artist_id} added to favorites for user {user_id}'}), 200


@user_bp.route('/users/<user_id>/favorite-genres', methods=['GET'])
def favorite_genres(user_id):
    genres = get_user_favorite_genres(user_id)
    return jsonify({'user_id': user_id, 'favorite_genres': genres}), 200

@user_bp.route('/users/<user_id>/favorite-artists', methods=['GET'])
def get_favorite_artists(user_id):
    artists = get_user_favorite_artists(user_id)
    return jsonify({'user_id': user_id, 'favorite_artists': artists}), 200

@user_bp.route('/users/<user_id>/recommendations', methods=['GET'])
def get_recommendations(user_id):
    # Ambil preferensi user
    mood = get_user_mood(user_id)
    genres = get_user_favorite_genres(user_id)
    artists = get_user_favorite_artists(user_id)
    artist_ids = [artist['id'] for artist in artists]

    if not mood and not genres and not artist_ids:
        return jsonify({'error': 'User preference belum lengkap'}), 400

    # Buat vektor user (biner)
    all_moods = ["sad", "calm", "happy", "energetic"]
    all_genres = list({doc.to_dict().get("genre") for doc in db.collection("songs").stream() if doc.to_dict().get("genre")})
    all_artists = list({doc.to_dict().get("artist_id") for doc in db.collection("songs").stream() if doc.to_dict().get("artist_id")})

    def build_vector(mood_val, genre_val, artist_val):
        return np.array([
            int(mood_val == m) for m in all_moods
        ] + [
            int(genre_val == g) for g in all_genres
        ] + [
            int(artist_val == a) for a in all_artists
        ])

    user_vector = build_vector(mood, None, None)
    for g in genres:
        user_vector += build_vector(None, g, None)
    for a in artist_ids:
        user_vector += build_vector(None, None, a)

    # Normalisasi
    user_vector = np.clip(user_vector, 0, 1)

    recommended = []
    for doc in db.collection('songs').stream():
        song = doc.to_dict()
        song_id = doc.id
        song_vector = build_vector(
            song.get("mood"),
            song.get("genre"),
            song.get("artist_id")
        )

        # Hitung cosine similarity
        similarity = cosine_similarity([user_vector], [song_vector])[0][0]
        if similarity > 0:
            song['id'] = song_id
            song['similarity'] = round(float(similarity), 4)
            recommended.append(song)

    # Urutkan dan ambil hanya 5 teratas
    recommended.sort(key=lambda x: x['similarity'], reverse=True)
    recommended = recommended[:5]

    return jsonify({
        "recommended_songs": recommended,
        "criteria": {
            "mood": mood,
            "favorite_genres": genres,
            "favorite_artists": artist_ids
        }
    }), 200

