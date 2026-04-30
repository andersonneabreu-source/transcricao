import os
import tempfile
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

META_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")

HEADERS_OPTIONS = [
    # Tenta sem autenticação (user-agent de browser)
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    },
    # Tenta com token se estiver configurado
    {
        "Authorization": f"Bearer {META_TOKEN}",
        "User-Agent": "Mozilla/5.0",
    } if META_TOKEN else None,
]


def baixar_audio(url):
    """Tenta baixar o áudio com diferentes estratégias de autenticação."""
    for headers in HEADERS_OPTIONS:
        if headers is None:
            continue
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200 and len(response.content) > 0:
                return response.content, None
        except Exception:
            continue

    return None, "Não foi possível baixar o áudio. Verifique a URL ou configure o META_ACCESS_TOKEN."


@app.route("/transcrever", methods=["POST"])
def transcrever():
    data = request.get_json()

    if not data or "audio_url" not in data:
        return jsonify({"error": "audio_url é obrigatório"}), 400

    audio_url = data["audio_url"]

    # Baixar o áudio
    conteudo, erro = baixar_audio(audio_url)
    if erro:
        return jsonify({"error": erro}), 400

    # Detectar extensão pela URL ou usar .mp4 como padrão
    extensao = ".mp4"
    for ext in [".ogg", ".mp3", ".wav", ".m4a", ".webm", ".aac"]:
        if ext in audio_url.lower():
            extensao = ext
            break

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extensao, delete=False) as tmp:
            tmp.write(conteudo)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

        os.unlink(tmp_path)

        return jsonify({
            "transcricao": transcription.text,
            "status": "ok"
        })

    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mensagem": "Servidor de transcrição rodando!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
