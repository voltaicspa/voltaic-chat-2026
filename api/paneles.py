# -*- coding: utf-8 -*-
"""Pantalla de inicio de los paneles de VoltaicTech, para el celular.

Por que aca y no en el Centro de Control (:8600): esta app ya tiene HTTPS
gracias al tunel de Cloudflare, y sin HTTPS el celular no deja instalar una
pagina como aplicacion — queda como un marcador que abre el navegador con
barra de direcciones y todo. Con HTTPS se agrega a la pantalla de inicio con
su icono, como una app mas.

Los paneles se abren por la IP de Tailscale, asi que hay que tener la VPN
activa en el celular. Eso es a proposito: son paneles que hoy no piden clave,
y sacarlos a internet para que se vean lindos seria cambiar comodidad por
dejar la casa abierta.
"""
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request

bp_paneles = Blueprint("paneles", __name__)

# El host por el que se llega a los paneles. Tailscale por defecto: funciona
# igual dentro de la casa que fuera, sin abrir nada al mundo.
HOST_PANELES = os.environ.get("HOST_PANELES", "100.67.0.53").strip()

# Lo que se ve en el celular. El orden de esta lista es el orden en pantalla.
# Los grupos salen del prefijo, igual que en el Centro de Control.
PANELES = [
    ("Centro de Control", "Todo",     8600,  "🎛️", "El índice de todos"),
    ("Catalina",          "Todo",     8535,  "💬", "Asistente con cara y voz"),

    ("Admin de televisores", "Hub TV", 8518, "📺", "La consola del Hub"),
    ("Monitoreo",            "Hub TV", 8526, "📊", "Estado de los equipos"),
    ("Voz",                  "Hub TV", 8525, "🔊", "Avisos hablados"),
    ("Descargas APK",        "Hub TV", 8531, "📦", "Instaladores"),

    ("Consola Admin",    "Radar",   8502,  "🛡️", "Usuarios, licencias, claves"),
    ("Portal cliente",   "Radar",   8510,  "🎯", "Lo que ven los clientes"),
    ("Panel Analista",   "Radar",   8516,  "📈", "Producto premium"),

    ("Panel de Trabajo", "Yo",      8511,  "💼", "Postulaciones y pipeline"),
    ("NetControl",       "Casa",    3000,  "🛜", "El router de la casa"),
    ("Panel de Emergencia", "Casa", 8610,  "🚨", "Cortes y respaldos"),

    ("n8n",       "Motores", 5678,  "⚙️", "Automatizaciones"),
    ("OmniRoute", "Motores", 20128, "🔀", "Despachador de IAs"),
    ("Ollama",    "Motores", 11434, "🦙", "IA local"),
]

# Los que necesitan una ruta especifica para caer en la pagina util.
RUTAS = {20128: "/dashboard", 8535: "/catalina/cara"}

# La consola admin del Radar trae su propio SSL (certificado autofirmado), asi
# que hay que entrar por https o corta la conexion. El navegador va a advertir
# que el certificado no es de confianza: es esperado, lo firmo el propio Radar.
ESQUEMAS = {8502: "https"}


def _vivo(puerto, timeout=1.5):
    """Un TCP connect y nada mas. Pedir la pagina completa haria que la
    pantalla demore varios segundos en aparecer, y lo unico que queremos
    saber es si hay algo escuchando."""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((HOST_PANELES, puerto))
        return True
    except Exception:
        return False
    finally:
        s.close()


@bp_paneles.route("/api/paneles/estado")
def estado_paneles():
    """Cuales estan arriba. Se consultan todos en paralelo para que la
    pantalla no quede esperando trece timeouts en fila."""
    puertos = [p[2] for p in PANELES]
    with ThreadPoolExecutor(max_workers=13) as pool:
        vivos = dict(zip(puertos, pool.map(_vivo, puertos)))
    return jsonify({str(p): vivos[p] for p in puertos})


@bp_paneles.route("/paneles")
def pagina_paneles():
    """La pantalla de inicio. Protegida con la misma clave del panel de datos
    de Catalina: es una lista de accesos directos a paneles que en su mayoria
    no piden clave, asi que publicarla seria entregar el mapa completo."""
    from simli_live import _panel_autorizado
    no_pasa = _panel_autorizado()
    if no_pasa:
        return no_pasa

    grupos = {}
    for nombre, grupo, puerto, icono, detalle in PANELES:
        grupos.setdefault(grupo, []).append({
            "nombre": nombre,
            "puerto": puerto,
            "icono": icono,
            "detalle": detalle,
            "url": (f"{ESQUEMAS.get(puerto, 'http')}://{HOST_PANELES}:{puerto}"
                    f"{RUTAS.get(puerto, '')}"),
        })
    return render_template("paneles.html", grupos=grupos, host=HOST_PANELES)


@bp_paneles.route("/paneles/manifest.json")
def manifest():
    """Lo que hace que el celular la trate como aplicacion y no como marcador."""
    return jsonify({
        "name": "Paneles Voltaic",
        "short_name": "Paneles",
        "start_url": "/paneles",
        "display": "standalone",
        "background_color": "#0b0d14",
        "theme_color": "#0b0d14",
        "icons": [{
            # SVG en linea: evita tener que servir un PNG aparte y se ve nitido
            # en cualquier densidad de pantalla.
            "src": "data:image/svg+xml,"
                   "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E"
                   "%3Crect width='192' height='192' rx='42' fill='%230b0d14'/%3E"
                   "%3Ctext x='96' y='132' font-size='104' text-anchor='middle'%3E🎛️%3C/text%3E"
                   "%3C/svg%3E",
            "sizes": "192x192",
            "type": "image/svg+xml",
            "purpose": "any",
        }],
    })
