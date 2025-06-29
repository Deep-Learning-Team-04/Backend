from flask import Blueprint, request, jsonify
from google.cloud import firestore
from datetime import datetime

playlist_bp = Blueprint('playlist', __name__)
db = firestore.Client()

@playlist_bp.route('/create', methods=['POST'])
def create_playlist():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')

    if not name:
        return jsonify({'error': 'Nama playlist wajib diisi'}), 400

    playlist_ref = db.collection('playlists').add({
        'name': name,
        'description': description,
        'created_at': datetime.utcnow()
    })

    return jsonify({'message': 'Playlist berhasil dibuat', 'playlist_id': playlist_ref[1].id}), 201

#  Tambahkan Lagu ke Playlist
@playlist_bp.route('/<playlist_id>/add_song', methods=['POST'])
def add_song_to_playlist(playlist_id):
    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({'error': 'song_id wajib diisi'}), 400

    # Validasi
    if not db.collection('playlists').document(playlist_id).get().exists:
        return jsonify({'error': 'Playlist tidak ditemukan'}), 404
    if not db.collection('songs').document(song_id).get().exists:
        return jsonify({'error': 'Lagu tidak ditemukan'}), 404

    # Tambahkan entry
    db.collection('playlist_songs').add({
        'playlist_id': playlist_id,
        'song_id': song_id,
        'added_at': datetime.utcnow()
    })

    return jsonify({'message': 'Lagu berhasil ditambahkan ke playlist'}), 200

@playlist_bp.route('/list', methods=['GET'])
def list_playlists():
    playlists = []
    playlist_docs = db.collection('playlists').stream()

    for doc in playlist_docs:
        playlist_data = doc.to_dict()
        playlist_id = doc.id

        # Ambil lagu dalam playlist
        links = db.collection('playlist_songs').where('playlist_id', '==', playlist_id).stream()
        song_ids = [link.to_dict()['song_id'] for link in links]

        # Ambil detail lagu dan artis
        songs_detail = []
        for song_id in song_ids:
            song_doc = db.collection('songs').document(song_id).get()
            if song_doc.exists:
                song = song_doc.to_dict()
                artist = db.collection('artists').document(song['artist_id']).get()
                songs_detail.append({
                    'song_name': song['song_name'],
                    'artist_name': artist.to_dict().get('name') if artist.exists else 'Unknown',
                    'genre': song.get('genre'),
                    'mood': song.get('mood')
                })

        playlists.append({
            'id': playlist_id,
            'name': playlist_data['name'],
            'description': playlist_data.get('description', ''),
            'song_count': len(songs_detail),
            'songs': songs_detail
        })

    return jsonify(playlists), 200
