"""Coordina la ejecucion de los algoritmos y los traduce a JSON.

Es la capa de enlace entre el controller (app.py) y los modulos de
algoritmos: pasa de las estructuras internas (sets, frozensets de items,
nodos del arbol) a diccionarios y listas que Flask pueda serializar, y
traduce cualquier error del dominio en un GatewayError, para que el
controller nunca vea excepciones crudas de Python.

Los algoritmos no cambian ni se enteran de que existe la web: este archivo
solo los llama y da formato a lo que devuelven.
"""

import os

import evaluator
import ll1
import sdd as sdd_module
import slr1
from grammar import END, EPSILON, GrammarError, read_grammar_from_text
from sets import compute_first, compute_follow, format_set

# Ruta absoluta, para que el servidor encuentre la gramatica del Item 3 sin
# importar desde que carpeta se haya lanzado.
SDD_GRAMMAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdd_grammar.txt")

VERDICTS = {
    "both": "Select a parser (T: for LL(1), B: for SLR(1), Q: quit):",
    "ll1": "Grammar is LL(1).",
    "slr1": "Grammar is SLR(1).",
    "neither": "Grammar is neither LL(1) nor SLR(1).",
}


class GatewayError(Exception):
    """Error de dominio ya traducido a un mensaje legible para el cliente."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


# ----------------------------------------------------------------------
# Lectura de la gramatica
# ----------------------------------------------------------------------

def _normalize(text):
    """Deja el texto de la gramatica en el formato exacto de la Seccion 2.2.

    En la pagina web es incomodo tener que escribir a mano el numero de no
    terminales de la primera linea, asi que si falta se calcula. El formato
    oficial (con el numero) se sigue aceptando tal cual, que es el que usa
    main.py.
    """
    if not isinstance(text, str) or not text.strip():
        raise GatewayError("Hay que enviar el texto de la gramatica.")

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if lines[0].isdigit():
        return "\n".join(lines)

    return "\n".join([str(len(lines))] + lines)


def _load(text):
    """Lee la gramatica y calcula todo lo que depende solo de ella."""
    try:
        grammar = read_grammar_from_text(_normalize(text))
    except GrammarError as error:
        raise GatewayError(str(error))

    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table = ll1.build_table(grammar, first, follow)
    is_ll1, reasons = ll1.is_ll1(grammar, first, follow)
    automaton = slr1.SLRAutomaton(grammar, follow)

    return {
        "grammar": grammar,
        "first": first,
        "follow": follow,
        "table": table,
        "is_ll1": is_ll1,
        "reasons": reasons,
        "automaton": automaton,
    }


def _verdict(is_ll1, is_slr1):
    if is_ll1 and is_slr1:
        return "both"
    if is_ll1:
        return "ll1"
    if is_slr1:
        return "slr1"
    return "neither"


# ----------------------------------------------------------------------
# Formato de cada parte
# ----------------------------------------------------------------------

def _grammar_json(grammar):
    return {
        "start": grammar.start,
        "nonterminals": grammar.nonterminals,
        "terminals": grammar.terminals,
        "productions": [
            {
                "index": index,
                "head": head,
                "body": "".join(body) if body else EPSILON,
                "text": grammar.show_production(index),
            }
            for index, (head, body) in enumerate(grammar.productions)
        ],
    }


def _sets_json(grammar, first, follow):
    """FIRST y FOLLOW, con las mismas lineas que imprime --sets."""
    rows = [
        {
            "nonterminal": nonterminal,
            "first": format_set(first[nonterminal]),
            "follow": format_set(follow[nonterminal]),
            "firstSymbols": _ordered(first[nonterminal]),
            "followSymbols": _ordered(follow[nonterminal]),
        }
        for nonterminal in grammar.nonterminals
    ]

    lines = [f"First({row['nonterminal']}) = {row['first']}" for row in rows]
    lines += [f"Follow({row['nonterminal']}) = {row['follow']}" for row in rows]

    return {"rows": rows, "lines": lines}


def _ordered(symbols):
    """Los simbolos de un conjunto en el orden del enunciado."""
    result = sorted(s for s in symbols if s not in (EPSILON, END))
    if EPSILON in symbols:
        result.append(EPSILON)
    if END in symbols:
        result.append(END)
    return result


def _ll1_json(grammar, table, is_ll1, reasons):
    columns = grammar.terminals + [END]
    rows = []

    for head in grammar.nonterminals:
        cells = []
        for terminal in columns:
            indices = table.get((head, terminal), [])
            cells.append(
                {
                    "terminal": terminal,
                    "productions": [grammar.show_production(i) for i in indices],
                    "conflict": len(indices) > 1,
                }
            )
        rows.append({"nonterminal": head, "cells": cells})

    conflicts = [
        {
            "nonterminal": head,
            "terminal": terminal,
            "productions": [grammar.show_production(i) for i in indices],
        }
        for head, terminal, indices in ll1.table_conflicts(table)
    ]

    return {
        "isLL1": is_ll1,
        "reasons": reasons,
        "columns": columns,
        "rows": rows,
        "conflicts": conflicts,
    }


def _slr1_json(automaton):
    grammar = automaton.grammar
    terminals = grammar.terminals + [END]

    states = []
    for index, items in enumerate(automaton.states):
        transitions = [
            {"symbol": symbol, "target": automaton.goto_table[(index, symbol)]}
            for symbol in grammar.symbols()
            if (index, symbol) in automaton.goto_table
        ]
        states.append(
            {
                "index": index,
                "items": [automaton.show_item(item) for item in sorted(items)],
                "transitions": transitions,
            }
        )

    rows = []
    for state in range(len(automaton.states)):
        actions = {}
        for terminal in terminals:
            entry = automaton.action.get((state, terminal))
            if entry is None:
                continue
            kind, value = entry
            actions[terminal] = {
                "kind": kind,
                "text": automaton._show_action(entry, short=True),
                "detail": automaton._show_action(entry),
            }

        goto = {
            nonterminal: automaton.goto_table[(state, nonterminal)]
            for nonterminal in grammar.nonterminals
            if (state, nonterminal) in automaton.goto_table
        }

        rows.append({"state": state, "actions": actions, "goto": goto})

    return {
        "isSLR1": automaton.is_slr1,
        "conflicts": automaton.conflicts,
        "terminals": terminals,
        "nonterminals": grammar.nonterminals,
        "productions": [
            {"index": index, "text": automaton.show_production(index)}
            for index in range(len(automaton.productions))
        ],
        "states": states,
        "rows": rows,
    }


# ----------------------------------------------------------------------
# Arbol de analisis, con posiciones para dibujarlo
# ----------------------------------------------------------------------

def _tree_json(root):
    """Pasa el arbol a JSON y le calcula una disposicion para el dibujo.

    Cada hoja recibe una columna consecutiva y cada nodo interno se centra
    sobre sus hijos. Los nodos de A -> e no tienen hijos, asi que se les
    agrega un hijo visual 'e' solo para el dibujo.
    """
    counter = [0]

    def walk(node, depth):
        data = {
            "symbol": node.symbol,
            "depth": depth,
            "attrs": {name: _show(value) for name, value in sorted(node.attrs.items())},
            "children": [],
            "epsilon": False,
        }

        if node.children:
            data["children"] = [walk(child, depth + 1) for child in node.children]
            data["x"] = (data["children"][0]["x"] + data["children"][-1]["x"]) / 2
        elif not node.is_leaf:
            # Produccion A -> epsilon: se dibuja una hoja 'e'.
            child = {
                "symbol": EPSILON,
                "depth": depth + 1,
                "attrs": {},
                "children": [],
                "epsilon": True,
                "x": counter[0],
            }
            counter[0] += 1
            data["children"] = [child]
            data["x"] = child["x"]
        else:
            data["x"] = counter[0]
            counter[0] += 1

        return data

    tree = walk(root, 0)
    tree["width"] = counter[0]
    tree["height"] = _depth(tree) + 1
    return tree


def _depth(node):
    if not node["children"]:
        return node["depth"]
    return max(_depth(child) for child in node["children"])


def _show(value):
    """Un valor de atributo como texto, igual que en la salida de consola."""
    return repr(value) if isinstance(value, str) else str(value)


def _tree_lines(root):
    """El arbol anotado como lista de lineas, igual que lo imprime la consola."""
    lines = []

    def annotate(node):
        if not node.attrs:
            return ""
        parts = [f"{name} = {_show(value)}" for name, value in sorted(node.attrs.items())]
        return "{ " + ", ".join(parts) + " }"

    def walk(node, depth):
        suffix = annotate(node)
        lines.append("  " * depth + node.symbol + ("  " + suffix if suffix else ""))
        if not node.is_leaf and not node.children:
            lines.append("  " * (depth + 1) + EPSILON)
        for child in node.children:
            walk(child, depth + 1)

    walk(root, 0)
    return lines


# ----------------------------------------------------------------------
# Operaciones que usa el controller
# ----------------------------------------------------------------------

def analyze(text):
    """Todo lo que se puede decir de una gramatica: Items 1 y 2."""
    loaded = _load(text)
    grammar = loaded["grammar"]
    automaton = loaded["automaton"]

    code = _verdict(loaded["is_ll1"], automaton.is_slr1)

    return {
        "grammar": _grammar_json(grammar),
        "sets": _sets_json(grammar, loaded["first"], loaded["follow"]),
        "ll1": _ll1_json(grammar, loaded["table"], loaded["is_ll1"], loaded["reasons"]),
        "slr1": _slr1_json(automaton),
        "verdict": {"code": code, "message": VERDICTS[code]},
    }


def _choose_parser(loaded, requested):
    """Decide con cual parser se analiza, y avisa si el pedido no sirve."""
    is_ll1 = loaded["is_ll1"]
    is_slr1 = loaded["automaton"].is_slr1

    if requested == "ll1":
        if not is_ll1:
            raise GatewayError("La gramatica no es LL(1), no se puede usar ese parser.")
        return "ll1"

    if requested == "slr1":
        if not is_slr1:
            raise GatewayError("La gramatica no es SLR(1), no se puede usar ese parser.")
        return "slr1"

    # 'auto': el que sirva, con preferencia por LL(1) como en el enunciado.
    if is_ll1:
        return "ll1"
    if is_slr1:
        return "slr1"

    raise GatewayError("La gramatica no es LL(1) ni SLR(1), no hay parser que la analice.")


def _run_parser(loaded, which, string):
    """Analiza una cadena y devuelve (aceptada, raiz, rastro en JSON)."""
    trace = []

    if which == "ll1":
        accepted, root = ll1.parse(loaded["grammar"], loaded["table"], string, trace=trace)
        rows = [
            {
                "stack": stack,
                "input": rest,
                "action": (
                    f"output {detail}" if kind == "output"
                    else f"match {detail}" if kind == "match"
                    else f"error: {detail}" if kind == "error"
                    else "accept"
                ),
                "kind": kind,
            }
            for kind, stack, rest, detail in trace
        ]
    else:
        accepted, root = slr1.parse(loaded["automaton"], string, trace=trace)
        rows = [
            {
                "stack": states,
                "symbols": symbols,
                "input": rest,
                "action": action,
                "kind": action.split()[0].rstrip(":"),
            }
            for states, symbols, rest, action in trace
        ]

    return accepted, root, rows


def parse(text, strings, requested="auto", include_tree=True):
    """Items 1 y 2: analiza una lista de cadenas con el parser pedido."""
    if not isinstance(strings, list):
        raise GatewayError("'strings' debe ser una lista de cadenas.")

    loaded = _load(text)
    which = _choose_parser(loaded, requested)

    results = []
    for raw in strings:
        if not isinstance(raw, str):
            raise GatewayError("Cada cadena de 'strings' debe ser texto.")

        # La cadena vacia se escribe 'e', igual que en la consola.
        string = "" if raw.strip() == EPSILON else raw.strip()
        accepted, root, rows = _run_parser(loaded, which, string)

        result = {
            "string": raw.strip(),
            "parsed": string,
            "accepted": accepted,
            "answer": "yes" if accepted else "no",
            "trace": rows,
        }

        if include_tree and accepted and root is not None:
            result["tree"] = _tree_json(root)

        results.append(result)

    return {"parser": which, "results": results}


# ----------------------------------------------------------------------
# Item 3: la SDD
# ----------------------------------------------------------------------

def _sdd_json(sdd):
    return {
        "name": sdd["name"],
        "main": f"{sdd['main'][0]}.{sdd['main'][1]}",
        "attributes": [
            {
                "symbol": symbol,
                "attribute": name,
                "kind": kind,
                "type": datatype,
                "meaning": meaning,
            }
            for symbol, name, kind, datatype, meaning in sdd["attributes"]
        ],
        "rules": [
            {
                "production": f"{head} -> {''.join(body) if body else EPSILON}",
                "rules": [rule.text for rule in rules],
            }
            for (head, body), rules in sdd["rules"].items()
        ],
    }


def _graph_json(evaluation):
    """El grafo de dependencias por niveles, para dibujarlo sin cruces raros.

    El nivel de un atributo es uno mas que el mayor de los niveles de sus
    dependencias, asi todas las aristas van hacia abajo. Los atributos que
    quedaron en un ciclo no tienen nivel, y se mandan al fondo.
    """
    level = {}
    for instance in evaluation.order:
        level[instance] = 0

    incoming = {}
    for source, target in evaluation.edges:
        incoming.setdefault(target, []).append(source)

    for instance in evaluation.order:
        sources = incoming.get(instance, [])
        if sources:
            level[instance] = max(level.get(s, 0) for s in sources) + 1

    bottom = (max(level.values()) + 1) if level else 0
    unresolved = set(evaluation.unresolved)
    for instance in unresolved:
        level[instance] = bottom

    nodes = [
        {
            "id": evaluation.name(instance),
            "level": level.get(instance, bottom),
            "value": None if evaluation.circular else _show(evaluation.value(instance)),
            "unresolved": instance in unresolved,
        }
        for instance in sorted(level, key=lambda i: (level[i], evaluation.name(i)))
    ]

    edges = [
        {"from": evaluation.name(source), "to": evaluation.name(target)}
        for source, target in sorted(evaluation.edges)
    ]

    return {"nodes": nodes, "edges": edges, "levels": bottom + 1}


def sdd_grammar_text():
    """El texto de la gramatica del Item 3, para mostrarlo en la pagina."""
    try:
        with open(SDD_GRAMMAR_FILE, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        raise GatewayError(f"No se pudo leer '{SDD_GRAMMAR_FILE}': {error}")


def evaluate_sdd(strings, circular=False, requested="auto"):
    """Item 3: analiza y evalua una lista de cadenas con la SDD."""
    if not isinstance(strings, list):
        raise GatewayError("'strings' debe ser una lista de cadenas.")

    sdd = sdd_module.CIRCULAR_SDD if circular else sdd_module.SDD
    loaded = _load(sdd_grammar_text())
    which = _choose_parser(loaded, requested)

    results = []
    for raw in strings:
        if not isinstance(raw, str):
            raise GatewayError("Cada cadena de 'strings' debe ser texto.")

        string = "" if raw.strip() == EPSILON else raw.strip()
        accepted, root, rows = _run_parser(loaded, which, string)

        result = {
            "string": raw.strip(),
            "accepted": accepted,
            "answer": "yes" if accepted else "no",
            "trace": rows,
        }

        if accepted and root is not None:
            result.update(_evaluate_tree(root, loaded["grammar"], sdd))

        results.append(result)

    return {
        "parser": which,
        "circular": circular,
        "sdd": _sdd_json(sdd),
        "grammar": _grammar_json(loaded["grammar"]),
        "grammarText": sdd_grammar_text(),
        "results": results,
    }


def _evaluate_tree(root, grammar, sdd):
    """Evalua la SDD sobre un arbol y da el resultado en JSON."""
    try:
        evaluation = evaluator.evaluate(root, grammar, sdd)
    except evaluator.SDDError as error:
        return {"error": str(error)}

    data = {
        "circular": evaluation.circular,
        "graph": _graph_json(evaluation),
        "order": [
            {
                "position": position,
                "name": evaluation.name(instance),
                "value": _show(evaluation.value(instance)),
            }
            for position, instance in enumerate(evaluation.order, start=1)
        ],
        "unresolved": [evaluation.name(instance) for instance in evaluation.unresolved],
    }

    if evaluation.circular:
        return data

    # El arbol se pasa a JSON despues de evaluar, para que lleve los valores.
    data["tree"] = _tree_json(root)
    data["treeLines"] = _tree_lines(root)

    symbol, attribute = sdd["main"]
    data["main"] = {
        "name": f"{symbol}.{attribute}",
        "value": _show(root.attrs.get(attribute)),
    }

    return data
