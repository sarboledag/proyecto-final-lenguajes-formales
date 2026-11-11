"""Item 3: la definicion dirigida por la sintaxis, guardada como datos.

El enunciado exige que la SDD sea *datos y no codigo*: el evaluador de
evaluator.py no sabe nada de esta gramatica en particular, solo recorre las
reglas que estan aqui. Cambiar la SDD es cambiar unicamente este archivo.

La gramatica elegida (sdd_grammar.txt) describe un numeral escrito con sus
digitos, seguido de '#' y de una letra que dice en que base hay que leerlo:

    S -> N#B        B -> b   (base 2)
    N -> DR         B -> t   (base 3)
    R -> DR | e
    D -> 0 | 1 | 2

Por ejemplo '102#t' es el numeral 102 en base 3, o sea 11.

Lo interesante de esta SDD es que la base aparece al FINAL de la cadena,
pero se necesita desde el primer digito: en la produccion S -> N#B el
atributo heredado N.base depende de B.val, que esta a la derecha de N. Por
eso la SDD no es ni S-atribuida ni L-atribuida, y una evaluacion recursiva
de izquierda a derecha no sirve: hay que usar el grafo de dependencias y un
orden topologico, que es justo el metodo general que pide el enunciado.

Posiciones dentro de una produccion A -> X1 X2 ... Xn:
    0 es la cabeza A, 1 es X1, 2 es X2, y asi.
"""


class SemanticRule:
    """Una regla semantica de una produccion.

    'target' es el atributo que la regla define, '(posicion, nombre)'.
    'deps' son los atributos que usa, en el mismo orden en que la funcion
    'f' los va a recibir. 'text' es la regla escrita como en el libro, solo
    para imprimirla en el informe.
    """

    __slots__ = ("target", "deps", "f", "text")

    def __init__(self, target, deps, f, text):
        self.target = target
        self.deps = deps
        self.f = f
        self.text = text

    def __repr__(self):
        return f"SemanticRule({self.text})"


def _digit(lexval):
    """Valor numerico del caracter de un digito (su lexval)."""
    return ord(lexval) - ord("0")


def _base(lexval):
    """Base que indica la letra final: 'b' es binario y 't' es ternario."""
    return 2 if lexval == "b" else 3


# ----------------------------------------------------------------------
# Tabla de atributos (Paso 2.1 del enunciado)
# ----------------------------------------------------------------------
# (simbolo, atributo, tipo de atributo, tipo de dato, significado)
ATTRIBUTES = [
    ("S", "val", "sintetizado", "entero", "valor del numeral completo"),
    ("N", "base", "heredado", "entero", "base en la que hay que leer los digitos"),
    ("N", "acc", "heredado", "entero", "valor acumulado antes del primer digito"),
    ("N", "val", "sintetizado", "entero", "valor de toda la lista de digitos"),
    ("R", "base", "heredado", "entero", "base en la que hay que leer los digitos"),
    ("R", "acc", "heredado", "entero", "valor de los digitos ya leidos"),
    ("R", "val", "sintetizado", "entero", "valor acumulado al terminar la lista"),
    ("D", "val", "sintetizado", "entero", "valor del digito"),
    ("B", "val", "sintetizado", "entero", "base que indica la letra final"),
    ("terminal", "lexval", "sintetizado", "caracter", "el caracter mismo"),
]


