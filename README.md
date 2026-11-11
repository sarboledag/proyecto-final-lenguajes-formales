# Final Project — FIRST/FOLLOW, LL(1), SLR(1) and a Syntax-Directed Definition

Final project of Formal Languages. The program reads a context-free grammar in the
format of Section 2.2 of the assignment, computes its FIRST and FOLLOW sets, decides
whether the grammar is LL(1) and whether it is SLR(1), and parses strings with the
table-driven predictive parser and with the LR parser. A second program evaluates a
syntax-directed definition (SDD) over the parse tree of a string, using the dependency
graph and a topological order.

Everything follows Aho, Lam, Sethi and Ullman, *Compilers: Principles, Techniques, and
Tools* (2nd Edition). The section, algorithm or figure that each part follows is stated
in the docstring of the corresponding module and in the report.

There is also a **web interface** (the optional bonus, not required by the assignment),
organized in the same layers as the previous assignments of the course (Controller →
Gateway → Functions): a Flask
server that exposes the same algorithms as a REST API and a page that draws the tables,
the LR(0) automaton, the parse tree and the dependency graph.

No parser generator or parsing library is used. The algorithms use only the Python
standard library (`sys`, `heapq`, `io`); Flask is needed only to run the web part, and
the console programs work without it.

## Students

- Juan Manuel Zuluaga
- Santiago Arboleda Giraldo
- Nicolás Patiño Palacio

## Origin of the code

This group (Juan Manuel Zuluaga, Santiago Arboleda Giraldo and Nicolás Patiño Palacio) started from the
implementation that Juan Manuel Zuluaga had written together with Isabela Gómez Naranjo
in a previous group, and completed it for this submission. The base code and its first
version of the report are therefore credited to Juan Manuel Zuluaga and Isabela Gómez
Naranjo; the group is responsible for everything that is submitted here.

## Environment

- **Operating System:** Windows 11 Home Single Language (10.0.26200)
- **Programming Language:** Python 3.14.6
- **Framework (web part only):** Flask 3.1.3
- **Tools:** `pip` to install Flask (web part only), `curl` for testing the endpoints, any
  browser for the demo page, and LaTeX (`pdflatex`) for the report.
- **Also verified on:** Linux (Debian), Python 3.13.18, Flask 3.1.3 and pdfTeX 3.141592653-2.6-1.40.25
  (TeX Live 2023): `python tests.py` (67 checks), the three examples of the assignment,
  `sdd_main.py`, the web endpoints, and the compilation of `informe.tex`.

The code is plain Python 3 and runs on any Python 3.8 or newer. Items 1, 2 and 3 need no
third-party package at all; only the web server needs Flask.

## Project structure

| File | Role |
| --- | --- |
| `grammar.py` | Reading and representation of the grammar (Section 2.2 format). |
| `sets.py` | **Item 1.** FIRST and FOLLOW, and the `--sets` output format. Section 4.4.2. |
| `ll1.py` | **Item 2.** LL(1) condition, predictive parsing table and the table-driven parser. Sections 4.4.3 and 4.4.4, Algorithms 4.31 and 4.34. |
| `slr1.py` | **Item 2.** LR(0) items, `CLOSURE`, `GOTO`, canonical collection, ACTION/GOTO tables and the LR parser. Sections 4.6.2, 4.6.3 and 4.6.4, Algorithms 4.46 and 4.44. |
| `tree.py` | The parse tree that both parsers build. |
| `sdd.py` | **Item 3.** The SDD *as data*: attribute table and semantic rules. |
| `evaluator.py` | **Item 3.** Dependency graph and evaluation in topological order. Sections 5.2.1 and 5.2.2. Generic: it knows nothing about the particular SDD. |
| `main.py` | Program of Items 1 and 2. |
| `sdd_main.py` | Program of Item 3. |
| `sdd_grammar.txt` | The grammar chosen for the SDD, in the Section 2.2 format. |
| `tests.py` | Test suite. |
| `informe.tex` | **Item 4.** LaTeX source of the report. |
| `gateway.py` | **Web.** Bridge between the controller and the algorithms: turns the internal structures into JSON and every domain error into a `GatewayError`. |
| `app.py` | **Web.** Flask controller: validates the shape of each request and delegates to the gateway. |
| `templates/analyzer.html` | **Web.** The demo page: tables, LR(0) automaton, parse tree and dependency graph drawn as SVG. |
| `requirements.txt` | The only dependency, Flask, and only for the web part. |

