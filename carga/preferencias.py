# -*- coding: utf-8 -*-
"""
Interpretación de preferencias en lenguaje natural (capacidad del AgenteHorarios).

Estrategia híbrida y robusta:
  1. Se parte de las preferencias GUARDADAS en la ontología (PreferenciaHorario,
     PreferenciaModalidad, PreferenciaCarga).
  2. Si el alumno escribe una petición ("quiero carga ligera, en la tarde y sin
     viernes, me interesa IA"), un analizador de reglas la interpreta siempre.
  3. Si hay LLM, se le pide un JSON con esquema fijo; lo que regrese se valida
     contra el catálogo y los valores permitidos (el modelo no puede inventar
     materias). Lo válido del LLM tiene prioridad sobre las reglas.
"""
import json
import re
import unicodedata

from . import config

ESQUEMA = {
    "type": "object",
    "properties": {
        "tipo_carga": {"type": ["string", "null"], "enum": ["ligera", "normal", "pesada", None]},
        "turno": {"type": ["string", "null"], "enum": ["matutino", "vespertino", None]},
        "modalidad": {"type": ["string", "null"], "enum": ["presencial", "en_linea", "hibrida", None]},
        "dias_libres": {"type": "array", "items": {"type": "string",
                        "enum": ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]}},
        "materias_interes": {"type": "array", "items": {"type": "string"}},
        "materias_evitar": {"type": "array", "items": {"type": "string"}},
        "max_materias": {"type": ["integer", "null"]},
    },
    "required": ["tipo_carga", "turno", "modalidad", "dias_libres",
                 "materias_interes", "materias_evitar", "max_materias"],
}

_DIAS = {"lunes": "Lunes", "martes": "Martes", "miercoles": "Miercoles",
         "jueves": "Jueves", "viernes": "Viernes"}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_GENERICAS = {"sistemas", "programacion", "desarrollo", "calculo", "computacion", "computadoras",
              "ingenieria", "fundamentos", "introduccion", "matematicas", "datos", "analisis",
              "tecnologia", "tecnologico", "orientada", "ciencia", "arquitectura",
              # comunes en los nombres reales del plan de la Ibero
              "laboratorio", "proyecto", "proyectos", "topicos", "digital", "digitales", "diseno",
              "gestion", "general", "computacionales", "computadora", "avanzada", "avanzados",
              "aplicaciones", "servicios", "procesos", "informacion", "universitario",
              "universitarias", "tecnologias", "actual", "sociedad", "ambientes"}

# Palabras comunes del español que NO pueden contar como sigla ni palabra clave
# ("sin viernes" no es "Sistemas Informáticos en los Negocios"; "por la tarde"
# no es "Dibujo por Computadora"; "al" no es "Álgebra Lineal").
_STOP = {"a", "al", "el", "la", "lo", "le", "les", "los", "las", "de", "del", "di", "en", "es",
         "se", "si", "no", "un", "una", "uno", "sin", "con", "por", "para", "que", "mi", "me",
         "te", "tu", "su", "ya", "yo", "ni", "y", "o", "e", "in", "pe", "ca", "hoy", "mas", "muy",
         "dia", "son", "ser", "hay", "esa", "ese", "eso", "sus", "mis", "tus", "nos", "has",
         "ha", "he", "da", "va", "ve", "ir", "fe", "ti", "id", "md", "mu", "ee", "ed"}


def _siglas(nombre: str) -> str:
    """'Fundamentos de Inteligencia Artificial' → 'ia' (sin palabras genéricas)."""
    return "".join(p[0] for p in _norm(nombre).split()
                   if len(p) > 3 and p not in _GENERICAS)


def _sigla_util(sig: str) -> bool:
    return len(sig) >= 2 and sig not in _STOP


def _palabras_clave(nombre: str) -> set:
    """Palabras distintivas de una materia: 'redes', 'embebidos', 'nube'…"""
    return {p for p in _norm(nombre).split()
            if len(p) >= 3 and p not in _GENERICAS and p not in _STOP}


def _puntaje(clave: str, m, frase: str, palabras: set) -> int:
    """Qué tan claramente una frase habla de una materia: 3 = nombre completo,
    clave o sigla; si no, cuántas palabras distintivas comparte."""
    sig = _siglas(m.nombre)
    if (_norm(m.nombre) in frase or clave.lower() in palabras
            or (_sigla_util(sig) and sig in palabras)):
        return 3
    return len(_palabras_clave(m.nombre) & palabras)


