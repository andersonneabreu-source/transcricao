import os
import tempfile
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

META_TOKEN = os.environ.get("META_ACCESS_TOKEN")

@app.route("/transcrever", methods=["POST"])
def transcrever():
    data = request.get_json()

    if not data or "audio_url" not in data:
        return jsonify({"error": "audio_url é obrigatório"}), 400

    audio_url = data["audio_url"]

    try:
        # 1. Baixar o áudio da Meta com autenticação
        headers = {"Authorization": f"Bearer {META_TOKEN}"}
        response = requests.get(audio_url, headers=headers, timeout=30)

        if response.status_code != 200:
            return jsonify({"error": f"Erro ao baixar áudio: {response.status_code}"}), 400

        # 2. Salvar temporariamente e transcrever com Whisper
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

        os.unlink(tmp_path)

        return jsonify({"transcricao": transcription.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
