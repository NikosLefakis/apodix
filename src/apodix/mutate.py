"""Break code on purpose, one small change at a time.

Each mutant is a copy of the source with exactly one change. Only code that the linked tests actually
executed is changed, so a mutant always lands on a line the test could have noticed.

Every mutant carries two hints about how much it says about the criterion:
  depth     1 when the change is in a function the test calls directly, 2 when it is in something that
            function calls, and so on;
  function  the name of the function the change is in, so the verdict can favor code the criterion names.

A criterion may also name the functions it is about (`only`); then nothing else is changed.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Collection, Iterator, Mapping

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
    depth: int = 1
    function: str = ""


def _normalise(executed) -> Mapping[int, int] | None:
    """`executed` maps a line number to its call depth. A plain set of lines (depth 1 each) and None
    (everything counts, depth 1) are accepted too."""
    if executed is None:
        return None
    if isinstance(executed, Mapping):
        return executed
    return {line: 1 for line in executed}


def _span(node: ast.AST) -> range:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start) or start
    return range(start, end + 1)


def _depth_of(node: ast.AST, executed: Mapping[int, int] | None) -> int | None:
    """Smallest call depth among the executed lines of `node`; None if none of them ran."""
    if executed is None:
        return 1
    depths = [executed[line] for line in _span(node) if line in executed]
    return min(depths) if depths else None


def _allowed(stack: list[str], only: Collection[str] | None) -> bool:
    """Is a function (given as its chain of enclosing class and function names) one the criterion names?
    A name matches on its own ("bump_major") or qualified ("Version.bump_major"), and so do functions nested inside it."""
    if only is None:
        return True
    return any(stack[i] in only or ".".join(stack[: i + 1]) in only for i in range(len(stack)))


def _iter_functions(node: ast.AST, stack: list[str] | None = None) -> Iterator[tuple[list[str], ast.AST]]:
    stack = stack or []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield [*stack, child.name], child
            yield from _iter_functions(child, [*stack, child.name])
        elif isinstance(child, ast.ClassDef):
            yield from _iter_functions(child, [*stack, child.name])
        else:
            yield from _iter_functions(child, stack)


def _names_used_by_executed_code(tree: ast.AST, executed, only) -> dict[str, int]:
    """Module-level names read by executed code (inside allowed functions), with the smallest depth they are read at."""
    names: dict[str, int] = {}
    for stack, fn in _iter_functions(tree):
        if not _allowed(stack, only):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                depth = _depth_of(node, executed)
                if depth is not None:
                    names[node.id] = min(depth, names.get(node.id, depth))
    return names


class _Mutator(ast.NodeTransformer):
    def __init__(self, executed, used: dict[str, int], only, target: int | None = None):
        self.executed = executed
        self.used = used
        self.only = only
        self.target = target
        self.sites: list[tuple[int, str, int, str]] = []   # (line, description, depth, function)
        self._stack: list[str] = []                         # enclosing class and function names
        self._functions: list[str] = []                     # enclosing function names only
        self._constant_depth: int | None = None             # set inside a module-level constant that executed code reads

    # -- scope ------------------------------------------------------------
    def _function(self, node):
        self._stack.append(node.name)
        self._functions.append(node.name)
        self.generic_visit(node)
        self._functions.pop()
        self._stack.pop()
        return node

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def visit_ClassDef(self, node):
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()
        return node

    def _module_constant(self, node, names):
        if not self._functions and names and all(n in self.used for n in names):
            self._constant_depth = min(self.used[n] for n in names)
            self.generic_visit(node)
            self._constant_depth = None
        else:
            self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        return self._module_constant(node, [t.id for t in node.targets if isinstance(t, ast.Name)])

    def visit_AnnAssign(self, node):
        return self._module_constant(node, [node.target.id] if isinstance(node.target, ast.Name) else [])

    def _depth(self, node) -> int | None:
        """Depth if this node may be changed, None if it may not."""
        if self._constant_depth is not None:
            return self._constant_depth
        if self._functions and _allowed(self._stack, self.only):
            return _depth_of(node, self.executed)
        return None

    def _hit(self, node, description: str, depth: int) -> bool:
        index = len(self.sites)
        function = self._functions[-1] if self._functions else ""
        self.sites.append((node.lineno, description, depth, function))
        return index == self.target

    # -- operators --------------------------------------------------------
    def visit_Compare(self, node):
        self.generic_visit(node)
        depth = self._depth(node)
        if depth is not None and len(node.ops) == 1 and type(node.ops[0]) in _COMPARE:
            old = type(node.ops[0])
            new = _COMPARE[old]
            if self._hit(node, f"`{_SYMBOL[old]}` became `{_SYMBOL[new]}`", depth):
                node.ops = [new()]
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        depth = self._depth(node)
        if depth is not None and type(node.op) in _BINOP:
            old = type(node.op)
            new = _BINOP[old]
            if self._hit(node, f"`{_SYMBOL[old]}` became `{_SYMBOL[new]}`", depth):
                node.op = new()
        return node

    def visit_Constant(self, node):
        value = node.value
        depth = self._depth(node)
        if depth is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
            new = value / 2 if isinstance(value, float) and 0 < value < 1 else value + 1
            if self._hit(node, f"{value!r} became {new!r}", depth):
                return ast.copy_location(ast.Constant(new), node)
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        depth = self._depth(node.test)
        if depth is not None:
            cond = ast.unparse(node.test)
            if self._hit(node.test, f"condition `{cond}` always false", depth):
                node.test = ast.copy_location(ast.Constant(False), node.test)
            elif self._hit(node.test, f"condition `{cond}` always true", depth):
                node.test = ast.copy_location(ast.Constant(True), node.test)
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        depth = self._depth(node)
        if depth is not None and isinstance(node.op, ast.Not):
            if self._hit(node, f"`not {ast.unparse(node.operand)}` lost its `not`", depth):
                return node.operand
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        depth = self._depth(node)
        if depth is not None and node.value is not None and not isinstance(node.value, ast.Constant):
            if self._hit(node, "returned value replaced by 0", depth):
                node.value = ast.copy_location(ast.Constant(0), node.value)
        return node


def mutants_for(source: str, executed=None, only: Collection[str] | None = None) -> list[Mutant]:
    """All single-change mutants of `source`.

    executed  limits changes to lines the tests ran (line -> call depth, or a set of lines)
    only      limits changes to functions with these names ("bump_major" or "Version.bump_major")
    """
    lines = _normalise(executed)
    only = set(only) if only else None
    used = _names_used_by_executed_code(ast.parse(source), lines, only)
    probe = _Mutator(lines, used, only)
    probe.visit(ast.parse(source))

    mutants: list[Mutant] = []
    for index, (line, description, depth, function) in enumerate(probe.sites):
        tree = ast.parse(source)
        _Mutator(lines, used, only, target=index).visit(tree)
        ast.fix_missing_locations(tree)
        mutants.append(Mutant(index, line, description, ast.unparse(tree), depth, function))
    return mutants
