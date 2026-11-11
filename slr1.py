"""Item 2, SLR(1): automata LR(0), tablas ACTION/GOTO y parser LR.

Se siguen las Secciones 4.6.2, 4.6.3 y 4.6.4 del libro:
  * CLOSURE(I) y GOTO(I, X) de la Seccion 4.6.2 (Figura 4.32),
  * la coleccion canonica de conjuntos de items LR(0) (Figura 4.33),
  * el Algoritmo 4.46, que construye ACTION y GOTO usando FOLLOW,
  * el Algoritmo 4.44 (Seccion 4.6.3), el parser LR dirigido por tabla.

La gramatica se aumenta con un nuevo simbolo inicial S' -> S, como exige el
libro. Un item se representa como el par (indice de produccion, posicion del
punto) y un estado como el frozenset de sus items, de modo que dos estados
con los mismos items son el mismo estado.
"""

from grammar import END, is_nonterminal
from tree import Node

AUGMENTED_START = "S'"

SHIFT = "s"
REDUCE = "r"
ACCEPT = "acc"


class SLRAutomaton:
    """Automata LR(0) y tablas SLR(1) de una gramatica."""

    def __init__(self, grammar, follow):
        self.grammar = grammar
        self.follow = follow

        # Gramatica aumentada: la produccion 0 es siempre S' -> S.
        self.productions = [(AUGMENTED_START, (grammar.start,))]
        self.productions.extend(grammar.productions)

        self.states = []        # lista de frozenset de items
        self.goto_table = {}    # (estado, simbolo) -> estado
        self.action = {}        # (estado, terminal) -> (tipo, valor)
        self.conflicts = []

        self._build_collection()
        self._build_tables()

    # ------------------------------------------------------------------
    # Seccion 4.6.2: items LR(0), CLOSURE y GOTO
    # ------------------------------------------------------------------

    def closure(self, items):
        """CLOSURE(I): si A -> alfa . B beta esta en I, se agregan los
        items B -> . gamma de todas las producciones de B, hasta que no se
        pueda agregar nada mas.
        """
        result = set(items)
        pending = list(items)

        while pending:
            production, dot = pending.pop()
            body = self.productions[production][1]

            if dot >= len(body):
                continue

            symbol = body[dot]
            if not is_nonterminal(symbol):
                continue

            for index, (head, _) in enumerate(self.productions):
                if head == symbol and (index, 0) not in result:
                    result.add((index, 0))
                    pending.append((index, 0))

        return frozenset(result)

    def goto(self, items, symbol):
        """GOTO(I, X): cierre de los items de I con el punto corrido sobre X."""
        moved = set()

        for production, dot in items:
            body = self.productions[production][1]
            if dot < len(body) and body[dot] == symbol:
                moved.add((production, dot + 1))

        return self.closure(moved) if moved else frozenset()

    def _build_collection(self):
        """Coleccion canonica de conjuntos de items LR(0) (Figura 4.33)."""
        initial = self.closure({(0, 0)})
        self.states = [initial]
        index_of = {initial: 0}

        pending = [initial]
        while pending:
            items = pending.pop(0)
            source = index_of[items]

            for symbol in self.grammar.symbols():
                target = self.goto(items, symbol)
                if not target:
                    continue

                if target not in index_of:
                    index_of[target] = len(self.states)
                    self.states.append(target)
                    pending.append(target)

                self.goto_table[(source, symbol)] = index_of[target]

    # ------------------------------------------------------------------
    # Seccion 4.6.4: tablas ACTION y GOTO
    # ------------------------------------------------------------------

    def _set_action(self, state, terminal, entry):
        """Escribe una celda de ACTION y registra el conflicto si ya estaba
        ocupada con una accion distinta."""
        current = self.action.get((state, terminal))

        if current is not None and current != entry:
            kinds = {current[0], entry[0]}
            kind = "shift/reduce" if kinds == {SHIFT, REDUCE} else "reduce/reduce"
            self.conflicts.append(
                f"Conflicto {kind} en el estado {state} con '{terminal}': "
                f"{self._show_action(current)} contra {self._show_action(entry)}."
            )
            return

        self.action[(state, terminal)] = entry

    def _build_tables(self):
        """Algoritmo 4.46.

          1. Si [A -> alfa . a beta] esta en Ii y GOTO(Ii, a) = Ij, entonces
             ACTION[i, a] = shift j.
          2. Si [A -> alfa .] esta en Ii y A no es S', entonces para todo a
             de FOLLOW(A), ACTION[i, a] = reduce A -> alfa.
          3. Si [S' -> S .] esta en Ii, entonces ACTION[i, $] = accept.

        La gramatica es SLR(1) si y solo si ninguna celda queda con dos
        acciones distintas.
        """
        for state, items in enumerate(self.states):
            for production, dot in items:
                head, body = self.productions[production]

                if dot < len(body):
                    symbol = body[dot]
                    if not is_nonterminal(symbol):
                        target = self.goto_table.get((state, symbol))
                        if target is not None:
                            self._set_action(state, symbol, (SHIFT, target))
                    continue

                # El punto esta al final del cuerpo.
                if head == AUGMENTED_START:
                    self._set_action(state, END, (ACCEPT, None))
                else:
                    for terminal in self.follow[head]:
                        self._set_action(state, terminal, (REDUCE, production))

    @property
    def is_slr1(self):
        return not self.conflicts

    # ------------------------------------------------------------------
    # Presentacion (para el informe)
    # ------------------------------------------------------------------

    def show_production(self, index):
        head, body = self.productions[index]
        return f"{head} -> {''.join(body) if body else 'e'}"

    def show_item(self, item):
        production, dot = item
        head, body = self.productions[production]
        marked = list(body)
        marked.insert(dot, ".")
        return f"{head} -> {''.join(marked)}"

    def _show_action(self, entry, short=False):
        kind, value = entry
        if kind == SHIFT:
            return f"s{value}"
        if kind == REDUCE:
            return f"r{value}" if short else f"r{value} ({self.show_production(value)})"
        return "acc"

    def show_automaton(self, out=print):
        """Imprime la coleccion canonica con sus transiciones."""
        for state, items in enumerate(self.states):
            out(f"I{state}:")
            for item in sorted(items):
                out(f"    {self.show_item(item)}")
            for symbol in self.grammar.symbols():
                target = self.goto_table.get((state, symbol))
                if target is not None:
                    out(f"    GOTO(I{state}, {symbol}) = I{target}")

    def show_tables(self, out=print):
        """Imprime ACTION y GOTO en una sola tabla, como la Figura 4.37.

        Las reducciones salen como 'rk', con k el numero de produccion de la
        lista que se imprime arriba, igual que en el libro.
        """
        out("Producciones numeradas:")
        for index in range(1, len(self.productions)):
            out(f"    {index}. {self.show_production(index)}")
        out()

        terminals = self.grammar.terminals + [END]
        nonterminals = list(self.grammar.nonterminals)
        width = 6

        header = "STATE".ljust(7)
        header += "".join(t.center(width) for t in terminals)
        header += " |"
        header += "".join(A.center(width) for A in nonterminals)
        out(header)

        for state in range(len(self.states)):
            row = str(state).ljust(7)
            for terminal in terminals:
                entry = self.action.get((state, terminal))
                row += (self._show_action(entry, short=True) if entry else "").center(width)
            row += " |"
            for nonterminal in nonterminals:
                target = self.goto_table.get((state, nonterminal))
                row += (str(target) if target is not None else "").center(width)
            out(row.rstrip())


