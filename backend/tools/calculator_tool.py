"""Safe math calculator."""
import math, re, ast, operator
from .registry import register

OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
FUNCS = {"sqrt": math.sqrt, "abs": abs, "sin": math.sin, "cos": math.cos,
         "tan": math.tan, "log": math.log, "log10": math.log10,
         "exp": math.exp, "round": round, "floor": math.floor, "ceil": math.ceil}
CONSTS = {"pi": math.pi, "e": math.e}


def _eval(n):
    if isinstance(n, ast.Constant): return n.value
    if isinstance(n, ast.BinOp): return OPS[type(n.op)](_eval(n.left), _eval(n.right))
    if isinstance(n, ast.UnaryOp): return OPS[type(n.op)](_eval(n.operand))
    if isinstance(n, ast.Name):
        if n.id in CONSTS: return CONSTS[n.id]
        raise ValueError(f"Unknown: {n.id}")
    if isinstance(n, ast.Call):
        if not isinstance(n.func, ast.Name): raise ValueError("Invalid call")
        if n.func.id not in FUNCS: raise ValueError(f"Unknown func: {n.func.id}")
        return FUNCS[n.func.id](*[_eval(a) for a in n.args])
    raise ValueError("Unsupported expression")


@register("calculator", "Evaluate a math expression.", {
    "type": "object",
    "properties": {"expression": {"type": "string"}},
    "required": ["expression"],
})
def calculator(args: dict) -> str:
    expr = args.get("expression", "").strip().lower()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)$", expr)
    if m:
        return str(float(m.group(1)) / 100 * float(m.group(2)))
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(expr, mode="eval")
        r = _eval(tree.body)
    except Exception as e:
        raise ValueError(f"Cannot calculate: {e}")
    if isinstance(r, float) and r.is_integer(): return str(int(r))
    return f"{r:.6f}".rstrip("0").rstrip(".") if isinstance(r, float) else str(r)