import time
import requests

# Ganti ini dengan URL ngrok kamu
NGROK_URL = "https://57a4-2001-448a-5001-20d3-556c-7f5c-5957-8be4.ngrok-free.app"

# Endpoint sederhana (pastikan ada di aplikasimu)
ENDPOINT = "/playlists/list"

FULL_URL = NGROK_URL + ENDPOINT

def keep_alive():
    while True:
        try:
            print(f"[Ping] Sending GET to {FULL_URL}...")
            response = requests.get(FULL_URL)
            print(f"[Response] Status Code: {response.status_code}")
        except Exception as e:
            print(f"[Error] {e}")

        time.sleep(100)  # tunggu 5 menit (300 detik)

if __name__ == "__main__":
    keep_alive()
