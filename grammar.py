"""Lectura y representacion de una gramatica libre de contexto.

El formato de entrada es el de la Seccion 2.2 del enunciado:

    n                       (numero de no terminales)
    S -> AB                 (un no terminal por linea, con sus alternativas
    A -> aA d                separadas por espacios en blanco)
    B -> bBc e

Convenciones del enunciado:
  * 'S' es siempre el simbolo inicial.
  * Los no terminales son letras mayusculas.
  * Los terminales son un unico caracter que no es mayuscula.
  * 'e' representa la cadena vacia y no puede ser terminal.
  * '$' es el marcador de fin y no puede ser terminal; lo agrega el programa.

Este modulo no sabe nada de parsers ni de tablas: solo guarda la gramatica
y responde preguntas basicas sobre ella.
"""

EPSILON = "e"
END = "$"


class GrammarError(Exception):
    """La gramatica recibida no respeta el formato de la Seccion 2.2."""


def is_nonterminal(symbol):
    """Un simbolo es no terminal si es una unica letra mayuscula."""
    return len(symbol) == 1 and symbol.isupper()


class Grammar:
    """Una gramatica libre de contexto.

    Las producciones se guardan en una lista de pares (cabeza, cuerpo),
    donde el cuerpo es una tupla de simbolos. El cuerpo vacio () representa
    la produccion A -> epsilon. El orden de la lista es el orden de lectura,
    y ese indice es el que usan las tablas LL(1) y SLR(1) para referirse a
    una produccion.
    """

    def __init__(self, productions, start="S"):
        if not productions:
            raise GrammarError("La gramatica no tiene producciones.")

        self.productions = list(productions)
        self.start = start
        self.nonterminals = sorted({head for head, _ in self.productions})

        if start not in self.nonterminals:
            raise GrammarError(f"El simbolo inicial '{start}' no tiene producciones.")

        terminals = set()
        for _, body in self.productions:
            for symbol in body:
                if not is_nonterminal(symbol):
                    terminals.add(symbol)
        self.terminals = sorted(terminals)

        self._check_symbols()

        # Indice cabeza -> indices de sus producciones, para no recorrer la
        # lista completa cada vez que se piden las alternativas de un A.
        self._by_head = {A: [] for A in self.nonterminals}
        for i, (head, _) in enumerate(self.productions):
            self._by_head[head].append(i)

    def _check_symbols(self):
        """Verifica que todo no terminal usado tenga al menos una produccion."""
        for head, body in self.productions:
            for symbol in body:
                if is_nonterminal(symbol) and symbol not in self.nonterminals:
                    raise GrammarError(
                        f"El no terminal '{symbol}' se usa en '{head} -> "
                        f"{''.join(body)}' pero no tiene producciones."
                    )

    def symbols(self):
        """Todos los simbolos de la gramatica: no terminales y terminales."""
        return self.nonterminals + self.terminals

    def productions_for(self, head):
        """Indices de las producciones cuya cabeza es 'head'."""
        return self._by_head.get(head, [])

    def is_nonterminal(self, symbol):
        return is_nonterminal(symbol)

    def show_production(self, index):
        """Texto legible de una produccion, con 'e' para la cadena vacia."""
        head, body = self.productions[index]
        return f"{head} -> {''.join(body) if body else EPSILON}"

    def __len__(self):
        return len(self.productions)


def parse_line(line):
    """Pasa una linea 'A -> alt1 alt2 ...' a una lista de producciones.

    Devuelve pares (cabeza, cuerpo). La alternativa 'e' se traduce al cuerpo
    vacio (), que es como se representa epsilon en todo el proyecto.
    """
    if "->" not in line:
        raise GrammarError(f"La linea '{line}' no tiene el separador '->'.")

    head, _, rest = line.partition("->")
    head = head.strip()

    if not is_nonterminal(head):
        raise GrammarError(f"'{head}' no es un no terminal valido (una mayuscula).")

    alternatives = rest.split()
    if not alternatives:
        raise GrammarError(f"El no terminal '{head}' no tiene alternativas.")

    productions = []
    for alternative in alternatives:
        if alternative == EPSILON:
            productions.append((head, ()))
            continue

        for symbol in alternative:
            if symbol == EPSILON:
                raise GrammarError(
                    f"'{EPSILON}' solo puede aparecer como alternativa sola, "
                    f"pero esta dentro de '{alternative}'."
                )
            if symbol == END:
                raise GrammarError(f"'{END}' no puede ser un simbolo de la gramatica.")

        productions.append((head, tuple(alternative)))

    return productions


def read_grammar(read_line):
    """Lee la gramatica usando la funcion 'read_line' que se le pase.

    'read_line' devuelve la siguiente linea de la entrada (sin el salto de
    linea) o None si ya no hay mas. Se separa asi para poder leer igual de
    stdin, de un archivo o de una lista en las pruebas.
    """
    first = read_line()
    while first is not None and not first.strip():
        first = read_line()

    if first is None:
        raise GrammarError("No se recibio el numero de no terminales.")

    try:
        count = int(first.strip())
    except ValueError:
        raise GrammarError(f"'{first.strip()}' no es un numero de no terminales.")

    if count <= 0:
        raise GrammarError("El numero de no terminales debe ser mayor que cero.")

    productions = []
    heads = set()

    for _ in range(count):
        line = read_line()
        while line is not None and not line.strip():
            line = read_line()
        if line is None:
            raise GrammarError("Faltan lineas de producciones.")

        new = parse_line(line.strip())
        head = new[0][0]
        if head in heads:
            raise GrammarError(f"El no terminal '{head}' aparece en dos lineas.")
        heads.add(head)
        productions.extend(new)

    return Grammar(productions)


def read_grammar_from_text(text):
    """Atajo para leer una gramatica que ya esta en memoria como texto."""
    lines = iter(text.splitlines())

    def read_line():
        return next(lines, None)

    return read_grammar(read_line)