def _mencionada(clave: str, materias: dict, texto: str) -> bool:
    """¿Hay evidencia en el texto de que el alumno habló de esta materia?"""
    t = _norm(texto)
    return _puntaje(clave, materias[clave], t, set(re.findall(r"\w+", t))) > 0


def buscar_materia(texto: str, materias: dict) -> str | None:
    """Mapea 'IA', 'inteligencia artificial', 'IAR501', 'redes'… a una clave."""
    t = _norm(texto).strip()
    if not t:
        return None
    for clave, m in materias.items():
        if t == clave.lower() or t == _norm(m.nombre):
            return clave
    for clave, m in materias.items():
        if _sigla_util(t) and t == _siglas(m.nombre):
            return clave
    for clave, m in materias.items():
        if len(t) >= 4 and t in _norm(m.nombre):
            return clave
    return None


# ------------------------------------------------------------------- reglas
def _por_reglas(texto: str, materias: dict) -> dict:
    t = _norm(texto)
    r = {}
    if re.search(r"\b(ligera|liger[oa]|poca[s]?|pocas materias|tranquil|no .*saturar|relajad)", t):
        r["tipo_carga"] = "ligera"
    elif re.search(r"\b(pesada|muchas|adelantar|maxim[oa]|cargad[oa]|lo mas posible)", t):
        r["tipo_carga"] = "pesada"
    elif re.search(r"\b(normal|regular|equilibrad)", t):
        r["tipo_carga"] = "normal"

    if re.search(r"(tarde|vespertin|despues de (la )?comida)", t):
        r["turno"] = "vespertino"
    elif re.search(r"(manana|matutin|temprano)", t):
        r["turno"] = "matutino"

    if re.search(r"(hibrid)", t):
        r["modalidad"] = "hibrida"
    elif re.search(r"(en linea|online|virtual|remot|desde casa|a distancia)", t):
        r["modalidad"] = "en_linea"
    elif re.search(r"presencial", t):
        r["modalidad"] = "presencial"

    libres = []
    for d, D in _DIAS.items():
        if re.search(rf"(sin|no\b[^.,;]*|libre[s]? (el |los )?|descansar (el |los )?)[^.,;]*\b{d}", t) \
                or re.search(rf"\b{d}[^.,;]* libre", t):
            libres.append(D)
    r["dias_libres"] = libres

    m = re.search(r"\b(\d)\s*materias", t)
    if m:
        r["max_materias"] = int(m.group(1))

    interes, evitar = [], []
    frases = re.split(r"[.,;]| y | pero ", t)
    for f in frases:
        negativa = re.search(r"\b(no quiero|no me gusta|evitar|sin|odio|nada de)\b", f)
        palabras = set(re.findall(r"\w+", f))
        puntos = {c: _puntaje(c, mat, f, palabras) for c, mat in materias.items()}
        mejor = max(puntos.values(), default=0)
        if mejor:   # solo las que mejor coinciden: "inteligencia artificial" ≠ "inteligencia de datos"
            (evitar if negativa else interes).extend(c for c, p in puntos.items() if p == mejor)
    r["materias_interes"] = sorted(set(interes))
    r["materias_evitar"] = sorted(set(evitar))
    return r


# ------------------------------------------------------------------- LLM
_SISTEMA = (
    "Eres un extractor de preferencias académicas. Lee la petición de un estudiante "
    "y devuelve SOLO un JSON con los campos del esquema. Usa null o [] cuando el "
    "estudiante no mencione algo. NO inventes preferencias.\n"
    "- tipo_carga: ligera | normal | pesada\n"
    "- turno: matutino (mañana) | vespertino (tarde)\n"
    "- modalidad: presencial | en_linea | hibrida\n"
    "- dias_libres: días en los que NO quiere clases\n"
    "- materias_interes / materias_evitar: nombres de materias tal como aparecen en el catálogo\n"
    "- max_materias: número máximo de materias si lo dice explícitamente"
)


