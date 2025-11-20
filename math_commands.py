import discord
from discord.ext import commands
from discord import app_commands
import ast
import operator
import math
from timeout import timeout


allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

# Allowed mathematical functions
allowed_functions = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'exp': math.exp,
    'abs': abs,
    'max': max,
    'min': min,
    'floor': math.floor,
    'ceil': math.ceil,
    'round': round
}


def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using AST parsing.
    """
    def _eval(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](left, right)
            else:
                raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):  # - <operand>
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](operand)
            else:
                raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.Call):  # Function calls like sin(x)
            func_name = node.func.id
            if func_name in allowed_functions:
                args = [_eval(arg) for arg in node.args]
                return allowed_functions[func_name](*args)
            else:
                raise ValueError(f"Unsupported function: {func_name}")
        elif isinstance(node, ast.Name):
            if node.id in ('pi', 'e'):
                return getattr(math, node.id)
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        else:
            raise ValueError(f"Unsupported expression: {node}")

    node = ast.parse(expr, mode='eval').body
    return _eval(node)


class MathCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="eval")
    async def eval_cmd(self, interaction: discord.Interaction, expression: str):
        """Safely evaluate a mathematical expression
        
        Parameters
        -----------
        expression: str
            The mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)", "sin(pi/2)")
        """
        # Replace ^ with ** for power operations
        expression = expression.replace('^', '**')
        
        try:
            with timeout(seconds=5):
                result = safe_eval(expression)
                await interaction.response.send_message(content=f"> {result}")
        except TimeoutError:
            await interaction.response.send_message(content="Error: Evaluation timed out.")
        except Exception as e:
            await interaction.response.send_message(content=f"Error evaluating expression: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MathCog(bot))
