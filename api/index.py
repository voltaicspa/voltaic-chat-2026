import os
import sys

# En Vercel el directorio del entrypoint NO queda en sys.path, asi que los
# `import simli_live` / `vidu_live` / `paneles` fallan con "No module named".
# En local no se nota porque se ejecuta parado dentro de api/. Sin esto, la
# pagina /catalina/cara carga pero sus rutas de API devuelven 404.
_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

import requests
from flask import Flask, render_template, render_template_string, request, jsonify

import os as _os
_BASE = _os.path.dirname(_os.path.abspath(__file__))
_TEMPLATES = _os.path.join(_os.path.dirname(_BASE), "templates")
if not _os.path.isdir(_TEMPLATES):
    _TEMPLATES = _os.path.join(_BASE, "templates")
app = Flask(__name__, template_folder=_TEMPLATES)
app.secret_key = os.environ.get("SECRET_KEY", "voltaic-chat-secret-key-2026")

@app.after_request
def _no_cache(resp):
    """Evita que los navegadores guarden en caché versiones viejas del dashboard."""
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_CONVAI_URL = "https://api.elevenlabs.io/v1/convai"
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# ============================================================
#  CANDADO DE LOS ENDPOINTS QUE USAN NUESTRA CLAVE
#
#  El chat (/api/chat) usa la clave que manda CADA CLIENTE, y por eso puede
#  quedar abierto. Pero /api/voices y /api/copilots usan la clave de
#  ElevenLabs de VoltaicTech, y estaban SIN NINGUNA autenticacion: cualquiera
#  en internet podia mandar un PATCH y reescribirle el prompt, el primer
#  mensaje y la voz al asistente que hablan con los clientes. Y el id del
#  agente estaba publicado en el HTML de la propia pagina, asi que estaba la
#  cerradura y la llave juntas.
#
#  Ahora exigen la cabecera X-Voltaic-Token. Si el token no esta configurado
#  en el servidor, se NIEGA el acceso: cerrar por defecto. Dejarlo abierto
#  "mientras tanto" es exactamente como llegamos hasta aca.
# ============================================================
ADMIN_API_TOKEN = os.environ.get("ADMIN_API_TOKEN", "").strip()


