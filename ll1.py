"""Item 2, LL(1): prueba, tabla predictiva y parser dirigido por tabla.

Se siguen las Secciones 4.4.3 y 4.4.4 del libro:
  * la condicion de LL(1) del comienzo de la Seccion 4.4.3,
  * el Algoritmo 4.31, que construye la tabla M a partir de FIRST y FOLLOW,
  * el Algoritmo 4.34, el parser predictivo no recursivo con pila.

La gramatica NO se transforma antes de la prueba: si es recursiva por la
izquierda, simplemente no pasa la condicion y se reporta que no es LL(1).
"""

from grammar import END, EPSILON
from sets import first_of_string
from tree import Node


def build_table(grammar, first, follow):
    """Tabla predictiva M[A, a] (Algoritmo 4.31).

    Para cada produccion A -> alfa:
      1. Para cada terminal a de FIRST(alfa), M[A, a] recibe A -> alfa.
      2. Si epsilon esta en FIRST(alfa), para cada b de FOLLOW(A) (incluido
         $ si pertenece) M[A, b] recibe A -> alfa.

    El valor de cada celda es una lista de indices de produccion. Si alguna
    lista queda con mas de un elemento hay un conflicto y la gramatica no es
    LL(1).
    """
    table = {}

    for index, (head, body) in enumerate(grammar.productions):
        first_body = first_of_string(body, first)

        for terminal in first_body - {EPSILON}:
            table.setdefault((head, terminal), []).append(index)

        if EPSILON in first_body:
            for terminal in follow[head]:
                table.setdefault((head, terminal), []).append(index)

    return table


def table_conflicts(table):
    """Celdas de la tabla con mas de una produccion."""
    return sorted(
        (head, terminal, indices)
        for (head, terminal), indices in table.items()
        if len(indices) > 1
    )


def is_ll1(grammar, first, follow):
    """Condicion de LL(1) del comienzo de la Seccion 4.4.3.

    Para cada par de producciones distintas A -> alfa | beta:
      1. No hay un terminal a tal que alfa y beta deriven cadenas que
         empiecen por a.
      2. A lo sumo una de las dos deriva epsilon.
      3. Si beta deriva epsilon, alfa no deriva ninguna cadena que empiece
         por un terminal de FOLLOW(A), y simetricamente.

    Devuelve (True/False, lista de motivos). Los motivos no se imprimen en
    la salida oficial, pero sirven para el informe y para depurar.
    """
    reasons = []

    for head in grammar.nonterminals:
        indices = grammar.productions_for(head)

        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                a_index, b_index = indices[i], indices[j]
                alpha = grammar.productions[a_index][1]
                beta = grammar.productions[b_index][1]

                first_alpha = first_of_string(alpha, first)
                first_beta = first_of_string(beta, first)

                # Condicion 1.
                common = (first_alpha & first_beta) - {EPSILON}
                if common:
                    reasons.append(
                        f"FIRST de '{grammar.show_production(a_index)}' y de "
                        f"'{grammar.show_production(b_index)}' comparten "
                        f"{sorted(common)}."
                    )

                # Condicion 2.
                if EPSILON in first_alpha and EPSILON in first_beta:
                    reasons.append(
                        f"'{grammar.show_production(a_index)}' y "
                        f"'{grammar.show_production(b_index)}' derivan ambas "
                        f"epsilon."
                    )

                # Condicion 3, en los dos sentidos.
                for nullable, other, nullable_index, other_index in (
                    (first_beta, first_alpha, b_index, a_index),
                    (first_alpha, first_beta, a_index, b_index),
                ):
                    if EPSILON in nullable:
                        clash = (other - {EPSILON}) & follow[head]
                        if clash:
                            reasons.append(
                                f"'{grammar.show_production(nullable_index)}' "
                                f"deriva epsilon y "
                                f"'{grammar.show_production(other_index)}' "
                                f"empieza por {sorted(clash)}, que esta en "
                                f"FOLLOW({head})."
                            )

    return not reasons, reasons


