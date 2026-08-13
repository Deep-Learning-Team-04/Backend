import os
import torch
import numpy as np
import librosa
from tensorflow.keras.models import load_model

from app.services.Cnn14 import Cnn14


PANNs_PATH = "app/services/Cnn14_16k_mAP=0.438.pth"
KERAS_PATH = "app/services/model.h5"
AUDIO_PATH = os.path.join(
    os.path.dirname(__file__),
    "test-audio",
    "song1.wav"
)


def safe_load_panns(model, ckpt_path, device):
    ckpt = torch.load(
        ckpt_path,
        map_location=device,
        weights_only=False
    )

    src_state = ckpt["model"]
    dst_state = model.state_dict()

    filtered = {
        k: v
        for k, v in src_state.items()
        if k in dst_state and v.shape == dst_state[k].shape
    }

    dst_state.update(filtered)
    model.load_state_dict(dst_state, strict=False)

    print(
        f"PANNs loaded: "
        f"{len(filtered)}/{len(src_state)} layers"
    )

    return model


def extract_embedding(audio_path, model, device):

    y, sr = librosa.load(
        audio_path,
        sr=16000,
        mono=True
    )

    win = int(5 * sr)
    hop = int(0.5 * sr)

    if len(y) < win:
        raise ValueError(
            "Audio terlalu pendek. Minimal 5 detik."
        )

    embeddings = []

    for start in range(
        0,
        len(y) - win + 1,
        hop
    ):

        segment = y[start:start + win]

        x = (
            torch.from_numpy(segment)
            .float()
            .to(device)
            .unsqueeze(0)
        )

        with torch.no_grad():
            result = model(x, None)

        embedding = (
            result["embedding"]
            .cpu()
            .numpy()
            .squeeze()
        )

        embedding = np.pad(
            embedding,
            (0, max(0, 2048 - embedding.shape[0]))
        )[:2048]

        embeddings.append(embedding)

    embedding = np.mean(
        embeddings,
        axis=0,
        dtype=np.float32
    )

    return embedding.reshape(1, -1)


def classify_mood(valence, arousal):

    if valence >= 0.5 and arousal >= 0.5:
        return "Happy"

    if valence >= 0.5 and arousal < 0.5:
        return "Relax"

    if valence < 0.5 and arousal >= 0.5:
        return "Tense"

    return "Sad"


# --------------------------------------------------
# MAIN
# --------------------------------------------------

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)

print("\n[1] Loading PANNs...")

panns_model = Cnn14(
    sample_rate=16000,
    window_size=512,
    hop_size=320,
    mel_bins=64,
    fmin=50,
    fmax=8000,
    classes_num=527
).to(device)

safe_load_panns(
    panns_model,
    PANNs_PATH,
    device
)

panns_model.eval()

print("PANNs ready.")


print("\n[2] Loading model.h5...")

keras_model = load_model(KERAS_PATH)

print("model.h5 ready.")
print("Input:", keras_model.input_shape)
print("Output:", keras_model.output_shape)


print("\n[3] Extracting audio embedding...")

features = extract_embedding(
    AUDIO_PATH,
    panns_model,
    device
)

print("Embedding shape:", features.shape)


print("\n[4] Predicting valence/arousal...")

valence, arousal = keras_model.predict(
    features,
    verbose=0
)[0]

print("Valence :", float(valence))
print("Arousal :", float(arousal))


print("\n[5] Classifying mood...")

mood = classify_mood(
    float(valence),
    float(arousal)
)

print("Mood:", mood)

print("\nAI PIPELINE SUCCESS!")