## Items 1 and 2: building and running

Nothing to build. From this directory:

```bash
python main.py
```

Add `--sets` to print the FIRST and FOLLOW sets before the program continues, as the
assignment requires:

```bash
python main.py --sets
```

The program first reads the grammar: a line with the number `n` of nonterminals, then
`n` lines `A -> alt1 alt2 ...`. After that it prints one of the four messages of
Section 2.2.2 and reads strings, one per line, until an empty line. For each string it
prints `yes` or `no`. The empty string is given as a line containing only `e`; `$` is
appended by the program and must not be typed.

Example session (Example 2 of the assignment):

```
3
S -> AB
A -> aA d
B -> bBc e
Select a parser (T: for LL(1), B: for SLR(1), Q: quit):
T
d
yes
adbc
yes
a
no

Select a parser (T: for LL(1), B: for SLR(1), Q: quit):
Q
```

On Windows it is often easier to put the input in a file and redirect it:

```bash
python main.py --sets < input.txt
```

### Extra flags (not part of the required output)

These two flags only add information and are never used in the official run:

- `--tables` prints the LL(1) table, the LR(0) automaton and the ACTION/GOTO tables.
  This is how the tables of the report were produced.
- `--trace` prints the step-by-step parse of every string, in the three-column format of
  Figure 4.21 (LL(1)) and the four-column format of Figure 4.38 (SLR(1)).

```bash
python main.py --tables --trace < input.txt
```

## Item 3: building and running

```bash
python sdd_main.py
```

It reads the grammar from `sdd_grammar.txt` and then the strings, one per line, until an
empty line. For every string it prints `no` if the string is not in the language;
otherwise it prints the annotated parse tree (one node per line, indented by depth), the
evaluation order and the value of the main attribute of the start symbol.

```bash
echo 102#t | python sdd_main.py
```

Flags:

| Flag | Effect |
| --- | --- |
| *(a path)* | Use another grammar file instead of `sdd_grammar.txt`. |
| `--slr` | Parse with the SLR(1) parser instead of the LL(1) one. Both build the same tree, so the result is the same. |
| `--sdd` | Print the attribute table and the semantic rules. |
| `--graph` | Also print the edges of the dependency graph. |
| `--circular` | Use the circular version of the SDD, to show that the evaluator detects cycles (Step 6 of the assignment). |
| `--step` | Print the evaluation attribute by attribute; when the input is a terminal, wait for Enter at each step (the optional visualizer). |

The chosen grammar describes a numeral followed by `#` and by a letter that says in
which base it must be read:

```
S -> N#B        B -> b   (base 2)
N -> DR         B -> t   (base 3)
R -> DR | e
D -> 0 | 1 | 2
```

So `102#t` is the numeral 102 in base 3, that is 11, and `1011#b` is 1011 in base 2,
which is also 11.

The point of this SDD is that the base appears at the **end** of the string but is
needed from the **first** digit: in `S -> N#B` the inherited attribute `N.base` depends
on `B.val`, which is to the right of `N`. The SDD is therefore neither S-attributed nor
L-attributed, and a recursive left-to-right evaluation does not work. The dependency
graph and the topological order do, which is exactly the general method the assignment
asks for.

## Web interface (extra)

Install Flask once and start the server:

```bash
pip install -r requirements.txt
```

```bash
python app.py
```

Then open <http://127.0.0.1:5000/analyzer>. The page has three tabs:

1. **Gramatica** — paste a grammar and get the verdict, the FIRST and FOLLOW sets, the
   LL(1) table with its conflicts highlighted, the canonical collection of LR(0) item
   sets and the ACTION/GOTO tables. There are buttons with the three examples of the
   assignment ready to load.
