"""Item 1: conjuntos FIRST y FOLLOW.

Se sigue la Seccion 4.4.2 de Aho et al., Compilers: Principles, Techniques,
and Tools (2nd Edition). Las dos funciones se calculan con el metodo de
punto fijo que describe el libro: se aplican las reglas una y otra vez sobre
todos los simbolos hasta que ninguna de las dos familias de conjuntos cambia.

Estructuras de datos: un dict {simbolo: set de terminales}. Epsilon se guarda
dentro del conjunto como la cadena 'e' y el marcador de fin como '$', igual
que en la notacion del enunciado.
"""

from grammar import END, EPSILON, is_nonterminal


def compute_first(grammar):
    """FIRST(X) para todo simbolo X de la gramatica (Seccion 4.4.2).

    Reglas del libro:
      1. Si X es terminal, FIRST(X) = {X}.
      2. Si X -> epsilon es una produccion, se agrega epsilon a FIRST(X).
      3. Si X -> Y1 Y2 ... Yk, se agrega a FIRST(X) todo lo que este en
         FIRST(Yi) menos epsilon, siempre que epsilon este en FIRST(Yj) para
         todo j < i. Si epsilon esta en FIRST(Yj) para todo j, se agrega
         epsilon a FIRST(X).
    """
    first = {terminal: {terminal} for terminal in grammar.terminals}
    for nonterminal in grammar.nonterminals:
        first[nonterminal] = set()

    changed = True
    while changed:
        changed = False

        for head, body in grammar.productions:
            before = len(first[head])

            if not body:
                # Regla 2: la produccion es X -> epsilon.
                first[head].add(EPSILON)
            else:
                # Regla 3: se recorre el cuerpo mientras los simbolos
                # anteriores puedan desaparecer.
                all_nullable = True
                for symbol in body:
                    first[head] |= first[symbol] - {EPSILON}
                    if EPSILON not in first[symbol]:
                        all_nullable = False
                        break
                if all_nullable:
                    first[head].add(EPSILON)

            if len(first[head]) != before:
                changed = True

    return first


def first_of_string(symbols, first):
    """FIRST de una cadena X1 X2 ... Xn (extension de la Seccion 4.4.2).

    Hace falta para construir la tabla LL(1), donde se necesita FIRST del
    cuerpo completo de cada produccion y no solo de un simbolo. La cadena
    vacia tiene FIRST = {epsilon}.
    """
    result = set()

    for symbol in symbols:
        result |= first[symbol] - {EPSILON}
        if EPSILON not in first[symbol]:
            return result

    # Si se llego hasta el final, todos los simbolos derivan epsilon.
    result.add(EPSILON)
    return result


def compute_follow(grammar, first):
    """FOLLOW(A) para todo no terminal A (Seccion 4.4.2).

    Reglas del libro:
      1. $ esta en FOLLOW(S), con S el simbolo inicial.
      2. Si A -> alfa B beta, todo FIRST(beta) menos epsilon esta en
         FOLLOW(B).
      3. Si A -> alfa B, o A -> alfa B beta con epsilon en FIRST(beta),
         todo FOLLOW(A) esta en FOLLOW(B).
    """
    follow = {nonterminal: set() for nonterminal in grammar.nonterminals}
    follow[grammar.start].add(END)  # Regla 1

    changed = True
    while changed:
        changed = False

        for head, body in grammar.productions:
            for i, symbol in enumerate(body):
                if not is_nonterminal(symbol):
                    continue

                before = len(follow[symbol])
                rest = body[i + 1:]
                first_rest = first_of_string(rest, first)

                # Regla 2.
                follow[symbol] |= first_rest - {EPSILON}

                # Regla 3: beta puede desaparecer (o no existe).
                if EPSILON in first_rest:
                    follow[symbol] |= follow[head]

                if len(follow[symbol]) != before:
                    changed = True

    return follow


def format_set(symbols):
    """Da el texto '{a, d, e, $}' que pide el enunciado.

    Dentro de las llaves van primero los terminales en orden ASCII, luego
    'e' si epsilon pertenece al conjunto y por ultimo '$' si el marcador de
    fin pertenece al conjunto.
    """
    terminals = sorted(s for s in symbols if s not in (EPSILON, END))

    if EPSILON in symbols:
        terminals.append(EPSILON)
    if END in symbols:
        terminals.append(END)

    return "{" + ", ".join(terminals) + "}"


def print_sets(grammar, first, follow, out=print):
    """Imprime los conjuntos en el formato exacto del argumento --sets.

    Una linea por no terminal, en orden alfabetico, primero todos los
    First(A) y despues todos los Follow(A).
    """
    for nonterminal in grammar.nonterminals:
        out(f"First({nonterminal}) = {format_set(first[nonterminal])}")

    for nonterminal in grammar.nonterminals:
        out(f"Follow({nonterminal}) = {format_set(follow[nonterminal])}")