# ----------------------------------------------------------------------
# Reglas semanticas (Paso 2.2 del enunciado, formato de la Figura 5.1)
# ----------------------------------------------------------------------
RULES = {
    ("S", ("N", "#", "B")): [
        SemanticRule((1, "base"), [(3, "val")], lambda v: v[0], "N.base = B.val"),
        SemanticRule((1, "acc"), [], lambda v: 0, "N.acc = 0"),
        SemanticRule((0, "val"), [(1, "val")], lambda v: v[0], "S.val = N.val"),
    ],
    ("N", ("D", "R")): [
        SemanticRule((2, "base"), [(0, "base")], lambda v: v[0], "R.base = N.base"),
        SemanticRule(
            (2, "acc"),
            [(0, "acc"), (0, "base"), (1, "val")],
            lambda v: v[0] * v[1] + v[2],
            "R.acc = N.acc * N.base + D.val",
        ),
        SemanticRule((0, "val"), [(2, "val")], lambda v: v[0], "N.val = R.val"),
    ],
    ("R", ("D", "R")): [
        SemanticRule((2, "base"), [(0, "base")], lambda v: v[0], "R1.base = R.base"),
        SemanticRule(
            (2, "acc"),
            [(0, "acc"), (0, "base"), (1, "val")],
            lambda v: v[0] * v[1] + v[2],
            "R1.acc = R.acc * R.base + D.val",
        ),
        SemanticRule((0, "val"), [(2, "val")], lambda v: v[0], "R.val = R1.val"),
    ],
    ("R", ()): [
        SemanticRule((0, "val"), [(0, "acc")], lambda v: v[0], "R.val = R.acc"),
    ],
    ("D", ("0",)): [
        SemanticRule((0, "val"), [(1, "lexval")], lambda v: _digit(v[0]), "D.val = digito(0.lexval)"),
    ],
    ("D", ("1",)): [
        SemanticRule((0, "val"), [(1, "lexval")], lambda v: _digit(v[0]), "D.val = digito(1.lexval)"),
    ],
    ("D", ("2",)): [
        SemanticRule((0, "val"), [(1, "lexval")], lambda v: _digit(v[0]), "D.val = digito(2.lexval)"),
    ],
    ("B", ("b",)): [
        SemanticRule((0, "val"), [(1, "lexval")], lambda v: _base(v[0]), "B.val = base(b.lexval)"),
    ],
    ("B", ("t",)): [
        SemanticRule((0, "val"), [(1, "lexval")], lambda v: _base(v[0]), "B.val = base(t.lexval)"),
    ],
}


SDD = {
    "name": "Numeral con la base al final",
    "grammar": "sdd_grammar.txt",
    "main": ("S", "val"),
    "attributes": ATTRIBUTES,
    "rules": RULES,
}


# ----------------------------------------------------------------------
# Version circular, para la prueba del Paso 6 del enunciado
# ----------------------------------------------------------------------
# Se cambia una sola regla de R -> DR: en vez de acumular hacia la derecha,
# R1.acc pasa a depender de R.val. Como R.val depende de R1.val y R1.val
# depende de R1.acc, el grafo queda con el ciclo
#     R.val -> R1.acc -> R1.val -> R.val
CIRCULAR_RULES = dict(RULES)
CIRCULAR_RULES[("R", ("D", "R"))] = [
    SemanticRule((2, "base"), [(0, "base")], lambda v: v[0], "R1.base = R.base"),
    SemanticRule((2, "acc"), [(0, "val")], lambda v: v[0], "R1.acc = R.val"),
    SemanticRule((0, "val"), [(2, "val")], lambda v: v[0], "R.val = R1.val"),
]

CIRCULAR_SDD = dict(SDD, name="Version circular (prueba del Paso 6)", rules=CIRCULAR_RULES)


def show_attributes(out=print):
    """Imprime la tabla de atributos del Paso 2."""
    out(f"{'SIMBOLO':<10}{'ATRIBUTO':<10}{'TIPO':<14}{'DATO':<10}SIGNIFICADO")
    for symbol, name, kind, datatype, meaning in ATTRIBUTES:
        out(f"{symbol:<10}{name:<10}{kind:<14}{datatype:<10}{meaning}")


def show_rules(sdd, out=print):
    """Imprime las reglas semanticas en el formato de la Figura 5.1."""
    out(f"{'PRODUCCION':<16}REGLAS SEMANTICAS")
    for (head, body), rules in sdd["rules"].items():
        production = f"{head} -> {''.join(body) if body else 'e'}"
        out(f"{production:<16}" + ";  ".join(rule.text for rule in rules))
