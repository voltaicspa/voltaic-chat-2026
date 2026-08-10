from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json
import os

app = Flask(__name__)

# La API key la envía cada usuario desde el frontend (no se guarda en el servidor)

CONFIG_FILE = "config.json"
messages = []

# ============================================
# FUNCIONES DE CONFIGURACIÓN
# ============================================
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "system_prompt": "Responde siempre en español. Sé claro y directo.",
            "voice_id": "es-ES-ElviraNeural",
            "temperature": 0.7,
            "model": "deepseek-v4-pro"
        }

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ============================================
# RUTAS
# ============================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/camila")
def camila():
    """Pagina limpia con SOLO el chat de voz de Camila (para el iPhone)."""
    return render_template("camila.html")

@app.route("/test")
def test():
    return "✅ Servidor funcionando!"

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def update_config():
    new_config = request.json
    save_config(new_config)
    return jsonify({"status": "success"})

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        mensaje = data.get("message", "")
        api_key = data.get("api_key", "")
        if not mensaje:
            return jsonify({"error": "Mensaje vacío"})
        if not api_key or not api_key.startswith("sk-"):
            return jsonify({"error": "API Key de DeepSeek inválida. Consigue una en platform.deepseek.com"})
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        config = load_config()
        mensajes_para_enviar = []
        mensajes_para_enviar.append({
            "role": "system",
            "content": config.get("system_prompt", "Responde siempre en español.")
        })
        for msg in messages:
            mensajes_para_enviar.append(msg)
        mensajes_para_enviar.append({"role": "user", "content": mensaje})
        messages.append({"role": "user", "content": mensaje})
        response = client.chat.completions.create(
            model=config.get("model", "deepseek-v4-pro"),
            messages=mensajes_para_enviar,
            temperature=config.get("temperature", 0.7),
            max_tokens=2000
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/exportar")
def exportar():
    if not messages:
        return "No hay mensajes", 404
    text = "="*50 + "\nVOLTAIC CHAT\n" + "="*50 + "\n\n"
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "DEEPSEEK"
        text += f"{role}: {msg['content']}\n\n"
    return text, 200, {"Content-Type": "text/plain", "Content-Disposition": "attachment; filename=chat.txt"}

if __name__ == "__main__":
    print("")
    print("⬡ VOLTAIC CHAT")
    print("🌐 Chat: http://localhost:8599")
    print("📊 Dashboard: http://localhost:8599/dashboard")
    print("🧪 Test: http://localhost:8599/test")
    print("")
    app.run(host="127.0.0.1", port=8599, debug=True)