def solo_admin(fn):
    """Exige el token de administrador. Sin token configurado, no se pasa."""
    from functools import wraps

    @wraps(fn)
    def envoltorio(*args, **kwargs):
        if not ADMIN_API_TOKEN:
            return jsonify({
                "success": False,
                "error": "Este panel no está habilitado: falta configurar "
                         "ADMIN_API_TOKEN en el servidor."
            }), 503
        enviado = (request.headers.get("X-Voltaic-Token", "")
                   or request.args.get("token", "")).strip()
        # Comparacion en tiempo constante: evita que se pueda adivinar el token
        # midiendo cuanto tarda en responder.
        import hmac
        if not hmac.compare_digest(enviado, ADMIN_API_TOKEN):
            return jsonify({"success": False, "error": "No autorizado."}), 401
        return fn(*args, **kwargs)

    return envoltorio

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoltaicChat - Dashboard Avanzado</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex justify-between items-center border-b border-slate-800 pb-4">
            <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-blue-500 inline-block animate-pulse"></span> Dashboard VoltaicChat
            </h1>
            <div class="flex items-center gap-3">
                <span id="statusBadge" class="text-xs bg-slate-900 text-slate-400 px-3 py-1 rounded-full border border-slate-800">Sistema Conectado</span>
            </div>
        </header>

        <!-- Grid Principal de Tarjetas -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <!-- TARJETA 1: REGLAS DEL SISTEMA -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">📄 REGLAS DEL SISTEMA</h2>
                </div>
                <p class="text-xs text-slate-400">Instrucciones que el modelo debe seguir (Prompt del Sistema)</p>
                <div>
                    <textarea id="promptInput" rows="5" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-purple-500 transition resize-none"></textarea>
                </div>
                <div>
                    <label class="block text-xs font-medium text-slate-400 mb-1">Agent ID de ElevenLabs</label>
                    <input type="text" id="agentIdInput" value="agent_4101krkj2n1jf04bxfhpbjmt3qzf" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500">
                </div>
                <button onclick="saveAgentPrompt()" class="w-full bg-purple-600 hover:bg-purple-500 text-white font-medium py-2 rounded-lg transition text-sm shadow-lg shadow-purple-900/20">Guardar Reglas</button>
            </div>

            <!-- TARJETA 2: ELEVENLABS ENGINE -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">🎙️ ELEVENLABS ENGINE (AUDIO PREMIUM)</h2>
                </div>
                <div>
                    <label class="block text-xs font-medium text-slate-400 mb-1">ElevenLabs API Key</label>
                    <input type="password" id="apiKeyInput" placeholder="Configurada en Vercel (Segura)" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500" disabled>
                </div>
                <div>
                    <label class="block text-xs font-medium text-slate-400 mb-1">Voice ID (Voz clonada o preferida)</label>
                    <input type="text" id="voiceIdInput" placeholder="Ej: 21m00Tcm4TlvDq8ikWAM" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500">
                </div>
                <div>
                    <label class="block text-xs font-medium text-slate-400 mb-1">Primer Mensaje del Agente</label>
                    <input type="text" id="firstMessageInput" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500">
                </div>
                <button onclick="saveElevenLabsConfig()" class="w-full bg-purple-600 hover:bg-purple-500 text-white font-medium py-2 rounded-lg transition text-sm shadow-lg shadow-purple-900/20">Guardar ElevenLabs</button>
            </div>

            <!-- TARJETA 3: MODELO Y TEMPERATURA -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl flex flex-col justify-between">
                <div class="space-y-4">
                    <h2 class="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">⚙️ MODELO Y CONVERSACIÓN</h2>
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Modelo activo</label>
                        <select class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500">
                            <option>ElevenLabs Conversational AI v1</option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <div class="flex justify-between text-xs text-slate-400">
                            <span>Estabilidad / Coherencia</span>
                            <span id="tempVal">0.7</span>
                        </div>
                        <input type="range" min="0" max="1" step="0.1" value="0.7" class="w-full accent-purple-500 cursor-pointer" oninput="document.getElementById('tempVal').innerText=this.value">
                    </div>
                </div>
                <button onclick="loadAgentConfig()" class="w-full bg-purple-600 hover:bg-purple-500 text-white font-medium py-2 rounded-lg transition text-sm shadow-lg shadow-purple-900/20">Cargar desde Nube</button>
            </div>

        </div>

        <!-- SECCIÓN INFERIOR: CHAT DE VOZ Y ESTADÍSTICAS -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <!-- ESTADÍSTICAS -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl flex flex-col justify-center">
                <h2 class="text-sm font-semibold text-slate-200 uppercase tracking-wider">📊 ESTADÍSTICAS</h2>
                <div class="grid grid-cols-2 gap-4 text-center py-2">
                    <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                        <span class="block text-2xl font-bold text-purple-400" id="msgCount">--</span>
                        <span class="text-xs text-slate-400">Estado API</span>
                    </div>
                    <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                        <span class="block text-2xl font-bold text-blue-400">100%</span>
                        <span class="text-xs text-slate-400">Operativo</span>
                    </div>
                </div>
                <button onclick="loadAgentConfig()" class="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium py-2 rounded-lg transition text-xs border border-slate-700">Actualizar Estado</button>
            </div>

            <!-- WIDGET DE VOZ INTEGRADO -->
            <div class="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl flex flex-col items-center justify-center text-center">
                <h2 class="text-sm font-semibold text-slate-200 uppercase tracking-wider">🎧 CHAT DE VOZ INTERACTIVO (CATALINA)</h2>
                <p class="text-xs text-slate-400">Prueba la llamada de voz directamente con tu asistente configurado en ElevenLabs:</p>
                <div class="py-2">
                    <elevenlabs-convai agent-id="agent_4101krkj2n1jf04bxfhpbjmt3qzf"></elevenlabs-convai>
                    <script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>
                </div>
            </div>

        </div>

        <div id="toast" class="fixed bottom-5 right-5 bg-slate-900 border border-slate-700 text-slate-200 px-4 py-3 rounded-xl shadow-2xl text-xs hidden transition-all duration-300"></div>
    </div>

    <script>
        window.onload = function() {
            loadAgentConfig();
        };

        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.innerText = message;
            toast.className = `fixed bottom-5 right-5 px-4 py-3 rounded-xl shadow-2xl text-xs transition-all duration-300 border ${isError ? 'bg-red-950 border-red-800 text-red-200' : 'bg-emerald-950 border-emerald-800 text-emerald-200'}`;
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 3500);
        }


        // Token de administrador. Se pide UNA vez y queda solo en la sesion del
        // navegador (sessionStorage): al cerrar la pestana se borra. No se
        // guarda en el codigo ni en el disco.
        function tokenAdmin() {
            let t = sessionStorage.getItem('voltaic_token');
            if (!t) {
                t = prompt('Token de administrador de VoltaicChat:');
                if (t) sessionStorage.setItem('voltaic_token', t.trim());
            }
            return (t || '').trim();
        }

        function cabecerasAdmin(extra) {
            return Object.assign({'X-Voltaic-Token': tokenAdmin()}, extra || {});
        }
        async function loadAgentConfig() {
            const agentId = document.getElementById('agentIdInput').value.trim();
            if (!agentId) return;
            try {
                const res = await fetch(`/api/copilots/${agentId}`, {headers: cabecerasAdmin()});
                const data = await res.json();
                if (data.success) {
                    document.getElementById('promptInput').value = data.data.prompt;
                    document.getElementById('firstMessageInput').value = data.data.first_message;
                    document.getElementById('voiceIdInput').value = data.data.voice_id;
                    document.getElementById('msgCount').innerText = 'OK';
                    showToast('¡Configuración sincronizada desde ElevenLabs!');
                } else {
                    showToast(data.error, true);
                    document.getElementById('msgCount').innerText = 'ERR';
                }
            } catch (e) {
                showToast('Error de conexión con el servidor', true);
                document.getElementById('msgCount').innerText = 'ERR';
            }
        }

        async function saveAgentPrompt() {
            const agentId = document.getElementById('agentIdInput').value.trim();
            const prompt = document.getElementById('promptInput').value;
            const first_message = document.getElementById('firstMessageInput').value;
            const voice_id = document.getElementById('voiceIdInput').value;

            try {
                const res = await fetch(`/api/copilots/${agentId}`, {
                    method: 'PATCH',
                    headers: cabecerasAdmin({'Content-Type': 'application/json'}),
                    body: JSON.stringify({ prompt, first_message, voice_id })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('¡Reglas guardadas con éxito en ElevenLabs!');
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast('Error al guardar las reglas', true);
            }
        }

        async function saveElevenLabsConfig() {
            saveAgentPrompt();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/voices', methods=['GET'])
@solo_admin
def get_voices():
    if not ELEVENLABS_API_KEY:
        return jsonify({"success": False, "error": "ELEVENLABS_API_KEY no configurada"}), 400
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    try:
        response = requests.get(f"{ELEVENLABS_BASE_URL}/voices", headers=headers)
        if response.status_code == 200:
            voices = response.json().get("voices", [])
            lista_voces = [{"voice_id": v["voice_id"], "name": v["name"]} for v in voices]
            return jsonify({"success": True, "voices": lista_voces})
        else:
            return jsonify({"success": False, "error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/copilots/<agent_id>', methods=['GET'])
@solo_admin
def get_copilot_config(agent_id):
    if not ELEVENLABS_API_KEY:
        return jsonify({"success": False, "error": "ELEVENLABS_API_KEY no configurada"}), 400
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    try:
        response = requests.get(f"{ELEVENLABS_CONVAI_URL}/agents/{agent_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            conv_config = data.get("conversation_config", {})
            agent_config = conv_config.get("agent", {})
            tts_config = conv_config.get("tts", {})
            config = {
                "id": agent_id,
                "name": data.get("name", "Agente ElevenLabs"),
                "prompt": agent_config.get("prompt", {}).get("prompt", ""),
                "first_message": agent_config.get("first_message", ""),
                "voice_id": tts_config.get("voice_id", ""),
                "stability": tts_config.get("stability", 0.5),
                "similarity_boost": tts_config.get("similarity_boost", 0.75),
                "style": tts_config.get("style", 0),
                "use_speaker_boost": tts_config.get("use_speaker_boost", True)
            }
            return jsonify({"success": True, "data": config})
        else:
            return jsonify({"success": False, "error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/copilots/<agent_id>', methods=['PATCH'])
@solo_admin
def update_copilot_config(agent_id):
    if not ELEVENLABS_API_KEY:
        return jsonify({"success": False, "error": "ELEVENLABS_API_KEY no configurada"}), 400
    payload = request.get_json() or {}
    nuevo_prompt = payload.get("prompt")
    nuevo_first_message = payload.get("first_message")
    nuevo_voice_id = payload.get("voice_id")
    stability = payload.get("stability")
    similarity_boost = payload.get("similarity_boost")
    style = payload.get("style")
    use_speaker_boost = payload.get("use_speaker_boost")
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    tts = {}
    if nuevo_voice_id:
        tts["voice_id"] = nuevo_voice_id
    if stability is not None:
        tts["stability"] = float(stability)
    if similarity_boost is not None:
        tts["similarity_boost"] = float(similarity_boost)
    if style is not None:
        tts["style"] = float(style)
    if use_speaker_boost is not None:
        tts["use_speaker_boost"] = bool(use_speaker_boost)
    update_data = {
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": nuevo_prompt},
                "first_message": nuevo_first_message
            }
        }
    }
    if tts:
        update_data["conversation_config"]["tts"] = tts
    try:
        response = requests.patch(f"{ELEVENLABS_CONVAI_URL}/agents/{agent_id}", json=update_data, headers=headers)
        if response.status_code == 200:
            return jsonify({"success": True, "message": "¡Configuración actualizada con éxito!"})
        else:
            return jsonify({"success": False, "error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/chat')
def chat_page():
    return render_template('index.html')

# ============================================================
#  CANDADO DE LA PAGINA DE CAMILA
#
#  Camila es el asistente PERSONAL de Cristian, no un producto publico.
#  Se protege del lado del SERVIDOR con autenticacion HTTP basica: una clave
#  en JavaScript no sirve de nada, cualquiera la lee con "ver codigo fuente".
#
#  Safari en el iPhone muestra su ventana nativa y guarda la clave en el
#  Llavero, asi que se escribe una sola vez.
#
#  Cerrado por defecto: si CAMILA_PASS no esta configurada en el servidor,
#  la pagina NO se sirve. Preferimos que quede inaccesible antes que abierta.
# ============================================================
CAMILA_USER = os.environ.get("CAMILA_USER", "cristian").strip()
CAMILA_PASS = os.environ.get("CAMILA_PASS", "").strip()


def _pedir_clave_camila():
    from flask import Response
    return Response(
        "Acceso restringido.", 401,
        {"WWW-Authenticate": 'Basic realm="Camila - Asistente de Cristian"'},
    )


def _camila_autorizado():
    """Devuelve None si puede pasar, o la respuesta a devolver si no.

    Cerrado por defecto: sin CAMILA_PASS configurada, no se sirve la pagina.
    """
    if not CAMILA_PASS:
        return jsonify({
            "error": "Pagina cerrada: falta configurar CAMILA_PASS en el "
                     "servidor (Vercel > Settings > Environment Variables)."
        }), 503

    import hmac
    auth = request.authorization
    if not auth:
        return _pedir_clave_camila()

    # Comparacion en tiempo constante: evita adivinar la clave midiendo demoras.
    usuario_ok = hmac.compare_digest(auth.username or "", CAMILA_USER)
    clave_ok = hmac.compare_digest(auth.password or "", CAMILA_PASS)
    if not (usuario_ok and clave_ok):
        return _pedir_clave_camila()

    return None


@app.route('/camila')
def camila_page():
    """Pagina limpia con SOLO el chat de voz de Camila (para el iPhone).

    No carga el panel ni pide el token de administrador: el widget de
    ElevenLabs se conecta directo con su agent-id publico, sin API key en la
    pagina. El acceso se protege con clave (ver bloque de arriba).
    """
    no_pasa = _camila_autorizado()
    return no_pasa if no_pasa else render_template('camila.html')


@app.route('/camila/config')
def camila_config_page():
    """Panel dedicado a configurar SOLO a Camila: voz, saludo, personalidad
    y modulacion. Separado de la pagina donde se le habla.

    Doble candado: la clave de Camila para entrar a la pagina, y ademas el
    ADMIN_API_TOKEN para que sus llamadas a la API sean aceptadas.
    """
    no_pasa = _camila_autorizado()
    return no_pasa if no_pasa else render_template('camila_config.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json() or {}
    msg = data.get('message', '')
    api_key = data.get('api_key', '')
    if not msg:
        return jsonify({"error": "Mensaje vacío"})
    if not api_key or not api_key.startswith('sk-'):
        api_key = _SHARED_DEEPSEEK
        if not api_key:
            return jsonify({"error": "API Key de DeepSeek requerida. Consigue una gratis en platform.deepseek.com"})
    try:
        r = requests.post('https://api.deepseek.com/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={'model': 'deepseek-chat', 'messages': [{'role':'system','content':'Responde siempre en español. Sé claro y directo.'},{'role':'user','content':msg}]},
            timeout=30)
        if r.status_code == 200:
            text = r.json()['choices'][0]['message']['content']
            return jsonify({"response": text})
        return jsonify({"error": f"DeepSeek: {r.text[:200]}"}), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_web():
    """Endpoint de busqueda web para Catalina (ElevenLabs webhook)."""
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "query vacio"}), 400
    try:
        r = requests.get('https://html.duckduckgo.com/html/',
            params={'q': query},
            headers={'User-Agent': 'VoltaicChat/1.0'},
            timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        resultados = []
        for res in soup.select('.result')[:5]:
            title = res.select_one('.result__title')
            snippet = res.select_one('.result__snippet')
            link = res.select_one('.result__url')
            if title:
                resultados.append({
                    'titulo': title.get_text(strip=True),
                    'descripcion': snippet.get_text(strip=True) if snippet else '',
                    'url': link.get_text(strip=True) if link else ''
                })
        if not resultados:
            return jsonify({"respuesta": f"No encontre resultados para: {query}"})
        texto = '\n'.join([f"- {r['titulo']}: {r['descripcion'][:200]}" for r in resultados])
        return jsonify({"respuesta": texto})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ USUARIOS ============
import json as _json
_USERS_FILE = _os.path.join(_os.path.dirname(_BASE), "users.json")
_SHARED_DEEPSEEK = os.environ.get("DEEPSEEK_API_KEY", "")

# SIN valor por defecto. Antes decia os.environ.get("ADMIN_KEY", "voltaic2026"):
# esa clave estaba escrita en el codigo, ADMIN_KEY no esta configurada en
# Vercel, y por eso /api/usuarios?key=voltaic2026 respondia 200 a cualquiera
# en internet con la lista de usuarios. Ahora: si no hay clave, no se abre.
_ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()

def _cargar_usuarios():
    try:
        with open(_USERS_FILE, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

@app.route("/api/user/<code>")
def api_usuario(code):
    """Devuelve SOLO lo que el frontend necesita para mostrar u ocultar el
    panel de ElevenLabs. Nada sensible.

    Antes devolvia tambien 'deepseek_key'. Este endpoint no pide autenticacion
    y los codigos son palabras adivinables (cristian, demo, abuelos...), asi
    que cualquiera podia pedir la clave ajena. Ningun cliente la usaba:
    dashboard.html:309 solo lee 'has_elevenlabs'. Se saco.
    """
    usuarios = _cargar_usuarios()
    u = usuarios.get(code)
    if not u or not u.get("active"):
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({
        "name": u["name"],
        "has_elevenlabs": u.get("has_elevenlabs", False),
    })

@app.route("/api/usuarios")
def api_usuarios():
    """Admin: lista los usuarios. Cerrado por defecto."""
    if not _ADMIN_KEY:
        return jsonify({
            "error": "Endpoint deshabilitado: falta configurar ADMIN_KEY en "
                     "el servidor."
        }), 503

    import hmac
    # Se acepta por cabecera (preferido) o por query, por compatibilidad.
    # Comparacion en tiempo constante: no se puede adivinar midiendo demoras.
    enviado = (request.headers.get("X-Voltaic-Token", "")
               or request.args.get("key", "")).strip()
    if not hmac.compare_digest(enviado, _ADMIN_KEY):
        return jsonify({"error": "No autorizado"}), 403

    usuarios = _cargar_usuarios()
    return jsonify({
        code: {
            "name": u["name"],
            "has_elevenlabs": u.get("has_elevenlabs", False),
            "active": u.get("active", True),
        }
        for code, u in usuarios.items()
    })


VOLTRACKER_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voltracker - Familia</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#0a0a0f;color:#f0f0f5;min-height:100vh;padding:16px}
header{text-align:center;padding:20px 0}
header h1{font-size:22px;background:linear-gradient(135deg,#00d4ff,#7b2ffc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.card{background:#161822;border:1px solid #26293b;border-radius:16px;padding:16px;margin-bottom:12px}
.card.alerta{border-color:#ef4444;background:#1f1215}
.card h3{font-size:16px;margin-bottom:4px}
.card .estado{font-size:13px;font-weight:bold}
.card .estado.calma{color:#4ade80}
.card .estado.alerta{color:#ef4444}
.card .info{font-size:12px;color:#8a8d9e;margin-top:4px}
.refresh{text-align:center;margin:16px 0;font-size:11px;color:#5a5d6e}
.spinner{text-align:center;padding:40px;color:#8a8d9e}
.error{text-align:center;padding:20px;color:#ef4444}
</style>
</head>
<body>
<header><h1>📺 Voltracker Familia</h1></header>
<div id="content"><div class="spinner">Cargando...</div></div>
<div class="refresh" id="refresh">Actualizado: --</div>

<script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore-compat.js"></script>
<script>
firebase.initializeApp({
  apiKey:"AIzaSyDZIq2zUDtp6GVorVM-DY2nsE6Pz4kX8Mg",
  projectId:"voltaic-familia-503c3",
  appId:"1:866657046047:web:c0c1c1c1c1c1c1c1c1c1c1"
});
var db=firebase.firestore();

function load(){
  db.collection("hubs").onSnapshot(function(snap){
    var html='';
    snap.forEach(function(doc){
      var d=doc.data();
      var alerta=d.estado==='alerta';
      var icono=alerta?'🔴':'🟢';
      var css=alerta?'alerta':'calma';
      var nivel=d.nivel||'';
      var ts=d.actualizado;
      var hace='';
      if(ts){var diff=(Date.now()-ts.toMillis())/1000;
        if(diff<60)hace='ahora';else if(diff<3600)hace='hace '+Math.floor(diff/60)+'min';else hace='hace '+Math.floor(diff/3600)+'h';
      }
      html+='<div class="card'+(alerta?' alerta':'')+'"><h3>'+icono+' '+doc.id+'</h3><div class="estado '+css+'">'+(alerta?'⚠ '+nivel:'✅ Calma')+'</div><div class="info">'+d.mensaje+'</div><div class="info">'+(d.hogar||'')+' · '+hace+'</div></div>';
    });
    if(!html)html='<div class="card"><h3>No hay hubs registrados</h3></div>';
    document.getElementById('content').innerHTML=html||'<div class="card"><h3>No hay hubs</h3></div>';
    document.getElementById('refresh').textContent='Actualizado: '+new Date().toLocaleTimeString();
  },function(err){
    document.getElementById('content').innerHTML='<div class="error">Error conectando</div>';
  });
}
load();
</script>
</body>
</html>"""

@app.route("/voltracker")
@app.route("/voltracker/")
def voltracker_page():
    import flask
    tracker_dir = _os.path.join(_os.path.dirname(_BASE), "tracker")
    return flask.send_from_directory(tracker_dir, "index.html")


@app.route("/tracker/")
@app.route("/tracker/<path:filename>")
def tracker_files(filename="index.html"):
    import flask
    tracker_dir = _os.path.join(_os.path.dirname(_BASE), "tracker")
    return flask.send_from_directory(tracker_dir, filename)


# ============================================================
#  VIDU S1 — el personaje con cara (ver api/vidu_live.py)
#
#  Se registra envuelto en try/except a proposito: si este modulo falla al
#  importar, se cae SOLO la funcion de video y el resto del sitio sigue en
#  pie. Tumbar a Catalina de voz, que ya funciona, por un problema de la
#  parte nueva seria peor que quedarnos sin la parte nueva.
# ============================================================
try:
    from vidu_live import bp_vidu
    app.register_blueprint(bp_vidu)
except Exception as _e:
    print(f"[vidu] no se pudo registrar el modulo de video: {_e}")


try:
    from simli_live import bp_simli
    app.register_blueprint(bp_simli)
except Exception as _e:
    print(f"[simli] no se pudo registrar el modulo de video: {_e}")

try:
    from paneles import bp_paneles
    app.register_blueprint(bp_paneles)
except Exception as _e:
    print(f"[paneles] no se pudo registrar la pantalla de paneles: {_e}")


@app.route("/static/js/<path:filename>")
def js_estatico(filename):
    """Sirve los JS propios desde C:/VoltaicChat/static/js.

    El SDK de Simli se sirve desde aca y no desde un CDN porque ninguno logra
    empaquetarlo: depende de livekit-client y jsDelivr, esm.sh y skypack fallan
    todos con "failed to resolve an internal import". El bundle se genera con
    esbuild (ver static/js/README.md). De paso, la pagina deja de depender de
    que un CDN de terceros este arriba.

    send_from_directory bloquea salirse del directorio, asi que un filename
    con ../ no sirve para leer otros archivos.
    """
    import flask
    return flask.send_from_directory(
        _os.path.join(_os.path.dirname(_BASE), "static", "js"), filename)


@app.route('/catalina/cara')
def catalina_simli_page():
    """Catalina con cara vía Simli.

    A diferencia de la version con Vidu, aca el cerebro es nuestro: piensa
    DeepSeek o Kimi y la voz sigue siendo la de ElevenLabs. Simli solo pone la
    cara. Sale nueve veces mas barato y Catalina si sabe de licitaciones.
    """
    return render_template('catalina_simli.html')


@app.route('/catalina/video')
def catalina_video_page():
    """Catalina con cara: video interactivo en tiempo real (Vidu S1).

    Queda abierta, como el resto de Catalina, porque es la cara publica de
    venta. Lo que la protege no es una clave sino los topes de gasto que
    aplica el servidor en /api/vidu/* (por sesion y por dia).
    """
    return render_template('catalina_video.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)