def show_table(grammar, table, out=print):
    """Imprime la tabla M en texto, para el informe (Figura 4.17 del libro)."""
    columns = grammar.terminals + [END]

    cells = {}
    for head in grammar.nonterminals:
        for terminal in columns:
            indices = table.get((head, terminal), [])
            cells[(head, terminal)] = " | ".join(
                grammar.show_production(i) for i in indices
            )

    width = max([len(c) for c in cells.values()] + [len(c) for c in columns]) + 2

    out("".ljust(4) + "".join(c.center(width) for c in columns))
    for head in grammar.nonterminals:
        row = [head.ljust(4)]
        for terminal in columns:
            row.append(cells[(head, terminal)].center(width))
        out("".join(row).rstrip())


def parse(grammar, table, string, trace=None):
    """Parser predictivo no recursivo (Algoritmo 4.34).

    Se empuja $ y el simbolo inicial, y en cada paso se mira la cima de la
    pila X y el simbolo de entrada a:
      * si X es el terminal a, se saca X y se avanza en la entrada;
      * si X es un terminal distinto, o M[X, a] esta vacia, es error;
      * si M[X, a] = X -> Y1 ... Yk, se saca X y se empujan Yk ... Y1.

    En paralelo a la pila de simbolos se lleva una pila de nodos, para
    construir el arbol de analisis que necesita el Item 3.

    Devuelve (True, raiz) si la cadena pertenece al lenguaje y
    (False, None) si no.
    """
    root = Node(grammar.start)

    stack = [(END, None), (grammar.start, root)]
    input_symbols = list(string) + [END]
    position = 0

    def fail(reason):
        """Deja el motivo del rechazo en el rastro, si se pidio rastro."""
        if trace is not None:
            trace.append(
                ("error", _stack_text(stack), _rest(input_symbols, position), reason)
            )
        return False, None

    while stack:
        symbol, node = stack[-1]
        lookahead = input_symbols[position]

        if symbol == END:
            if lookahead == END:
                if trace is not None:
                    trace.append(("accept", _stack_text(stack), _rest(input_symbols, position), ""))
                return True, root
            return fail(f"la pila ya solo tiene $ pero queda entrada por leer")

        if not grammar.is_nonterminal(symbol):
            if symbol == lookahead:
                if trace is not None:
                    trace.append(
                        ("match", _stack_text(stack), _rest(input_symbols, position), symbol)
                    )
                node.attrs["lexval"] = symbol
                stack.pop()
                position += 1
                continue
            return fail(f"se esperaba '{symbol}' y llego '{lookahead}'")

        indices = table.get((symbol, lookahead), [])
        if not indices:
            return fail(f"M[{symbol}, {lookahead}] esta vacia")

        index = indices[0]  # si hay conflicto la gramatica ya se rechazo antes
        _, body = grammar.productions[index]

        if trace is not None:
            trace.append(
                (
                    "output",
                    _stack_text(stack),
                    _rest(input_symbols, position),
                    grammar.show_production(index),
                )
            )

        node.production = index
        node.children = [Node(child) for child in body]

        stack.pop()
        for child_symbol, child_node in reversed(list(zip(body, node.children))):
            stack.append((child_symbol, child_node))

    return False, None


def _stack_text(stack):
    """Contenido de la pila de abajo hacia arriba, como en el libro."""
    return "".join(symbol for symbol, _ in stack)


def _rest(input_symbols, position):
    return "".join(input_symbols[position:])


def show_trace(trace, out=print):
    """Imprime el rastro del analisis en tres columnas (pila, entrada, salida)."""
    out(f"{'STACK':<24}{'INPUT':<16}ACTION")
    for kind, stack, rest, detail in trace:
        if kind == "output":
            action = f"output {detail}"
        elif kind == "match":
            action = f"match {detail}"
        elif kind == "error":
            action = f"error: {detail}"
        else:
            action = "accept"
        out(f"{stack:<24}{rest:<16}{action}")