def parse(automaton, string, trace=None):
    """Parser LR dirigido por tabla (Algoritmo 4.44, Seccion 4.6.3).

    La pila guarda estados. En cada paso se mira el estado de la cima s y el
    simbolo de entrada a:
      * ACTION[s, a] = shift t: se empuja t y se avanza en la entrada;
      * ACTION[s, a] = reduce A -> beta: se sacan |beta| estados y se empuja
        GOTO[estado que queda, A];
      * ACTION[s, a] = accept: la cadena pertenece al lenguaje;
      * celda vacia: error.

    En paralelo se lleva una pila de nodos para armar el arbol de analisis:
    al desplazar se empuja una hoja y al reducir se sacan |beta| nodos, que
    pasan a ser los hijos del nodo de A.
    """
    grammar = automaton.grammar
    states = [0]
    nodes = []
    input_symbols = list(string) + [END]
    position = 0

    while True:
        state = states[-1]
        lookahead = input_symbols[position]
        entry = automaton.action.get((state, lookahead))

        if entry is None:
            if trace is not None:
                trace.append((_states_text(states), _symbols_text(nodes),
                              _rest(input_symbols, position),
                              f"error: ACTION[{state}, {lookahead}] esta vacia"))
            return False, None

        kind, value = entry

        if kind == SHIFT:
            if trace is not None:
                trace.append((_states_text(states), _symbols_text(nodes),
                              _rest(input_symbols, position), f"shift {value}"))
            leaf = Node(lookahead)
            leaf.attrs["lexval"] = lookahead
            nodes.append(leaf)
            states.append(value)
            position += 1

        elif kind == REDUCE:
            head, body = automaton.productions[value]
            if trace is not None:
                trace.append((_states_text(states), _symbols_text(nodes),
                              _rest(input_symbols, position),
                              f"reduce {automaton.show_production(value)}"))

            # El indice de la produccion en la gramatica aumentada es uno mas
            # que en la gramatica original (la 0 es S' -> S).
            parent = Node(head, production=value - 1)
            if body:
                parent.children = nodes[-len(body):]
                del nodes[-len(body):]
                del states[-len(body):]
            nodes.append(parent)

            states.append(automaton.goto_table[(states[-1], head)])

        else:  # ACCEPT
            if trace is not None:
                trace.append((_states_text(states), _symbols_text(nodes),
                              _rest(input_symbols, position), "accept"))
            return True, nodes[-1] if nodes else None


def _states_text(states):
    return " ".join(str(s) for s in states)


def _symbols_text(nodes):
    return "".join(node.symbol for node in nodes)


def _rest(input_symbols, position):
    return "".join(input_symbols[position:])


def show_trace(trace, out=print):
    """Imprime el rastro del analisis en cuatro columnas, como la Figura 4.38."""
    out(f"{'STACK':<22}{'SYMBOLS':<14}{'INPUT':<14}ACTION")
    for states, symbols, rest, action in trace:
        out(f"{states:<22}{symbols:<14}{rest:<14}{action}")