2. **Cadenas** — type strings, pick the parser, and get `yes`/`no`, the step-by-step
   parse (including the step where it fails) and the parse tree drawn as SVG.
3. **SDD** — Item 3: the annotated parse tree, the dependency graph drawn by levels, the
   evaluation order and the value of `S.val`. The checkbox switches to the circular SDD,
   and the attributes that end up inside the cycle are shown in red.

The page has no external dependencies (no CDN), so it works offline.

Environment variables: `HOST` (default `127.0.0.1`), `PORT` (default `5000`) and `DEBUG`
(`DEBUG=0` turns off the debugger and the reloader).

### Endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /` | Health check, lists the endpoints. |
| `POST /api/grammar` | FIRST, FOLLOW, LL(1) table, LR(0) automaton, SLR(1) tables and verdict. |
| `POST /api/parse` | Parses strings with the LL(1) or the SLR(1) parser. Returns `yes`/`no`, the trace and the tree. |
| `POST /api/sdd` | Evaluates the SDD of Item 3 on each string. |
| `GET /api/sdd` | The grammar, the attribute table and the semantic rules of Item 3. |
| `GET /analyzer` | The demo page. |

Both `POST /api/grammar` and `POST /api/parse` take the grammar in the format of Section
2.2, except that the first line with the number of nonterminals is optional here. In
`strings` you can send a list or a single text with one string per line.

```bash
curl -s -X POST http://127.0.0.1:5000/api/grammar -H "Content-Type: application/json" -d "{\"grammar\":\"S -> AB\nA -> aA d\nB -> bBc e\"}"
```

```bash
curl -s -X POST http://127.0.0.1:5000/api/sdd -H "Content-Type: application/json" -d "{\"strings\":\"102#t\"}"
```

Errors always come back as JSON: `400` when the request is malformed and `422` when the
grammar or the request is valid JSON but the algorithms reject it (for example, asking
for the LL(1) parser on a grammar that is not LL(1)).

The web layer does not reimplement anything: `app.py` and `gateway.py` call the very
same functions that `main.py` and `sdd_main.py` call from the console.

## Tests

```bash
python tests.py
```

It checks the three examples of the assignment, the FIRST and FOLLOW sets of Example
4.30 of the book, the four output cases, both parsers on the same strings, the size of
the LR(0) collection of the expression grammar (12 states, as in Figure 4.31), the whole
Item 3 including the detection of the circular SDD, and the JSON that the web layer
returns. All 67 checks pass. The suite does not need Flask.

## Report

The report is written in LaTeX, in `informe.tex`. It needs only `geometry`, `amsmath`,
`booktabs`, `array`, `tikz` and `hyperref`, so it compiles with any standard
distribution:

```bash
pdflatex informe.tex
pdflatex informe.tex
```

Two runs are needed so that the table of contents and the cross-references to the
figures come out right. The easiest way is to upload `informe.tex` to Overleaf and
download the PDF. **`informe.pdf` must sit in the root directory of the submission**, as
the assignment requires.

## Generative AI tools

Claude (Anthropic) was used in this project. In the first version of the code, written by
Juan Manuel Zuluaga and Isabela Gómez Naranjo, it was used through Claude Code for the
following:

- To explain the statement and to clarify the algorithms of Sections 4.4, 4.6 and 5.2 of
  the book.
- To help write the Python code of the modules listed above and the comments that point
  to the section or algorithm each one follows.
- To help write the web layer (`app.py`, `gateway.py` and the demo page), which is an
  extra and does not implement any algorithm of its own.
- To review the wording of this README and of the report.

In this group's work on the final version, Claude (claude.ai) was used to review the code
against the statement, to run the test suite and the examples of the assignment, to
correct the README and the report, and to prepare the repository.

The algorithms themselves are the ones described in the book; no parser generator or
parsing library was used, and every member of the group has gone through the code and
can explain and trace it by hand.
