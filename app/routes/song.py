import os
import tempfile
import librosa
import numpy as np
import torch


from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from google.cloud import storage, firestore
from tensorflow.keras.models import load_model


song_bp = Blueprint("song", __name__)


GCS_BUCKET_NAME = "model-deep-learning"


BASE_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVICE_DIR  = os.path.join(BASE_DIR, "app", "services")
PANNs_PATH   = os.path.join(SERVICE_DIR, "Cnn14_16k_mAP=0.438.pth")
KERAS_PATH   = os.path.join(SERVICE_DIR, "model.h5")


db             = firestore.Client()
storage_client = storage.Client()


from app.services.Cnn14 import Cnn14


def safe_load_panns(model: torch.nn.Module, ckpt_path: str, device: torch.device):
   """
   Memuat checkpoint PANNs dan MENGABAIKAN layer yang shape-nya tidak cocok
   (contoh: bn0.* dari fork lain).
   """
   ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
   src_state = ckpt["model"] if isinstance(ckpt, dict) and "model" in ckpt else ckpt
   dst_state = model.state_dict()


   filtered = {k: v for k, v in src_state.items() if k in dst_state and v.shape == dst_state[k].shape}
   dst_state.update(filtered)
   model.load_state_dict(dst_state, strict=False)


   print(f"[PANNs] Loaded {len(filtered)}/{len(src_state)} compatible layers (ignored the rest).")
   return model




# ------------------------------------------------------------------ #
#  Load model (hanya sekali di cold-start)                           #
# ------------------------------------------------------------------ #
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


panns_model = Cnn14(
   sample_rate=16000,
   window_size=512,
   hop_size=320,
   mel_bins=64,
   fmin=50,
   fmax=8000,          #  ♦ harus sama dgn training
   classes_num=527,
).to(device)


safe_load_panns(panns_model, PANNs_PATH, device)
panns_model.eval()


keras_model = load_model(KERAS_PATH)




# ------------------------------------------------------------------ #
#  Helper fungsi                                                     #
# ------------------------------------------------------------------ #
def extract_panns_embedding(audio_path: str) -> np.ndarray:


   y, sr = librosa.load(audio_path, sr=16000, mono=True)
   win   = int(5 * sr)
   hop   = int(0.5 * sr)


   if len(y) < win:
       raise ValueError("Audio terlalu pendek (< 5 detik)")


   emb_list = []
   for start in range(0, len(y) - win + 1, hop):
       seg = y[start:start + win]
       x   = torch.from_numpy(seg).float().to(device).unsqueeze(0)


       with torch.no_grad():
           emb = panns_model(x, None)["embedding"].cpu().numpy().squeeze()


       emb = np.pad(emb, (0, max(0, 2048 - emb.shape[0])))[:2048]
       emb_list.append(emb)


   return np.mean(emb_list, axis=0, dtype=np.float32).reshape(1, -1)




def classify_mood(val: float, aro: float) -> str:
   if val >= 0.5 and aro >= 0.5:
       return "Happy"
   if val >= 0.5 and aro < 0.5:
       return "Relax"
   if val < 0.5 and aro >= 0.5:
       return "Tense"
   return "Sad"




# ------------------------------------------------------------------ #
#  Routes                                                            #
# ------------------------------------------------------------------ #
@song_bp.route("/upload", methods=["POST"])
def upload_song():
   if "file" not in request.files:
       return jsonify(error="File audio tidak ditemukan"), 400


   file       = request.files["file"]
   song_name  = request.form.get("song_name")
   genre      = request.form.get("genre")
   artist_id  = request.form.get("artist_id")


   if not all([song_name, genre, artist_id]):
       return jsonify(error="song_name, genre, dan artist_id wajib diisi"), 400


   if not db.collection("artists").document(artist_id).get().exists:
       return jsonify(error="Artist dengan ID tersebut tidak ditemukan"), 404


   # simpan sementara
   tmp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
   file.save(tmp_path)


   # Upload ke GCS
   bucket = storage_client.bucket(GCS_BUCKET_NAME)
   blob   = bucket.blob(f"songs/{os.path.basename(tmp_path)}")
   blob.upload_from_filename(tmp_path)
   public_url = blob.public_url


   # Prediksi
   try:
       features          = extract_panns_embedding(tmp_path)
       valence, arousal  = keras_model.predict(features, verbose=0)[0]
       print(f"[DEBUG] {song_name}: val={valence:.3f}, aro={arousal:.3f}")
       mood              = classify_mood(float(valence), float(arousal))
   except Exception as e:
       return jsonify(error=f"Gagal klasifikasi: {e}"), 500
   finally:
       if os.path.exists(tmp_path):
           os.remove(tmp_path)


   # Simpan metadata
   song_ref = db.collection("songs").add({
       "song_name": song_name,
       "genre"    : genre,
       "artist_id": artist_id,
       "mood"     : mood,
       "file_url" : public_url,
   })[1]


   return jsonify(
       message   ="Lagu berhasil di-upload & diproses",
       song_id   =song_ref.id,
       song_name =song_name,
       genre     =genre,
       mood      =mood,
       artist_id =artist_id,
   ), 201




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



