"""Pruebas del proyecto, con la libreria estandar y nada mas.

Se ejecuta con

    python tests.py

Cubre los tres ejemplos del enunciado, los conjuntos FIRST y FOLLOW de
gramaticas con epsilon, los cuatro casos de salida de la Seccion 2.2.2, los
dos parsers sobre las mismas cadenas y el evaluador de la SDD del Item 3,
incluida la deteccion de una SDD circular.
"""

import io
import sys

import evaluator
import gateway
import ll1
import sdd as sdd_module
import slr1
from grammar import read_grammar_from_text
from sets import compute_first, compute_follow, format_set, print_sets

PASSED = 0
FAILED = []


def check(name, got, expected):
    global PASSED
    if got == expected:
        PASSED += 1
    else:
        FAILED.append(f"{name}\n    se esperaba: {expected!r}\n    se obtuvo:   {got!r}")


def analyze(text):
    """Devuelve (gramatica, first, follow, tabla LL(1), automata SLR)."""
    grammar = read_grammar_from_text(text)
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table = ll1.build_table(grammar, first, follow)
    automaton = slr1.SLRAutomaton(grammar, follow)
    return grammar, first, follow, table, automaton


def verdict(text):
    """Cual de los cuatro casos de la Seccion 2.2.2 corresponde."""
    grammar, first, follow, _, automaton = analyze(text)
    is_ll1, _ = ll1.is_ll1(grammar, first, follow)

    if is_ll1 and automaton.is_slr1:
        return "both"
    if is_ll1:
        return "ll1"
    if automaton.is_slr1:
        return "slr1"
    return "neither"


def accepts(text, strings, parser):
    """Respuestas 'yes'/'no' de un parser sobre una lista de cadenas."""
    grammar, first, follow, table, automaton = analyze(text)
    answers = []

    for string in strings:
        if parser == "ll1":
            accepted, _ = ll1.parse(grammar, table, string)
        else:
            accepted, _ = slr1.parse(automaton, string)
        answers.append("yes" if accepted else "no")

    return answers


# ----------------------------------------------------------------------
# Item 1: FIRST y FOLLOW
# ----------------------------------------------------------------------

EXAMPLE_2 = "3\nS -> AB\nA -> aA d\nB -> bBc e\n"

# Gramatica de expresiones de la Seccion 4.4.2 del libro, con los nombres
# del enunciado: S hace de E, T de T y F de F.
BOOK_EXPRESSIONS = "5\nS -> TA\nA -> +TA e\nT -> FB\nB -> *FB e\nF -> (S) i\n"


def test_first_follow():
    _, first, follow, _, _ = analyze(BOOK_EXPRESSIONS)

    # Valores de la Seccion 4.4.2 del libro (Ejemplo 4.30).
    check("FIRST(S)", format_set(first["S"]), "{(, i}")
    check("FIRST(A)", format_set(first["A"]), "{+, e}")
    check("FIRST(T)", format_set(first["T"]), "{(, i}")
    check("FIRST(B)", format_set(first["B"]), "{*, e}")
    check("FIRST(F)", format_set(first["F"]), "{(, i}")

    check("FOLLOW(S)", format_set(follow["S"]), "{), $}")
    check("FOLLOW(A)", format_set(follow["A"]), "{), $}")
    check("FOLLOW(T)", format_set(follow["T"]), "{), +, $}")
    check("FOLLOW(B)", format_set(follow["B"]), "{), +, $}")
    check("FOLLOW(F)", format_set(follow["F"]), "{), *, +, $}")


def test_epsilon_sets():
    _, first, follow, _, _ = analyze(EXAMPLE_2)

    check("FIRST(B) con epsilon", format_set(first["B"]), "{b, e}")
    check("FIRST(S) con epsilon", format_set(first["S"]), "{a, d}")
    check("FOLLOW(A)", format_set(follow["A"]), "{b, $}")
    check("FOLLOW(B)", format_set(follow["B"]), "{c, $}")


def test_sets_output():
    """El formato exacto que debe imprimir --sets."""
    grammar, first, follow, _, _ = analyze(EXAMPLE_2)

    buffer = io.StringIO()
    print_sets(grammar, first, follow, out=lambda line: buffer.write(line + "\n"))

    check(
        "salida de --sets",
        buffer.getvalue(),
        "First(A) = {a, d}\n"
        "First(B) = {b, e}\n"
        "First(S) = {a, d}\n"
        "Follow(A) = {b, $}\n"
        "Follow(B) = {c, $}\n"
        "Follow(S) = {$}\n",
    )


