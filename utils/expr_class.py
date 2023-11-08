# - expr_class.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Provide class declaration for AST - - - - - - - - - - - - - - - - - - - - - - - - - #
class ExprAST:
    """
    Base class to parse the expression.
    """

    def __init__(self, content=None) -> None:
        self._content = ""
        self.in_loop = False
        self._attr = {}

    def __error__(self, msg: str):
        raise ValueError(msg)

    def get_content(self):
        return self._content

    def is_empty(self):
        return len(self._content) == 0

    def mark_attr(self, key, value):
        self._attr[key] = value


class BlockAST:
    """
    Class to represent the block.
    """

    def __init__(self, body: list = []):
        self.type = None
        self.body = body
        self._is_loop = False

    def add_body(self, body: ExprAST):
        self.body.append(body)

    def set_variable_list(self, variable_list: list):
        self.variable_list = variable_list

    def is_empty(self):
        return len(self.body) == 0


class NumberExprAST(ExprAST):
    """
    Class to represent a numeric constant.
    """

    def __init__(self, value: str):
        super().__init__()
        self.value = float(value)
        self._content = value


class VariableExprAST(ExprAST):
    """
    Class to represent a variable.
    """

    def __init__(
        self,
        var_name: str,
        notation: str = "#0",
        varAttr: int = 0,
        slice: ExprAST = ExprAST(),
        production: ExprAST = ExprAST(),
    ):
        super().__init__()

        self.var_name = var_name
        if not isinstance(notation, str):
            raise ValueError("The notation should be a string.")
        self.notation = notation
        self.production = {}
        if not production.is_empty():
            self.production[slice] = self.child_AST(production)
        self.usage = []
        # add the attributes to record the variable usage including internal(0),
        # input(1), and output(2)
        self._varAttr = varAttr
        # set super class content
        self._content = var_name

    def child_AST(self, expr: ExprAST, slice: ExprAST = ExprAST()):
        """
        AST where the variable is produced.
        """
        self.production[slice] = expr

    def __parent_AST__(self, expr: ExprAST):
        # avoid append the same usage during the recurse process
        if expr not in self.usage:
            self.usage.append(expr)

    def mark_parent_AST(self, expr: ExprAST):
        """
        AST where the variable is used.
        """
        if isinstance(expr, list):
            for e in expr:
                self.__parent_AST__(e)
        else:
            self.__parent_AST__(expr)

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used.
        """
        self.block = block
        self.in_loop = block._is_loop
        if isinstance(block, IfExprAST):
            self.mark_attr("cond", block.cond_ind)
        if isinstance(block, SwitchExprAST):
            self.mark_attr("switch", block.case[-1].get_content())
        if isinstance(block, TryExprAST):
            self.mark_attr("catch", block.catch)

    def get_block(self):
        """
        Get the block where the variable is used.
        """
        return self.block


class StringExprAST(ExprAST):
    """
    Class to represent a string constant.
    """

    def __init__(self, value):
        super().__init__()
        str_value = ""
        if isinstance(value, list):
            for v in value:
                if isinstance(v, str):
                    str_value += v
                elif isinstance(v, ExprAST):
                    str_value += v.get_content()
                else:
                    raise ValueError("The value should be a string or ExprAST.")
        self.value = str_value
        self._content = str_value


class ConcatExprAST(ExprAST):
    """
    Class to represent the concatenate expression in "[]".
    """

    def __init__(self, value=[]):
        super().__init__()
        self.value = value
        self._content = value
        self.args = []

    def get_content(self):
        str_content = ""
        for c in self._content:
            if isinstance(c, ExprAST):
                str_content += ", " + c.get_content()
            else:
                str_content += ", " + c
        return "[" + str_content + "]"

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used.
        """
        self.block = block
        if isinstance(block, IfExprAST):
            self.mark_attr("cond", block.cond_ind)


class CellExprAST(VariableExprAST):
    """
    Class to represent a boolean constant.
    """

    def __init__(
        self,
        var_name: str,
        notation: str = "#0",
        varAttr: int = 0,
        slice: ExprAST = ExprAST(),
        production: ExprAST = ExprAST(),
    ):
        super().__init__(var_name, notation, varAttr, slice, production)


