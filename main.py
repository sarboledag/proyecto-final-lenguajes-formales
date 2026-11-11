"""Programa principal de los Items 1 y 2.

Lee una gramatica en el formato de la Seccion 2.2 del enunciado, decide si
es LL(1) y si es SLR(1), y despues analiza las cadenas que reciba.

Uso:
    python main.py [--sets] [--tables] [--trace]

    --sets      imprime FIRST y FOLLOW antes de seguir (lo pide el Item 1).
    --tables    extra: imprime la tabla LL(1), el automata LR(0) y las
                tablas SLR(1). No hace parte de la salida oficial.
    --trace     extra: imprime el analisis paso a paso de cada cadena.

Las cadenas se leen una por linea y una linea vacia termina la lectura. La
cadena vacia se escribe como 'e'. Para cada cadena se imprime 'yes' si la
genera la gramatica y 'no' si no.
"""

import sys

import ll1
import slr1
from grammar import GrammarError, read_grammar
from sets import compute_first, compute_follow, print_sets


def read_line():
    """Siguiente linea de la entrada estandar, o None si ya se acabo."""
    line = sys.stdin.readline()
    if line == "":
        return None
    return line.rstrip("\n").rstrip("\r")


def say(text=""):
    """Imprime y vacia el buffer, porque el programa es interactivo."""
    print(text, flush=True)


def read_strings(parse_string):
    """Lee cadenas hasta una linea vacia y aplica 'parse_string' a cada una.

    La cadena vacia llega como una linea que solo contiene 'e'.
    """
    while True:
        line = read_line()
        if line is None:
            return
        text = line.strip()
        if text == "":
            return
        say("yes" if parse_string("" if text == "e" else text) else "no")


def main(argv):
    show_sets = "--sets" in argv
    show_tables = "--tables" in argv
    show_trace = "--trace" in argv

    try:
        grammar = read_grammar(read_line)
    except GrammarError as error:
        say(f"Error en la gramatica: {error}")
        return 1

    first = compute_first(grammar)
    follow = compute_follow(grammar, first)

    if show_sets:
        print_sets(grammar, first, follow, out=say)

    # Item 2: las dos pruebas.
    table = ll1.build_table(grammar, first, follow)
    grammar_is_ll1, _ = ll1.is_ll1(grammar, first, follow)

    automaton = slr1.SLRAutomaton(grammar, follow)
    grammar_is_slr1 = automaton.is_slr1

    if show_tables:
        say()
        say("Tabla LL(1):")
        ll1.show_table(grammar, table, out=say)
        say()
        say("Automata LR(0):")
        automaton.show_automaton(out=say)
        say()
        say("Tablas ACTION y GOTO:")
        automaton.show_tables(out=say)
        say()

    def parse_with_ll1(text):
        trace = [] if show_trace else None
        accepted, _ = ll1.parse(grammar, table, text, trace=trace)
        if show_trace:
            ll1.show_trace(trace, out=say)
        return accepted

    def parse_with_slr1(text):
        trace = [] if show_trace else None
        accepted, _ = slr1.parse(automaton, text, trace=trace)
        if show_trace:
            slr1.show_trace(trace, out=say)
        return accepted

    # Seccion 2.2.2: los cuatro casos de salida.
    if grammar_is_ll1 and grammar_is_slr1:
        while True:
            say("Select a parser (T: for LL(1), B: for SLR(1), Q: quit):")
            line = read_line()
            if line is None:
                return 0

            choice = line.strip()
            if choice == "Q":
                return 0
            if choice == "T":
                read_strings(parse_with_ll1)
            elif choice == "B":
                read_strings(parse_with_slr1)

    elif grammar_is_ll1:
        say("Grammar is LL(1).")
        read_strings(parse_with_ll1)

    elif grammar_is_slr1:
        say("Grammar is SLR(1).")
        read_strings(parse_with_slr1)

    else:
        say("Grammar is neither LL(1) nor SLR(1).")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
