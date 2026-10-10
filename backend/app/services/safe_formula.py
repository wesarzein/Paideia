"""Bounded numeric expression language. Parsing is never execution of Python code."""

import ast
from decimal import ROUND_HALF_UP, Decimal, DecimalException, localcontext

FUNCTIONS = frozenset({"SUM", "MEAN", "MIN", "MAX", "ROUND"})
MAX_EXPRESSION = 512
MAX_NODES = 128
MAX_DEPTH = 20
MAX_MAGNITUDE = Decimal("1e9")


class FormulaError(ValueError):
    pass


def number(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float | str | Decimal):
        raise FormulaError("Se requiere un número finito")
    if len(str(value)) > 64:
        raise FormulaError("Número demasiado largo")
    try:
        result = Decimal(str(value))
    except DecimalException:
        raise FormulaError("Número inválido") from None
    if not result.is_finite() or abs(result) > MAX_MAGNITUDE:
        raise FormulaError("Número no finito o fuera del límite")
    if not -28 <= result.as_tuple().exponent <= 9 or len(result.as_tuple().digits) > 28:
        raise FormulaError("Precisión numérica fuera del límite")
    return result


def parse(expression: str, allowed_names) -> tuple[ast.Expression, frozenset[str]]:
    if not isinstance(expression, str) or not 1 <= len(expression) <= MAX_EXPRESSION:
        raise FormulaError("Expresión vacía o demasiado larga")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError):
        raise FormulaError("Sintaxis de fórmula inválida") from None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise FormulaError("Fórmula demasiado compleja")
    references = set()

    def validate(node, depth=0):
        if depth > MAX_DEPTH:
            raise FormulaError("Fórmula demasiado profunda")
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise FormulaError("Solo se permiten constantes numéricas")
            node.decimal_value = number(ast.get_source_segment(expression, node).replace('_', ''))
        elif isinstance(node, ast.Name):
            if node.id not in allowed_names:
                raise FormulaError(f"Referencia desconocida: {node.id}")
            references.add(node.id)
        elif isinstance(node, ast.BinOp) and isinstance(
            node.op, ast.Add | ast.Sub | ast.Mult | ast.Div
        ):
            validate(node.left, depth + 1)
            validate(node.right, depth + 1)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub):
            validate(node.operand, depth + 1)
        elif isinstance(node, ast.Call):
            if (not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS
                    or node.keywords or not 1 <= len(node.args) <= 32):
                raise FormulaError("Función o argumentos no permitidos")
            if node.func.id == "ROUND":
                if len(node.args) != 2 or not isinstance(node.args[1], ast.Constant):
                    raise FormulaError("ROUND exige un número y decimales constantes (0–4)")
                digits = node.args[1].value
                if type(digits) is not int or not 0 <= digits <= 4:
                    raise FormulaError("ROUND admite entre cero y cuatro decimales")
            for argument in node.args:
                validate(argument, depth + 1)
        else:
            raise FormulaError("Operación no permitida")

    validate(tree.body)
    return tree, frozenset(references)


def evaluate(expression: str, values: dict) -> Decimal | None:
    tree, references = parse(expression, values.keys())
    # Empty input never silently becomes a recorded zero or a literal grade.
    if any(values[name] is None for name in references):
        return None
    normalized = {name: number(values[name]) for name in references}

    def calculate(node):
        if isinstance(node, ast.Constant):
            result = node.decimal_value
        elif isinstance(node, ast.Name):
            result = normalized[node.id]
        elif isinstance(node, ast.UnaryOp):
            result = calculate(node.operand)
            if isinstance(node.op, ast.USub):
                result = -result
        elif isinstance(node, ast.BinOp):
            left, right = calculate(node.left), calculate(node.right)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            else:
                if right == 0:
                    raise FormulaError("División por cero")
                result = left / right
        else:
            args = [calculate(argument) for argument in node.args]
            function = node.func.id
            if function == "ROUND":
                result = args[0].quantize(Decimal(1).scaleb(-int(args[1])), ROUND_HALF_UP)
            elif function in ("SUM", "MEAN"):
                result = sum(args, Decimal(0))
                if function == "MEAN":
                    result /= len(args)
            else:
                result = min(args) if function == "MIN" else max(args)
        return number(result)

    try:
        with localcontext() as context:
            context.prec = 28
            return calculate(tree.body)
    except DecimalException:
        raise FormulaError("Error aritmético de fórmula") from None
