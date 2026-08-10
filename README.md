# VoltaicChat — Chat con IA y Voz

Chat inteligente con IA (DeepSeek) + reconocimiento de voz + síntesis de voz.
Cada usuario configura su propia API key (ideal para vender como producto).

## 🌐 Chat en línea

**Chat:** https://voltaic-chat.vercel.app/chat
**Dashboard:** https://voltaic-chat.vercel.app/

Al entrar, pide la API key de DeepSeek. Se guarda solo en el navegador del usuario.

## 📦 Archivos del proyecto

| Archivo | Qué hace |
|---------|----------|
| `chat.py` | Servidor local (corre en tu PC, puerto 8599) |
| `api/index.py` | Versión para Vercel (web) |
| `templates/index.html` | Interfaz del chat (HTML + JS con voz) |
| `templates/dashboard.html` | Panel de configuración ElevenLabs |
| `config.json` | Configuración del sistema (prompt, voz, modelo) |
| `Iniciar_Chat.bat` | Iniciar el chat local con doble clic |
| `.env` | Variables de entorno locales |
| `vercel.json` | Configuración de despliegue Vercel |

## 🖥️ Para usar en tu PC (local)

```bash
cd C:\VoltaicChat
pip install flask openai requests
python chat.py
```

Abrir: http://localhost:8599
Dashboard: http://localhost:8599/dashboard

## 🚀 Para desplegar en Vercel (web)

```bash
cd C:\VoltaicChat
npx vercel deploy --prod
```

El proyecto ya está configurado (`vercel.json` + `api/index.py`).
Se despliega a: https://voltaic-chat.vercel.app

## 🎤 Funcionalidades

- **Texto** — Escribís y la IA responde
- **Voz entrada** — Botón 🎤, hablás y se transcribe
- **Voz salida** — La IA te responde hablando (speech del navegador)
- **API key propia** — Cada usuario pone la suya al entrar
- **Configurable** — Prompt del sistema, voz, temperatura desde el dashboard

## 🔑 API Keys

- **DeepSeek** — https://platform.deepseek.com/ (necesaria para el chat)
- **ElevenLabs** — https://elevenlabs.io/ (solo para el dashboard de configuración)

## 📤 Modelo de venta

Cada cliente:
1. Entra al link del chat
2. Pega su API key de DeepSeek (se guarda en su navegador)
3. Usa el chat con texto y voz

**Ventaja:** el cliente paga su propio consumo de IA. Tú solo vendes el software.
