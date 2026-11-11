"""Servidor web del proyecto final: FIRST/FOLLOW, LL(1), SLR(1) y la SDD.

Es la capa controller: recibe las peticiones, valida la forma del JSON y
delega el trabajo real en el gateway. Los algoritmos de los Items 1, 2 y 3
son exactamente los mismos que usa la version de consola (main.py y
sdd_main.py); aqui solo se exponen por HTTP.

Se ejecuta con: python app.py
"""

import os

from flask import Flask, jsonify, render_template, request
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException

import gateway

app = Flask(__name__)

PARSERS = ("auto", "ll1", "slr1")

# Valores que se interpretan como "no" en los campos booleanos del JSON.
FALSE_VALUES = ("0", "false", "no", "off")


def _is_off(value):
    """True si el valor recibido significa 'apagado'."""
    return str(value).strip().lower() in FALSE_VALUES


def _body():
    """Cuerpo JSON de la peticion, o None si no es un objeto valido."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _strings(data):
    """Lee el campo 'strings', que acepta una lista o un texto multilinea.

    El textarea de la pagina manda un solo texto con una cadena por linea,
    que es como se escriben en la consola.
    """
    raw = data.get("strings", [])

    if isinstance(raw, str):
        return [line.strip() for line in raw.splitlines() if line.strip()]

    if isinstance(raw, list):
        return raw

    return None


def _parser(data):
    """Lee el parser pedido: 'auto', 'll1' o 'slr1'."""
    requested = str(data.get("parser", "auto")).strip().lower()
    return requested if requested in PARSERS else None


@app.post("/api/grammar")
def analyze_grammar():
    """Items 1 y 2: conjuntos, tablas, automata LR(0) y veredicto.

    Cuerpo: {"grammar": "3\\nS -> AB\\n..."}. La primera linea con el numero
    de no terminales es opcional desde la web.
    """
    data = _body()
    if data is None:
        return jsonify({"error": "El cuerpo de la peticion debe ser un JSON valido."}), 400

    if not isinstance(data.get("grammar"), str):
        return jsonify({"error": "Falta el campo 'grammar' con el texto de la gramatica."}), 400

    try:
        return jsonify(gateway.analyze(data["grammar"])), 200
    except gateway.GatewayError as e:
        return jsonify({"error": e.message}), 422


@app.post("/api/parse")
def parse_strings():
    """Item 2: analiza cadenas con el parser LL(1) o con el SLR(1).

    Cuerpo: {"grammar": ..., "strings": [...] o texto, "parser": "auto"}.
    """
    data = _body()
    if data is None:
        return jsonify({"error": "El cuerpo de la peticion debe ser un JSON valido."}), 400

    if not isinstance(data.get("grammar"), str):
        return jsonify({"error": "Falta el campo 'grammar' con el texto de la gramatica."}), 400

    strings = _strings(data)
    if strings is None:
        return jsonify({"error": "'strings' debe ser una lista de cadenas o un texto."}), 400

    requested = _parser(data)
    if requested is None:
        return jsonify({"error": "'parser' debe ser 'auto', 'll1' o 'slr1'."}), 400

    # El arbol de analisis puede ser grande, asi que el cliente puede apagarlo.
    include_tree = not _is_off(data.get("includeTree", True))

    try:
        return jsonify(gateway.parse(data["grammar"], strings, requested, include_tree)), 200
    except gateway.GatewayError as e:
        return jsonify({"error": e.message}), 422


@app.post("/api/sdd")
def evaluate_sdd():
    """Item 3: evalua la SDD sobre el arbol de cada cadena.

    Cuerpo: {"strings": [...] o texto, "circular": false, "parser": "auto"}.
    La gramatica es la del Item 3 y la trae el servidor, porque las reglas
    semanticas estan escritas para ella.
    """
    data = _body()
    if data is None:
        return jsonify({"error": "El cuerpo de la peticion debe ser un JSON valido."}), 400

    strings = _strings(data)
    if strings is None:
        return jsonify({"error": "'strings' debe ser una lista de cadenas o un texto."}), 400

    requested = _parser(data)
    if requested is None:
        return jsonify({"error": "'parser' debe ser 'auto', 'll1' o 'slr1'."}), 400

    circular = not _is_off(data.get("circular", False))

    try:
        return jsonify(gateway.evaluate_sdd(strings, circular, requested)), 200
    except gateway.GatewayError as e:
        return jsonify({"error": e.message}), 422


@app.get("/api/sdd")
def sdd_definition():
    """La gramatica y la definicion de la SDD, sin evaluar nada."""
    try:
        return jsonify(gateway.evaluate_sdd([], False, "auto")), 200
    except gateway.GatewayError as e:
        return jsonify({"error": e.message}), 422


@app.get("/analyzer")
def analyzer_page():
    """Pagina de demostracion: tablas, automata, arbol y grafo."""
    try:
        return render_template("analyzer.html")
    except TemplateNotFound:
        # Sin la plantilla los endpoints siguen funcionando, asi que se avisa
        # que falta el archivo en vez de devolver un error interno.
        return jsonify(
            {
                "error": "Falta el archivo 'templates/analyzer.html', que es la pagina de "
                         "demostracion. Los endpoints de /api siguen funcionando."
            }
        ), 500


@app.get("/")
def health():
    """Comprobacion rapida de que el servidor esta arriba."""
    return jsonify(
        {
            "status": "ok",
            "message": "Formal Languages final project server is running",
            "endpoints": {
                "POST /api/grammar": "FIRST, FOLLOW, tabla LL(1), automata LR(0) y tablas SLR(1)",
                "POST /api/parse": "analiza cadenas con el parser LL(1) o SLR(1)",
                "POST /api/sdd": "evalua la SDD del Item 3 sobre cada cadena",
                "GET /api/sdd": "gramatica, atributos y reglas semanticas del Item 3",
                "GET /analyzer": "pagina web de demostracion",
            },
        }
    ), 200


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Los errores propios de Flask tambien salen como JSON.

    Sin esto, un 404 o un 405 devuelven la pagina HTML por defecto y la API
    contestaria en dos formatos distintos segun el error.
    """
    messages = {
        404: "La ruta no existe. Consulta GET / para ver los endpoints disponibles.",
        405: f"El metodo {request.method} no esta permitido en esta ruta.",
        413: "El cuerpo de la peticion es demasiado grande.",
    }

    return jsonify({"error": messages.get(error.code, error.description), "status": error.code}), error.code


if __name__ == "__main__":
    # Por defecto el servidor solo escucha en esta maquina. Para exponerlo en
    # la red local: HOST=0.0.0.0 antes de correrlo. Con DEBUG=0 se apaga el
    # modo depuracion (y con el, el recargador automatico).
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=not _is_off(os.environ.get("DEBUG", "1")),
    )
