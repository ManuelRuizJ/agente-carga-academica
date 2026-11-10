# -*- coding: utf-8 -*-
"""
Cliente mínimo de Ollama que trabaja solo con CPU.

  * La GPU se desactiva desde el servidor (./iniciar_ollama_cpu.sh) y, además,
    cada petición manda num_gpu=0. CrewAI usa el endpoint /v1 de Ollama, que
    ignora `num_gpu`, por eso también se desactiva en el servidor.

Reglas de uso:
  * El LLM SOLO interpreta lenguaje natural y redacta la explicación final
    (2 llamadas por ejecución). Todo el razonamiento lo hace Python + ontología.
  * Si Ollama no está disponible, el sistema sigue funcionando (reglas).
  * Respuestas cacheadas en disco: repetir una ejecución no vuelve a llamar al modelo.
"""
import hashlib
import json
import os
import time
from pathlib import Path

import requests

from . import config

_CACHE = config.DIR_SALIDAS / "cache_llm.json"
_PS = Path("/sys/class/power_supply")


def estado_energia() -> dict:
    """Lee /sys/class/power_supply: ¿hay cargador?, % y voltaje de la batería.

    En un equipo portátil, el pico de consumo del LLM en CPU puede apagar el
    equipo si está en batería; por eso sin cargador el LLM se desactiva.
    """
    info = {"cargador": None, "bateria": None, "porcentaje": None,
            "voltaje": None, "voltaje_min": None}
    try:
        for d in _PS.iterdir():
            tipo = (d / "type").read_text().strip()
            if tipo == "Mains":
                info["cargador"] = (d / "online").read_text().strip() == "1"
            elif tipo == "Battery":
                info["bateria"] = d.name
                leer = lambda f: int((d / f).read_text()) if (d / f).exists() else None
                info["porcentaje"] = leer("capacity")
                v, vmin = leer("voltage_now"), leer("voltage_min_design")
                info["voltaje"] = v / 1e6 if v else None
                info["voltaje_min"] = vmin / 1e6 if vmin else None
    except OSError:
        pass
    return info


def en_bateria() -> bool:
    e = estado_energia()
    return e["bateria"] is not None and e["cargador"] is False


class ClienteLLM:
    def __init__(self, modelo=None, habilitado=True):
        self.modelo = modelo or config.MODELO
        self.url = None
        self.motivo = ""
        self.llamadas = 0
        self.segundos = 0.0
        if habilitado:
            self._detectar()
        else:
            self.motivo = "desactivado con --sin-llm"

    # -------------------------------------------------------------- conexión
    def _detectar(self):
        if en_bateria() and os.getenv("LLM_EN_BATERIA") != "1":
            self.motivo = ("LLM desactivado: equipo en batería (riesgo de apagado). "
                           "Conecta el cargador o usa LLM_EN_BATERIA=1")
            print(f"⚠ {self.motivo}. Se continúa solo con reglas.")
            return
        errores = []
        for url in config.OLLAMA_URLS:
            try:
                tags = requests.get(f"{url}/api/tags", timeout=2).json()
            except Exception:
                errores.append(f"{url}: sin respuesta")
                continue
            nombres = {m["name"] for m in tags.get("models", [])}
            if self.modelo in nombres or f"{self.modelo}:latest" in nombres:
                self.url = url
                return
            errores.append(f"{url}: no tiene el modelo '{self.modelo}'")
        self.motivo = "; ".join(errores)

    @property
    def disponible(self) -> bool:
        return self.url is not None

    # -------------------------------------------------------------- caché
    @staticmethod
    def _leer_cache() -> dict:
        try:
            return json.loads(_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _guardar_cache(cache: dict):
        try:
            _CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

    # -------------------------------------------------------------- llamada
    def chat(self, sistema: str, usuario: str, esquema: dict | None = None,
             max_tokens: int = 300, temperatura: float = 0.1) -> str | None:
        """Devuelve el texto de respuesta, o None si no hay LLM o falla."""
        if not self.disponible:
            return None
        llave = hashlib.sha256(json.dumps(
            [self.modelo, sistema, usuario, esquema, max_tokens, temperatura],
            ensure_ascii=False).encode()).hexdigest()[:24]
        cache = self._leer_cache()
        if llave in cache:
            return cache[llave]

        cuerpo = {
            "model": self.modelo,
            "stream": False,
            "keep_alive": "2m",            # libera la RAM al poco tiempo
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": usuario}],
            "options": {
                "num_gpu": 0,              # NUNCA cargar capas en la GPU integrada
                "num_thread": config.HILOS_LLM,
                "num_ctx": config.CTX_LLM,
                "num_predict": max_tokens,
                "temperature": temperatura,
            },
        }
        if esquema:
            cuerpo["format"] = esquema     # salida estructurada (JSON Schema)
        t0 = time.perf_counter()
        try:
            r = requests.post(f"{self.url}/api/chat", json=cuerpo, timeout=config.TIMEOUT_LLM)
            r.raise_for_status()
            texto = r.json()["message"]["content"].strip()
        except Exception as e:  # el sistema nunca se cae por el LLM
            self.motivo = f"falló la llamada: {e}"
            return None
        finally:
            self.segundos += time.perf_counter() - t0
            self.llamadas += 1
        cache[llave] = texto
        self._guardar_cache(cache)
        return texto


def diagnostico() -> list[str]:
    """Revisa el entorno y explica qué está pasando con Ollama y la memoria."""
    lineas = []
    for url in config.OLLAMA_URLS:
        try:
            tags = requests.get(f"{url}/api/tags", timeout=2).json()
            modelos = [m["name"] for m in tags.get("models", [])]
            lineas.append(f"✔ Ollama responde en {url} — modelos: {', '.join(modelos) or 'NINGUNO'}")
            try:
                ps = requests.get(f"{url}/api/ps", timeout=2).json().get("models", [])
                for m in ps:
                    vram = m.get("size_vram", 0)
                    estado = "⚠ USANDO GPU" if vram else "CPU ✔"
                    lineas.append(f"    cargado: {m['name']} ({m.get('size', 0)/1e9:.1f} GB) → {estado}")
            except Exception:
                pass
        except Exception:
            lineas.append(f"✘ Ollama no responde en {url}")
    try:
        info = {}
        for ln in open("/proc/meminfo"):
            k, v = ln.split(":")
            info[k] = int(v.split()[0]) / 1024 / 1024
        disp = info.get("MemAvailable", 0)
        lineas.append(f"  RAM disponible: {disp:.1f} GB de {info.get('MemTotal', 0):.1f} GB")
        if disp < 3.5:
            lineas.append("  ⚠ Poca RAM libre: cierra el navegador antes de usar el LLM "
                          "(llama3.2 necesita ~2.5 GB).")
    except OSError:
        pass
    e = estado_energia()
    if e["bateria"]:
        volt = (f", {e['voltaje']:.2f} V (mín. de diseño {e['voltaje_min']:.2f} V)"
                if e["voltaje"] and e["voltaje_min"] else "")
        fuente = "cargador conectado ✔" if e["cargador"] else "⚠ EN BATERÍA"
        lineas.append(f"  Energía: {fuente} — batería {e['porcentaje']}%{volt}")
        if not e["cargador"]:
            lineas.append("  ⚠ Sin cargador el LLM queda desactivado: el pico de consumo "
                          "puede apagar el equipo.")
    lineas.append(f"  Modelo configurado: {config.MODELO} | hilos: {config.HILOS_LLM} | "
                  f"contexto: {config.CTX_LLM}")
    return lineas
