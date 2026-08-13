from app.config import db


# =========================
# USER
# =========================

def create_user(data):
    users_ref = db.collection('users')
    users_ref.document(data['email']).set(data)


def get_user_by_email(email):
    return db.collection('users').document(email).get()


# =========================
# USER MOOD
# =========================

def save_user_mood(user_id, mood):
    db.collection('moods').document(user_id).set({
        'mood': mood
    })


def get_user_mood(user_id):
    doc = db.collection('moods').document(user_id).get()

    if not doc.exists:
        return None

    return doc.to_dict().get('mood')


# =========================
# SONG PLAY HISTORY
# =========================

def log_user_song_play(user_id, song_id):
    db.collection('user_song_plays').add({
        'user_id': user_id,
        'song_id': song_id
    })


# =========================
# FAVORITE ARTIST
# =========================

def add_user_favorite_artist(user_id, artist_id):
    doc_ref = (
        db.collection('user_favorite_artists')
        .document(user_id)
    )

    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        artist_ids = data.get('artist_ids', [])

        if artist_id not in artist_ids:
            artist_ids.append(artist_id)

        doc_ref.set({
            'artist_ids': artist_ids
        })

    else:
        doc_ref.set({
            'artist_ids': [artist_id]
        })


def get_user_favorite_artists(user_id):
    doc = (
        db.collection('user_favorite_artists')
        .document(user_id)
        .get()
    )

    if not doc.exists:
        return []

    artist_ids = doc.to_dict().get('artist_ids', [])

    artists = []

    for artist_id in artist_ids:
        artist_doc = (
            db.collection('artists')
            .document(artist_id)
            .get()
        )

        if artist_doc.exists:
            artist = artist_doc.to_dict()
            artist['id'] = artist_doc.id
            artists.append(artist)

    return artists


# =========================
# FAVORITE GENRES
# =========================

def get_user_favorite_genres(user_id):
    played_songs = (
        db.collection('user_song_plays')
        .where('user_id', '==', user_id)
        .stream()
    )

    genre_count = {}

    for play in played_songs:
        song_id = play.to_dict().get('song_id')

        if not song_id:
            continue

        song_doc = (
            db.collection('songs')
            .document(song_id)
            .get()
        )

        if not song_doc.exists:
            continue

        genre = song_doc.to_dict().get('genre')

        if genre:
            genre_count[genre] = genre_count.get(genre, 0) + 1

    return sorted(
        genre_count,
        key=genre_count.get,
        reverse=True
    )


# =========================
# ARTIST
# =========================

def add_artist_data(data):
    return db.collection('artists').add(data)[1]


def get_all_artists():
    artists = []

    for doc in db.collection('artists').stream():
        artist = doc.to_dict()
        artist['id'] = doc.id
        artists.append(artist)

    return artists


def get_artist_by_id(artist_id):
    doc = (
        db.collection('artists')
        .document(artist_id)
        .get()
    )

    if not doc.exists:
        return None

    artist = doc.to_dict()
    artist['id'] = doc.id

    return artist


def get_songs_by_artist(artist_id):
    songs = []

    docs = (
        db.collection('songs')
        .where('artist_id', '==', artist_id)
        .stream()
    )

    for doc in docs:
        song = doc.to_dict()
        song['id'] = doc.id
        songs.append(song)

    return songs