# ----------------------------------------------------------------------
# Item 2: los cuatro casos de la Seccion 2.2.2
# ----------------------------------------------------------------------

EXAMPLE_1 = "3\nS -> S+T T\nT -> T*F F\nF -> (S) i\n"
EXAMPLE_3 = "1\nS -> SS a\n"
ONLY_LL1 = "3\nS -> AaAb BbBa\nA -> e\nB -> e\n"


def test_verdicts():
    check("ejemplo 1 es SLR(1) y no LL(1)", verdict(EXAMPLE_1), "slr1")
    check("ejemplo 2 es LL(1) y SLR(1)", verdict(EXAMPLE_2), "both")
    check("ejemplo 3 no es ninguno", verdict(EXAMPLE_3), "neither")
    check("gramatica LL(1) que no es SLR(1)", verdict(ONLY_LL1), "ll1")


def test_parsers():
    check(
        "ejemplo 1 con SLR(1)",
        accepts(EXAMPLE_1, ["i+i", "(i)", "(i+i)*i)"], "slr1"),
        ["yes", "yes", "no"],
    )
    check(
        "ejemplo 2 con LL(1)",
        accepts(EXAMPLE_2, ["d", "adbc", "a"], "ll1"),
        ["yes", "yes", "no"],
    )
    check(
        "ejemplo 2 con SLR(1) da lo mismo",
        accepts(EXAMPLE_2, ["d", "adbc", "a"], "slr1"),
        ["yes", "yes", "no"],
    )
    check(
        "cadena vacia",
        accepts("2\nS -> aS B\nB -> e\n", ["", "a", "b"], "ll1"),
        ["yes", "yes", "no"],
    )
    check(
        "gramatica LL(1) que no es SLR(1)",
        accepts(ONLY_LL1, ["ab", "ba", "aa", ""], "ll1"),
        ["yes", "yes", "no", "no"],
    )


def test_lr0_collection():
    """La gramatica de expresiones tiene 12 estados, como la Figura 4.31."""
    _, _, _, _, automaton = analyze(EXAMPLE_1)
    check("estados del automata LR(0)", len(automaton.states), 12)
    check("sin conflictos", automaton.conflicts, [])

    _, _, _, _, ambiguous = analyze(EXAMPLE_3)
    check("S -> SS a tiene conflictos", bool(ambiguous.conflicts), True)


# ----------------------------------------------------------------------
# Item 3: la SDD
# ----------------------------------------------------------------------

SDD_GRAMMAR = "5\nS -> N#B\nN -> DR\nR -> DR e\nD -> 0 1 2\nB -> b t\n"


def evaluate_string(string, sdd=None, parser="ll1"):
    """Analiza y evalua una cadena; devuelve (aceptada, evaluacion)."""
    grammar, first, follow, table, automaton = analyze(SDD_GRAMMAR)

    if parser == "ll1":
        accepted, root = ll1.parse(grammar, table, string)
    else:
        accepted, root = slr1.parse(automaton, string)

    if not accepted:
        return False, None

    return True, evaluator.evaluate(root, grammar, sdd or sdd_module.SDD)


def test_sdd_grammar():
    check("la gramatica de la SDD es LL(1) y SLR(1)", verdict(SDD_GRAMMAR), "both")


def test_sdd_values():
    cases = {
        "0#b": 0,          # la cadena mas corta del lenguaje
        "1#b": 1,
        "102#t": 11,       # el ejemplo hecho a mano
        "1011#b": 11,      # el mismo valor en binario
        "210201#t": 586,   # recursion profunda
    }

    for string, expected in cases.items():
        accepted, evaluation = evaluate_string(string)
        value = evaluation.nodes[0].attrs.get("val") if accepted else None
        check(f"valor de '{string}'", value, expected)

    for string in ("102", "#b", "12b", "121#x", ""):
        accepted, _ = evaluate_string(string)
        check(f"'{string}' no pertenece al lenguaje", accepted, False)


def test_sdd_same_with_both_parsers():
    for string in ("0#b", "102#t", "210201#t"):
        _, with_ll1 = evaluate_string(string, parser="ll1")
        _, with_slr1 = evaluate_string(string, parser="slr1")
        check(
            f"los dos parsers dan el mismo valor en '{string}'",
            with_ll1.nodes[0].attrs["val"],
            with_slr1.nodes[0].attrs["val"],
        )


