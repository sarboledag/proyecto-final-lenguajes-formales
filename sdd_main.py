"""Programa principal del Item 3: evaluacion de la SDD.

Lee la gramatica del archivo sdd_grammar.txt (formato de la Seccion 2.2),
analiza cada cadena con uno de los parsers del Item 2, construye el arbol,
arma el grafo de dependencias y evalua los atributos en un orden topologico.

Uso:
    python sdd_main.py [gramatica] [--slr] [--circular] [--sdd] [--graph] [--step]

    gramatica    archivo de la gramatica (por defecto sdd_grammar.txt).
    --slr        usa el parser SLR(1); por defecto usa el LL(1).
    --circular   usa la version circular de la SDD (prueba del Paso 6).
    --sdd        imprime la tabla de atributos y las reglas semanticas.
    --graph      imprime tambien las aristas del grafo de dependencias.
    --step       muestra la evaluacion atributo por atributo; si la entrada
                 es una terminal, espera un Enter en cada paso.

Las cadenas se leen una por linea y una linea vacia termina la lectura.
Para cada cadena se imprime 'no' si no pertenece al lenguaje; si pertenece,
se imprime el arbol anotado, el orden de evaluacion y el valor del atributo
principal del simbolo inicial.
"""

import sys

import evaluator
import ll1
import sdd as sdd_module
import slr1
from grammar import GrammarError, read_grammar
from sets import compute_first, compute_follow
from tree import show_tree


def say(text=""):
    print(text, flush=True)


def read_line():
    line = sys.stdin.readline()
    if line == "":
        return None
    return line.rstrip("\n").rstrip("\r")


def load_grammar(path):
    with open(path, encoding="utf-8") as handle:
        lines = iter(handle.read().splitlines())

        def next_line():
            return next(lines, None)

        return read_grammar(next_line)


def make_parser(grammar, use_slr):
    """Devuelve una funcion que analiza una cadena y devuelve la raiz del arbol.

    Se usa el parser del Item 2 que pida el usuario, siempre que la
    gramatica cumpla la condicion correspondiente.
    """
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)

    if use_slr:
        automaton = slr1.SLRAutomaton(grammar, follow)
        if not automaton.is_slr1:
            raise SystemExit("La gramatica de la SDD no es SLR(1).")
        say("Analizando con el parser SLR(1).")
        return lambda text: slr1.parse(automaton, text)

    table = ll1.build_table(grammar, first, follow)
    is_ll1, reasons = ll1.is_ll1(grammar, first, follow)
    if not is_ll1:
        raise SystemExit("La gramatica de la SDD no es LL(1): " + " ".join(reasons))
    say("Analizando con el parser LL(1).")
    return lambda text: ll1.parse(grammar, table, text)


def show_evaluation_order(evaluation, step, out=say):
    """Imprime el orden de evaluacion que se uso."""
    out("Orden de evaluacion:")

    interactive = step and sys.stdin.isatty()
    for position, instance in enumerate(evaluation.order, start=1):
        value = evaluation.value(instance)
        out(f"    {position:>3}. {evaluation.name(instance)} = {value!r}")
        if interactive:
            input()


def process(text, grammar, parse, sdd, options):
    """Analiza y evalua una cadena, e imprime todo lo que pide el Paso 5."""
    accepted, root = parse(text)

    if not accepted:
        say("no")
        return

    try:
        evaluation = evaluator.evaluate(root, grammar, sdd)
    except evaluator.SDDError as error:
        say(f"Error en la SDD: {error}")
        return

    if evaluation.circular:
        say("La SDD es circular: el grafo de dependencias tiene un ciclo.")
        say("Atributos que quedaron sin poder evaluarse:")
        for instance in evaluation.unresolved:
            say(f"    {evaluation.name(instance)}")
        return

    say("Arbol anotado:")
    show_tree(root, out=lambda line: say("  " + line), annotate=evaluator.annotate)

    if options["graph"]:
        say("Grafo de dependencias:")
        evaluator.show_graph(evaluation, out=say)

    show_evaluation_order(evaluation, options["step"])

    symbol, attribute = sdd["main"]
    say(f"{symbol}.{attribute} = {root.attrs.get(attribute)}")


def main(argv):
    options = {
        "slr": "--slr" in argv,
        "circular": "--circular" in argv,
        "sdd": "--sdd" in argv,
        "graph": "--graph" in argv,
        "step": "--step" in argv,
    }

    paths = [argument for argument in argv if not argument.startswith("--")]
    path = paths[0] if paths else "sdd_grammar.txt"

    try:
        grammar = load_grammar(path)
    except (OSError, GrammarError) as error:
        say(f"No se pudo leer la gramatica: {error}")
        return 1

    sdd = sdd_module.CIRCULAR_SDD if options["circular"] else sdd_module.SDD
    say(f"SDD: {sdd['name']}")

    if options["sdd"]:
        say()
        say("Atributos:")
        sdd_module.show_attributes(out=say)
        say()
        say("Reglas semanticas:")
        sdd_module.show_rules(sdd, out=say)
        say()

    parse = make_parser(grammar, options["slr"])

    while True:
        line = read_line()
        if line is None:
            return 0

        text = line.strip()
        if text == "":
            return 0

        say()
        say(f"Cadena: {text}")
        process("" if text == "e" else text, grammar, parse, sdd, options)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
