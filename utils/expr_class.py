class ExprAST:
    """
    Base class to parse the expression
    """

    def __init__(self, content=None) -> None:
        self._content = content
        self._attr = {}

    def __error__(self, msg: str):
        raise ValueError(msg)

    def is_empty(self):
        return self._content == None

    def mark_attr(self, key, value):
        self._attr[key] = value


class BlockAST:
    """
    Class to represent the block
    """

    def __init__(self, body: list = []):
        self.type = None
        self.body = body

        # init empty variable list
        self.variable_list = []

    def add_body(self, body: ExprAST):
        self.body.append(body)

    def is_empty(self):
        return len(self.body) == 0


class NumberExprAST(ExprAST):
    """
    Class to represent a numeric constant
    """

    def __init__(self, value: str):
        super().__init__()
        self.value = float(value)
        self._content = value


class BoolExprAST(ExprAST):
    """
    Class to represent a boolean constant
    """

    def __init__(self, value: str):
        super().__init__()
        self.value = value
        self._content = value


class VariableExprAST(ExprAST):
    """
    Class to represent a variable
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
        self.notation = notation
        self.production = {}
        if not production.is_empty():
            self.production[slice] = self.child_AST(production)
        self.usage = []
        # add the attributes to record the variable usage including internal(0), input(1), and output(2)
        self._varAttr = varAttr
        # set super class content
        self._content = var_name

    def child_AST(self, expr: ExprAST, slice: ExprAST = ExprAST()):
        """
        AST where the variable is produced
        """
        self.production[slice] = expr

    def __parent_AST__(self, expr: ExprAST):
        # avoid append the same usage during the recurse process
        if expr not in self.usage:
            self.usage.append(expr)

    def parent_AST(self, expr: ExprAST):
        """
        AST where the variable is used
        """
        if isinstance(expr, list):
            for e in expr:
                self.__parent_AST__(e)
        else:
            self.__parent_AST__(expr)

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used
        """
        self.block = block
        if isinstance(block, IfExprAST):
            self.mark_attr("cond", block.cond_ind)

    def get_block(self):
        """
        Get the block where the variable is used
        """
        return self.block


class StringExprAST(ExprAST):
    """
    Class to represent a string constant
    """

    def __init__(self, value: str):
        super().__init__()
        self.value = value
        self._content = value


class SliceExprAST(VariableExprAST):
    """
    Class to represent a slice of a variable
    """

    def __init__(self, var: VariableExprAST, slice: StringExprAST):
        notation = var.notation + ":" + str(len(var.usage) + 1)
        super().__init__(var.var_name, notation, var._varAttr)
        self.var = var
        self.slice = slice
        self._content = var.var_name + "(" + slice.value + ")"

    def revert_content_var(self):
        # if the slice is used in the lhs, revert the content to the variable
        self._content = self.var.var_name


class BinaryExprAST(ExprAST):
    """
    Class to represent a binary operator
    """

    def __init__(self, op: str, left_op: ExprAST, right_op: ExprAST):
        super().__init__()
        self.op = op
        self.left_op = left_op
        self.right_op = right_op
        self._content = left_op._content + op + right_op._content


class CallExprAST(ExprAST):
    """
    Class to represent a function call
    """

    def __init__(self, func_name: str, args: list = []):
        super().__init__()
        self.func_name = func_name
        self.args = args
        self._content = func_name

    def __content__(self):
        self._content = (
            self.func_name + "(" + ",".join([arg._content for arg in self.args]) + ")"
        )
        return self._content

    def is_empty(self):
        self.__content__()
        return super().is_empty()


class PrototypeAST:
    """
    Class to represent the function prototype
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
        self._content = proto.func_name
        # body initialized to be empty
        self.body = []

    def add_body(self, content: ExprAST):
        if content.is_empty():
            return
        self.body.append(content)


class ForLoopAST(BlockAST):
    """
    Class to represent the for loop
    """

    def __init__(
        self, var: VariableExprAST, start: ExprAST, end: ExprAST, body: list = []
    ):
        super().__init__(body)
        self.var = var
        self.start = start
        self.end = end
        self._content = (
            "for " + var.var_name + "=" + start._content + ":" + end._content
        )

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used
        """
        self.block = block

    def is_empty(self):
        return self._content == None and super().is_empty()


class WhileLoopAST(BlockAST):
    """
    Class to represent the while loop
    """

    def __init__(self, cond: ExprAST, body: ExprAST):
        super().__init__()
        self.cond = cond
        self.body = body

    def set_block(self, block: BlockAST):
        """
        Set the block where the variable is used
        """
        self.block = block


class IfExprAST(BlockAST):
    """
    Class to represent the if expression
    """

    def __init__(
        self,
        cond: ExprAST,
        content: ExprAST = ExprAST(),
        else_body: ExprAST = ExprAST(),
    ):
        super().__init__()
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
        Set the block where the variable is used
        """
        self.block = block

    # def add_elseif(self, cond: ExprAST, then_content: ExprAST = ExprAST()):
    #     self.cond.append(cond)
    #     if self.cond_ind > 0:
    #         self.cond_ind += 1
    #     else:
    #         raise ValueError("The elseif expression should be after if expression.")
    #     if not then_content.is_empty():
    #         self.body.append(then_content)

    # def add_else(self, else_content: ExprAST = ExprAST()):
    #     self.cond_ind = -1
    #     else_expr = ExprAST("else")
    #     self.body.append(else_expr)
    #     if not else_content.is_empty():
    #         self.body.append(else_content)

    # def add_then(self, then: ExprAST):
    #     if self.then.is_empty():
    #         self.then = then
    #     else:
    #         self.__error__("The then expression is already defined.")

    # def add_else(self, else_: ExprAST):
    #     self.else_ = else_
    #     if self.else_.is_empty():
    #         self.else_ = else_
    #     else:
    #         self.__error__("The else expression is already defined.")
