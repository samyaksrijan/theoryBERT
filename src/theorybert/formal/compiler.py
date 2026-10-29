"""Small arithmetic compiler: lex, parse with precedence, lower and check IR.

The grammar is explicit. User source is always data and is never evaluated as
Python, JavaScript, or shell code. Identifiers are symbolic external inputs.
"""

import re
from theorybert.contracts import TreeNode
from theorybert.formal.cfg import ParseError

ARITHMETIC_GRAMMAR = "E -> E '+' T | E '-' T | T\nT -> T '*' F | T '/' F | F\nF -> '(' E ')' | '-' F | '+' F | 'id' | 'num'"


def lex_expression(source):
    if len(source) > 4000:
        raise ParseError("RESOURCE_LIMIT", "Use at most 4,000 source characters.")
    rows, offset = [], 0
    while offset < len(source):
        if source[offset].isspace():
            offset += 1
            continue
        match = re.match(r"(?:\d+(?:\.\d*)?|\.\d+)|[A-Za-z_][A-Za-z_0-9]*|[()+*/-]", source[offset:])
        if match is None:
            raise ParseError("LEXICAL_ERROR", f"Unexpected source character at {offset+1}: {source[offset]!r}. Use identifiers, numbers, +, -, *, / and parentheses.")
        value = match[0]
        token = "num" if value[0].isdigit() or value[0] == "." else "id" if value[0].isalpha() or value[0] == "_" else value
        rows.append({"token": token, "lexeme": value, "start": offset, "end": offset+len(value)})
        offset += len(value)
        if len(rows) > 64:
            raise ParseError("RESOURCE_LIMIT", "Use at most 64 arithmetic tokens.")
    return rows


def compile_expression(tree, lexemes):
    leaves = []
    def collect(node):
        if node.terminal:
            leaves.append(node)
        for child in node.children:
            collect(child)
    collect(tree)
    if [n.symbol for n in leaves] != [r["token"] for r in lexemes]:
        raise ValueError("Compiler leaf/token alignment failed.")
    values = {node.node_id: row for node, row in zip(leaves, lexemes)}
    serial, instructions = 0, []
    def node(symbol, terminal=False, children=None):
        nonlocal serial
        result = TreeNode(f"ast{serial}", symbol, terminal, children or [])
        serial += 1
        return result
    def transform(n):
        children = n.children
        if len(children) == 1:
            if children[0].terminal:
                return node(values[children[0].node_id]["lexeme"], True)
            return transform(children[0])
        if len(children) == 2 and children[0].symbol in ("+", "-"):
            return node("unary " + children[0].symbol, children=[transform(children[1])])
        if len(children) == 3:
            if children[0].symbol == "(" and children[2].symbol == ")":
                return transform(children[1])
            if children[1].symbol in ("+", "-", "*", "/"):
                return node(children[1].symbol, children=[transform(children[0]), transform(children[2])])
        raise ValueError("Unsupported arithmetic production in compiler.")
    ast = transform(tree)
    def lower(n):
        if n.terminal:
            return {"kind": "identifier" if re.fullmatch(r"[A-Za-z_]\w*", n.symbol) else "number", "value": n.symbol}
        args = [lower(c) for c in n.children]
        target = f"t{len(instructions)}"
        instructions.append({"target": target, "operator": n.symbol, "arguments": args})
        return {"kind": "temporary", "value": target}
    result = lower(ast)
    # Reconstruct symbolic expressions from IR independently of lowering. This
    # catches undefined temps, operand order, arity and lost subexpressions.
    expressions = {}
    def read(operand):
        if operand["kind"] == "temporary":
            if operand["value"] not in expressions:
                raise ValueError("IR uses a temporary before definition.")
            return expressions[operand["value"]]
        return operand["value"]
    for instruction in instructions:
        op = instruction["operator"]
        args = instruction["arguments"]
        if len(args) != (1 if op.startswith("unary ") else 2):
            raise ValueError("IR operation has the wrong arity.")
        expressions[instruction["target"]] = (op, tuple(read(a) for a in args))
    def expression(n):
        return n.symbol if n.terminal else (n.symbol, tuple(expression(c) for c in n.children))
    if read(result) != expression(ast):
        raise ValueError("Lowered code does not preserve the syntax tree.")
    steps = []
    def expansions(n):
        if n.children:
            steps.append({"node_id": n.node_id, "children": [c.node_id for c in n.children]})
            for child in n.children:
                expansions(child)
    expansions(ast)
    # A leaf-only AST needs no animation steps; its root is always visible.
    symbols = sorted({r["lexeme"] for r in lexemes if r["token"] == "id"})
    return {"ast": ast.to_dict(), "instructions": instructions, "result": result, "inputs": symbols, "steps": steps, "ir_checked": True, "scope": "Symbolic arithmetic expression; identifiers are external inputs. Operators preserve the supplied grammar's precedence and associativity. No machine code or runtime execution."}, ast
