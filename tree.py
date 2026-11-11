"""Arbol de analisis sintactico compartido por los dos parsers.

Los dos parsers del Item 2 construyen exactamente el mismo tipo de arbol,
asi que el evaluador del Item 3 funciona sin importar con cual se analizo
la cadena. Cada nodo guarda su simbolo, la produccion usada (solo los no
terminales), sus hijos y sus atributos.
"""

from grammar import is_nonterminal


class Node:
    """Un nodo del arbol de analisis.

    'production' es el indice de la produccion aplicada en ese nodo, o None
    si el nodo es una hoja (un terminal). Una produccion A -> epsilon da un
    nodo sin hijos; al imprimir se muestra una hoja 'e' para que se vea.
    """

    __slots__ = ("symbol", "production", "children", "attrs", "nid")

    def __init__(self, symbol, production=None):
        self.symbol = symbol
        self.production = production
        self.children = []
        self.attrs = {}
        self.nid = None

    @property
    def is_leaf(self):
        return not is_nonterminal(self.symbol)

    def __repr__(self):
        return f"Node({self.symbol})"


def number_nodes(root):
    """Numera los nodos en preorden y devuelve la lista en ese orden.

    El numero identifica cada instancia de atributo en el grafo de
    dependencias: dos nodos con el mismo simbolo no se confunden.
    """
    order = []
    stack = [root]

    while stack:
        node = stack.pop()
        node.nid = len(order)
        order.append(node)
        stack.extend(reversed(node.children))

    return order


def show_tree(root, out=print, annotate=None):
    """Imprime el arbol, un nodo por linea, indentado por profundidad.

    'annotate' es una funcion opcional que recibe el nodo y devuelve el
    texto que se agrega a la derecha del simbolo (los atributos, en el
    Item 3).
    """

    def walk(node, depth):
        suffix = ""
        if annotate is not None:
            extra = annotate(node)
            if extra:
                suffix = "  " + extra

        out("  " * depth + node.symbol + suffix)

        if not node.is_leaf and not node.children:
            out("  " * (depth + 1) + "e")  # produccion A -> epsilon

        for child in node.children:
            walk(child, depth + 1)

    walk(root, 0)