def test_topological_order():
    """La base se evalua antes que el atributo heredado que la usa."""
    _, evaluation = evaluate_string("102#t")
    names = [evaluation.name(instance) for instance in evaluation.order]

    base_of_b = next(n for n in names if n.startswith("B[") and n.endswith(".val"))
    check(
        "B.val se evalua antes que N.base",
        names.index(base_of_b) < names.index("N[1].base"),
        True,
    )
    check("no es circular", evaluation.circular, False)


def test_circular_sdd():
    _, evaluation = evaluate_string("102#t", sdd=sdd_module.CIRCULAR_SDD)
    check("la SDD circular se detecta", evaluation.circular, True)
    check("hay atributos sin evaluar", bool(evaluation.unresolved), True)

    # Con la cadena mas corta no se usa la produccion R -> DR, asi que el
    # ciclo no aparece y la evaluacion sigue funcionando.
    _, short = evaluate_string("0#b", sdd=sdd_module.CIRCULAR_SDD)
    check("sin la produccion circular no hay ciclo", short.circular, False)


# ----------------------------------------------------------------------
# Capa web: el gateway (no necesita Flask, solo traduce a JSON)
# ----------------------------------------------------------------------

def test_gateway_analyze():
    report = gateway.analyze(EXAMPLE_2)

    check("veredicto del ejemplo 2", report["verdict"]["code"], "both")
    check(
        "el gateway da las mismas lineas que --sets",
        report["sets"]["lines"][:3],
        ["First(A) = {a, d}", "First(B) = {b, e}", "First(S) = {a, d}"],
    )
    check("la tabla LL(1) no tiene conflictos", report["ll1"]["conflicts"], [])
    check("el automata LR(0) trae sus estados", len(report["slr1"]["states"]) > 0, True)

    # La primera linea con el numero de no terminales es opcional en la web.
    without_count = gateway.analyze("S -> AB\nA -> aA d\nB -> bBc e")
    check("la gramatica sin el numero da lo mismo", without_count["sets"], report["sets"])


def test_gateway_parse():
    data = gateway.parse(EXAMPLE_2, ["d", "adbc", "a"], "ll1")

    check("parser escogido", data["parser"], "ll1")
    check(
        "respuestas",
        [result["answer"] for result in data["results"]],
        ["yes", "yes", "no"],
    )
    check("la cadena aceptada trae arbol", "tree" in data["results"][1], True)
    check("la rechazada no trae arbol", "tree" in data["results"][2], False)
    check(
        "el rastro dice donde fallo",
        data["results"][2]["trace"][-1]["kind"],
        "error",
    )

    # Pedir un parser que no sirve tiene que avisar, no reventar.
    try:
        gateway.parse(EXAMPLE_1, ["i+i"], "ll1")
        check("pedir LL(1) en una gramatica que no lo es", "no fallo", "GatewayError")
    except gateway.GatewayError:
        check("pedir LL(1) en una gramatica que no lo es", "GatewayError", "GatewayError")

    automatic = gateway.parse(EXAMPLE_1, ["i+i"], "auto")
    check("en automatico escoge el SLR(1)", automatic["parser"], "slr1")


def test_gateway_sdd():
    data = gateway.evaluate_sdd(["102#t", "102"])
    first = data["results"][0]

    check("valor principal", first["main"], {"name": "S.val", "value": "11"})
    check("el grafo trae 22 atributos", len(first["graph"]["nodes"]), 22)
    check("el grafo trae 22 aristas", len(first["graph"]["edges"]), 22)
    check("la cadena mala se rechaza", data["results"][1]["answer"], "no")

    # Todas las aristas van de un nivel a uno mayor: asi se dibujan sin cruces.
    levels = {node["id"]: node["level"] for node in first["graph"]["nodes"]}
    descending = [e for e in first["graph"]["edges"] if levels[e["from"]] >= levels[e["to"]]]
    check("todas las aristas bajan de nivel", descending, [])

    circular = gateway.evaluate_sdd(["102#t"], circular=True)
    check("la SDD circular se reporta", circular["results"][0]["circular"], True)


def test_gateway_serializes():
    """Todo lo que devuelve el gateway tiene que poder volverse JSON."""
    import json

    for payload in (
        gateway.analyze(EXAMPLE_1),
        gateway.parse(EXAMPLE_2, ["adbc"], "auto"),
        gateway.evaluate_sdd(["102#t"]),
    ):
        try:
            json.dumps(payload)
            check("serializa a JSON", True, True)
        except (TypeError, ValueError) as error:
            check("serializa a JSON", str(error), True)


def main():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]

    for test in tests:
        test()

    print(f"{PASSED} comprobaciones correctas, {len(FAILED)} fallidas.")
    for failure in FAILED:
        print("FALLO: " + failure)

    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
