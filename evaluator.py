"""Item 3: grafo de dependencias y evaluacion por orden topologico.

Se siguen las Secciones 5.2.1 y 5.2.2 del libro:
  * el grafo de dependencias tiene un vertice por cada atributo de cada
    nodo del arbol, y una arista del atributo que se usa al atributo que la
    regla define (Seccion 5.2.1);
  * un orden valido de evaluacion es cualquier orden topologico de ese
    grafo; si el grafo tiene un ciclo, la SDD es circular para esa cadena y
    no hay ningun orden valido (Seccion 5.2.2).

Este modulo es generico: no sabe nada de la SDD de sdd.py. Recibe la
gramatica, el arbol y el diccionario de reglas, y con eso arma el grafo.
Una instancia de atributo se identifica con el par (numero de nodo, nombre
del atributo), por eso los nodos se numeran antes de empezar.
"""

import heapq

from tree import number_nodes


class SDDError(Exception):
    """La SDD no se puede evaluar sobre este arbol."""


class Evaluation:
    """Resultado de evaluar la SDD sobre un arbol.

    'order' es el orden topologico usado, como lista de instancias
    (nodo, atributo). 'graph' son las aristas del grafo de dependencias.
    'circular' dice si se encontro un ciclo; en ese caso 'order' trae solo
    las instancias que si se pudieron ordenar.
    """

    def __init__(self, nodes, order, edges, circular, unresolved):
        self.nodes = nodes
        self.order = order
        self.edges = edges
        self.circular = circular
        self.unresolved = unresolved

    def name(self, instance):
        """Nombre legible de una instancia, por ejemplo 'R[3].acc'.

        El numero entre corchetes es el del nodo en el arbol: sin el no se
        distinguirian los atributos de dos nodos con el mismo simbolo.
        """
        nid, attribute = instance
        return f"{self.nodes[nid].symbol}[{nid}].{attribute}"

    def value(self, instance):
        nid, attribute = instance
        return self.nodes[nid].attrs.get(attribute)


def build_graph(root, grammar, sdd):
    """Arma el grafo de dependencias del arbol (Seccion 5.2.1).

    Devuelve (nodes, rules_by_instance, edges, instances):
      * 'rules_by_instance' asocia cada instancia de atributo con la regla
        que la define y con las instancias de las que depende;
      * 'edges' es el conjunto de aristas (dependencia -> definida);
      * 'instances' son todos los vertices del grafo.

    Los terminales no tienen reglas: su lexval ya viene del parser y por eso
    son vertices sin aristas que entren.
    """
    nodes = number_nodes(root)
    rules_by_instance = {}
    instances = set()
    edges = set()

    for node in nodes:
        if node.is_leaf:
            # Un terminal aporta su lexval, que ya se conoce.
            instances.add((node.nid, "lexval"))
            continue

        head, body = grammar.productions[node.production]
        rules = sdd["rules"].get((head, body))

        if rules is None:
            raise SDDError(
                f"La SDD no tiene reglas para la produccion "
                f"{head} -> {''.join(body) if body else 'e'}."
            )

        # Posicion 0 es la cabeza y 1..n son los simbolos del cuerpo.
        participants = [node] + list(node.children)

        for rule in rules:
            target_position, target_attribute = rule.target
            target = (participants[target_position].nid, target_attribute)

            if target in rules_by_instance:
                raise SDDError(
                    f"El atributo {participants[target_position].symbol}."
                    f"{target_attribute} se define dos veces en la produccion "
                    f"{head} -> {''.join(body) if body else 'e'}."
                )

            dependencies = [
                (participants[position].nid, attribute)
                for position, attribute in rule.deps
            ]

            rules_by_instance[target] = (rule, dependencies)
            instances.add(target)

            for dependency in dependencies:
                instances.add(dependency)
                edges.add((dependency, target))

    return nodes, rules_by_instance, edges, instances


def topological_order(instances, edges):
    """Orden topologico del grafo (Seccion 5.2.2), con el algoritmo de Kahn.

    Se van sacando los vertices que ya no tienen dependencias pendientes. Si
    al final quedan vertices sin sacar, es porque hacen parte de un ciclo.
    Entre los vertices que estan listos se escoge siempre el menor, para que
    la salida sea la misma en cada ejecucion.
    """
    indegree = {instance: 0 for instance in instances}
    successors = {instance: [] for instance in instances}

    for source, target in edges:
        indegree[target] += 1
        successors[source].append(target)

    ready = [instance for instance in instances if indegree[instance] == 0]
    heapq.heapify(ready)

    order = []
    while ready:
        instance = heapq.heappop(ready)
        order.append(instance)

        for successor in successors[instance]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    unresolved = sorted(instance for instance in instances if indegree[instance] > 0)
    return order, unresolved


def evaluate(root, grammar, sdd):
    """Evalua la SDD sobre el arbol y devuelve una Evaluation.

    Si el grafo tiene un ciclo no se evalua nada y la Evaluation queda con
    circular = True.
    """
    nodes, rules_by_instance, edges, instances = build_graph(root, grammar, sdd)
    order, unresolved = topological_order(instances, edges)

    if unresolved:
        return Evaluation(nodes, order, edges, True, unresolved)

    for instance in order:
        nid, attribute = instance
        entry = rules_by_instance.get(instance)

        if entry is None:
            # Solo puede ser el lexval de un terminal, que ya esta puesto.
            if attribute not in nodes[nid].attrs:
                raise SDDError(
                    f"El atributo {nodes[nid].symbol}.{attribute} se usa pero "
                    f"ninguna regla lo define."
                )
            continue

        rule, dependencies = entry
        values = [nodes[dep_nid].attrs[dep_attribute]
                  for dep_nid, dep_attribute in dependencies]
        nodes[nid].attrs[attribute] = rule.f(values)

    return Evaluation(nodes, order, edges, False, [])


def annotate(node):
    """Texto con los atributos de un nodo, para imprimir el arbol anotado."""
    if not node.attrs:
        return ""

    parts = []
    for name in sorted(node.attrs):
        value = node.attrs[name]
        parts.append(f"{name} = {value!r}" if isinstance(value, str) else f"{name} = {value}")

    return "{ " + ", ".join(parts) + " }"


def show_graph(evaluation, out=print):
    """Imprime las aristas del grafo de dependencias, una por linea."""
    for source, target in sorted(evaluation.edges):
        out(f"    {evaluation.name(source)} -> {evaluation.name(target)}")
