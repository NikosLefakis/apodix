"""Break code on purpose, one small change at a time.

Each mutant is a copy of the source with exactly one change. Only code that the
linked tests actually executed is changed, so a mutant always lands on a line the
test could have noticed.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

_COMPARE = {
    ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
}
_BINOP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
_SYMBOL = {
    ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<=", ast.Eq: "==", ast.NotEq: "!=",
    ast.In: "in", ast.NotIn: "not in", ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
}


@dataclass(frozen=True)
class Mutant:
    index: int
    line: int
    description: str
    source: str


def _live(node: ast.AST, executed: set[int] | None) -> bool:
    if executed is None:
        return True
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start) or start
    return any(line in executed for line in range(start, end + 1))


def _names_used_by_executed_code(tree: ast.AST, executed: set[int] | None) -> set[str]:
    names: set[str] = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and _live(node, executed):
                    names.add(node.id)
    return names


class _Mutator(ast.NodeTransformer):
    def __init__(self, executed: set[int] | None, used: set[str], target: int | None = None):
        self.executed = executed
        self.used = used
        self.target = target
        self.sites: list[tuple[int, str]] = []
        self._depth = 0          # > 0 while inside a function
        self._constant = False   # inside a module-level constant that executed code reads

    # -- scope ------------------------------------------------------------
    def _function(self, node):
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1
        return node

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def _module_constant(self, node, names):
        if self._depth == 0 and names and all(n in self.used for n in names):
            self._constant = True
            self.generic_visit(node)
            self._constant = False
        else:
            self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        return self._module_constant(node, [t.id for t in node.targets if isinstance(t, ast.Name)])

    def visit_AnnAssign(self, node):
        return self._module_constant(node, [node.target.id] if isinstance(node.target, ast.Name) else [])

    def _eligible(self, node) -> bool:
        return self._constant or (self._depth > 0 and _live(node, self.executed))

    def _hit(self, node, description: str) -> bool:
        index = len(self.sites)
        self.sites.append((node.lineno, description))
        return index == self.target

    # -- operators --------------------------------------------------------
    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in _COMPARE and self._eligible(node):
            old = type(node.ops[0])
            new = _COMPARE[old]
            if self._hit(node, f"`{_SYMBOL[old]}` became `{_SYMBOL[new]}`"):
                node.ops = [new()]
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in _BINOP and self._eligible(node):
            old = type(node.op)
            new = _BINOP[old]
            if self._hit(node, f"`{_SYMBOL[old]}` became `{_SYMBOL[new]}`"):
                node.op = new()
        return node

    def visit_Constant(self, node):
        value = node.value
        if isinstance(value, (int, float)) and not isinstance(value, bool) and self._eligible(node):
            new = value / 2 if isinstance(value, float) and 0 < value < 1 else value + 1
            if self._hit(node, f"{value!r} became {new!r}"):
                return ast.copy_location(ast.Constant(new), node)
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        if self._eligible(node.test):
            cond = ast.unparse(node.test)
            if self._hit(node.test, f"condition `{cond}` always false"):
                node.test = ast.copy_location(ast.Constant(False), node.test)
            elif self._hit(node.test, f"condition `{cond}` always true"):
                node.test = ast.copy_location(ast.Constant(True), node.test)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._eligible(node):
            if self._hit(node, f"`not {ast.unparse(node.operand)}` lost its `not`"):
                return node.operand
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        if node.value is not None and not isinstance(node.value, ast.Constant) and self._eligible(node):
            if self._hit(node, "returned value replaced by 0"):
                node.value = ast.copy_location(ast.Constant(0), node.value)
        return node


def mutants_for(source: str, executed: set[int] | None = None) -> list[Mutant]:
    """All single-change mutants of `source`. `executed` limits them to lines the tests ran."""
    used = _names_used_by_executed_code(ast.parse(source), executed)
    probe = _Mutator(executed, used)
    probe.visit(ast.parse(source))

    mutants: list[Mutant] = []
    for index, (line, description) in enumerate(probe.sites):
        tree = ast.parse(source)
        _Mutator(executed, used, target=index).visit(tree)
        ast.fix_missing_locations(tree)
        mutants.append(Mutant(index, line, description, ast.unparse(tree)))
    return mutants