class SliceExprAST(VariableExprAST):
    """
    Class to represent a slice of a variable.
    """

    def __init__(self, var: VariableExprAST, slice: StringExprAST):
        notation = var.notation + ":" + str(len(var.usage) + 1)
        super().__init__(var.var_name, notation)
        self.var = var
        self.slice = slice
        self._content = var.var_name + "(" + slice.value + ")"

    def revert_content_var(self):
        # if the slice is used in the lhs, revert the content to the variable
        self._content = self.var.var_name


class BinaryExprAST(ExprAST):
    """
    Class to represent a binary operator.
    """

    def __init__(self, op: str, left_op: ExprAST, right_op: ExprAST):
        super().__init__()
        self.op = op
        self.left_op = left_op
        self.right_op = right_op

        self._content = left_op.get_content() + op + right_op.get_content()


class CallExprAST(ExprAST):
    """
    Class to represent a function call.
    """

    def __init__(self, func_name: str, args: list = []):
        super().__init__()
        self.func_name = func_name
        self.args = args
        self._content = func_name

    def __content__(self):
        self._content = (
            self.func_name
            + "("
            + ",".join([arg.get_content() for arg in self.args])
            + ")"
        )
        return self._content

    def get_content(self):
        return self.__content__()

    def is_empty(self):
        self.__content__()
        return super().is_empty()


class PrototypeAST:
    """
    Class to represent the function prototype.
    """

    def __init__(self, func_name: str, args: list = []):
        super().__init__()
        self.func_name = func_name
        self.args = args
        self._content = func_name

    def add_arg(self, arg: str):
        self.args.append(arg)


class FunctionAST(BlockAST):
    """
    Class to represent the function definition
    """

    def __init__(self, proto: PrototypeAST):
        super().__init__()
        self.proto = proto
        self.type = "function"
        self._content = proto.func_name
        # body initialized to be empty
        self.body = []

    def add_body(self, content: ExprAST):
        if content.is_empty():
            return
        self.body.append(content)


class ForLoopAST(BlockAST):
    """
    Class to represent the for loop.
    """

    def __init__(
        self, var: VariableExprAST, start: ExprAST, end: ExprAST, body: list = []
    ):
        super().__init__(body)
        self.var = var
        self.type = "for"
        if start == end:
            self.range = start
        else:
            self.start = start
            self.end = end
        self._content = (
            "for " + var.var_name + "=" + start._content + ":" + end._content
        )
        self._is_loop = True

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used.
        """
        self.block = block

    def is_empty(self):
        return self._content == None and super().is_empty()


class WhileLoopAST(BlockAST):
    """
    Class to represent the while loop.
    """

    def __init__(self, cond: ExprAST, body=[]):
        super().__init__()
        self.type = "while"
        self.cond = cond
        self.body = body
        self._is_loop = True

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used.
        """
        self.block = block


class IfExprAST(BlockAST):
    """
    Class to represent the if expression.
    """

    def __init__(
        self,
        cond: ExprAST,
        content: ExprAST = ExprAST(),
        else_body: ExprAST = ExprAST(),
    ):
        super().__init__()
        self.type = "if"
        self.cond = [cond]
        if isinstance(content, list):
            self.body = content
        elif not content.is_empty():
            self.body = [content]
        else:
            self.body = []
        # record the index of the current condition, -1 represents the else condition
        self.cond_ind = 0
        self.else_ = else_body

    def set_block(self, block: BlockAST):
        """
        Set the block where the block belongs to.
        """
        self.block = block
        self._is_loop = block._is_loop


class TryExprAST(BlockAST):
    """
    Class to represent the try expression.
    """

    def __init__(self, content: ExprAST = ExprAST()):
        super().__init__()
        if isinstance(content, list):
            self.body = content
        elif not content.is_empty():
            self.body = [content]
        else:
            self.body = []

        self.catch = 0

    def set_block(self, block: BlockAST):
        """
        Set the block where the block belongs to.
        """
        self.block = block
        self._is_loop = block._is_loop


class SwitchExprAST(BlockAST):
    """
    Class to represent the if expression.
    """

    def __init__(
        self,
        var: ExprAST,
        case: list = [],
    ):
        super().__init__()
        self.type = "switch"
        self.var = var
        self.case = case

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used
        """
        self.block = block
        self._is_loop = block._is_loop
