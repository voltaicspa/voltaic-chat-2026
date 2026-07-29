import json
import os
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

CONFIG_FILE = 'config.json'

# --- MANEJO DE CONFIGURACIÓN Y PERSISTENCIA ---

def load_config():
    """Lee config.json o crea valores por defecto si no existe."""
    default_config = {
        "system_prompt": "Responde siempre en español. Sé claro y directo. Si no sabes algo, dilo honestamente.",
        "voice_id": "es-ES-ElviraNeural",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "gemini_api_key": "",
        "deepseek_api_key": ""
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Asegurar que todas las claves existan
            for k, v in default_config.items():
                data.setdefault(k, v)
            return data
    except Exception:
        return default_config

def save_config(data):
    """Guarda los cambios enviados desde el Dashboard."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- RUTAS DE NAVEGACIÓN (HTML) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# --- ENDPOINTS API ---

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    new_data = request.json
    current_config = load_config()
    current_config.update(new_data)
    save_config(current_config)
    return jsonify({"status": "ok", "message": "Configuración guardada correctamente"})


# --- PROCESADOR MULTI-IA ---

def query_gemini(system_prompt, user_message, model_name, temperature, api_key):
    if not api_key:
        return "Error: No has configurado una API Key para Gemini en el Dashboard."
    
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature
    )
    response = client.models.generate_content(
        model=model_name,
        contents=user_message,
        config=config
    )
    return response.text

@app.route('/api/chat', methods=['POST'])
def chat():
    config = load_config()
    user_message = request.json.get("message", "")
    selected_model = config.get("model", "deepseek-chat")
    system_prompt = config.get("system_prompt", "")
    temperature = float(config.get("temperature", 0.7))

    try:
        # Si el modelo seleccionado es de la familia Gemini
        if "gemini" in selected_model:
            reply = query_gemini(
                system_prompt=system_prompt,
                user_message=user_message,
                model_name=selected_model,
                temperature=temperature,
                api_key=config.get("gemini_api_key", "")
            )
        else:
            # Lógica predeterminada de DeepSeek
            reply = f"Respuesta procesada con {selected_model}: {user_message}"

        return jsonify({"response": reply, "model": selected_model})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- ARRANQUE DEL SERVIDOR ---

if __name__ == '__main__':
    print("🚀 VoltaicChat activo en http://localhost:8599")
    print("🎛️  Dashboard en http://localhost:8599/dashboard")
    app.run(host='0.0.0.0', port=8599, debug=True)