def _por_llm(texto: str, materias: dict, llm) -> dict | None:
    if llm is None or not llm.disponible:
        return None
    catalogo = "; ".join(f"{m.nombre}" for m in materias.values())
    usuario = f"Catálogo de materias: {catalogo}\n\nPetición del estudiante: \"{texto}\""
    crudo = llm.chat(_SISTEMA, usuario, esquema=ESQUEMA, max_tokens=200, temperatura=0)
    if not crudo:
        return None
    try:
        d = json.loads(crudo)
    except json.JSONDecodeError:
        return None
    limpio = {}
    if d.get("tipo_carga") in config.CARGA_TIPO:
        limpio["tipo_carga"] = d["tipo_carga"]
    if d.get("turno") in ("matutino", "vespertino"):
        limpio["turno"] = d["turno"]
    if d.get("modalidad") in ("presencial", "en_linea", "hibrida"):
        limpio["modalidad"] = d["modalidad"]
    dias = [x for x in (d.get("dias_libres") or []) if x in _DIAS.values()]
    if dias:
        limpio["dias_libres"] = dias
    for k in ("materias_interes", "materias_evitar"):
        claves = sorted({c for c in (buscar_materia(x, materias) for x in d.get(k) or [])
                         if c and _mencionada(c, materias, texto)})   # anti-alucinación
        if claves:
            limpio[k] = claves
    mm = d.get("max_materias")
    if isinstance(mm, int) and 1 <= mm <= 8:
        limpio["max_materias"] = mm
    return limpio


# ------------------------------------------------------------------- API
def construir_preferencias(est, materias: dict, texto: str = "", llm=None) -> dict:
    guardadas = est.preferencias
    tipo, prio_c, cobj, maxm = guardadas.get("carga", ("normal", 1, None, None))
    turno, prio_t = guardadas.get("turno", (None, 1))
    modalidad, prio_m = guardadas.get("modalidad", (None, 1))
    p = {
        "texto": texto,
        "tipo_carga": tipo, "creditos_objetivo": cobj, "max_materias": maxm,
        "turno": turno, "peso_turno": prio_t,
        "modalidad": modalidad, "peso_modalidad": prio_m,
        "dias_libres": [], "peso_dias": 6,   # un día libre pedido explícitamente pesa el doble que el turno
        "materias_interes": [], "materias_evitar": [],
        "fuente": {k: "ontología" for k in ("tipo_carga", "turno", "modalidad")},
        "interpretado_por": "solo ontología",
    }
    if texto.strip():
        reglas = _por_reglas(texto, materias)
        llm_r = _por_llm(texto, materias, llm)
        if llm_r is not None:
            p["interpretado_por"] = f"LLM ({llm.modelo}) validado + reglas"
        else:
            p["interpretado_por"] = "reglas (sin LLM)"
        for campo in ("tipo_carga", "turno", "modalidad", "dias_libres",
                      "materias_interes", "materias_evitar", "max_materias"):
            val, fuente = None, None
            if llm_r and llm_r.get(campo):
                val, fuente = llm_r[campo], "petición (LLM)"
            elif reglas.get(campo):
                val, fuente = reglas[campo], "petición (reglas)"
            if val is not None:
                p[campo] = val
                p["fuente"][campo] = fuente
                if campo == "tipo_carga":           # la meta se recalcula según el tipo
                    p["creditos_objetivo"] = None   # (max_materias se procesa después)
                    p["max_materias"] = None
                if campo == "turno":
                    p["peso_turno"] = max(p["peso_turno"], 3)   # lo dijo explícitamente
                if campo == "modalidad":
                    p["peso_modalidad"] = max(p["peso_modalidad"], 3)

    # Una materia ya aprobada no puede ser "de interés" para este periodo
    for k in ("materias_interes", "materias_evitar"):
        p[k] = [c for c in p[k] if c not in est.aprobadas]

    meta = config.CARGA_TIPO.get(p["tipo_carga"], config.CARGA_TIPO["normal"])
    p["creditos_objetivo"] = p["creditos_objetivo"] or meta["creditos"]
    p["max_materias"] = p["max_materias"] or meta["max_materias"]
    p["max_dificiles"] = meta["max_dificiles"]
    return p


def describir(p: dict) -> str:
    partes = [f"carga {p['tipo_carga']} (~{p['creditos_objetivo']} créditos, máx. {p['max_materias']} materias)"]
    if p["turno"]:
        partes.append(f"turno {p['turno']}")
    if p["modalidad"]:
        partes.append(f"modalidad {p['modalidad'].replace('_', ' ')}")
    if p["dias_libres"]:
        partes.append("sin clases: " + ", ".join(p["dias_libres"]))
    if p["materias_interes"]:
        partes.append("le interesa: " + ", ".join(p["materias_interes"]))
    if p["materias_evitar"]:
        partes.append("evitar: " + ", ".join(p["materias_evitar"]))
    return "; ".join(partes)
