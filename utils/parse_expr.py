# - parse_expr.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Provide support functions that parse the matlab expression into AST - - - - - - - - #
from utils.expr_class import *

# Matlab operators
binary_operator = [
    "+",
    "-",
    "*",
    "/",
    "^",
    ">",
    "<",
    ">=",
    "<=",
    "==",
    "~=",
    "&&",
    "||",
    "&",
    "|",
    ".*",
    "./",
    ".\\",
    "\\",
    ".^",
    ".",  # consider struct operator . a special binary operator
]

operator = ["~", "'", ",'"]
operators = operator + binary_operator


def is_numeric(s):
    if s.isnumeric():
        return True
    try:
        float(s)  # Try to convert the string to a float
        return True
    except ValueError:
        return False


def parse_rhs_args_list(var_names: list, table_vars: dict):
    """
    Parse the rhs variable list to the input variables based on the variable table that
    provide information of existed variables.
    The rhs args can be variable or slice of variable in the table_vars, as well as
    nested expression of constant and function call.

    Args:
        var_names ([var1, var2, ...]): list of variable names (string) that need to be
        parsed
        table_vars (str : VariableExprAST): dict of variable names : variable AST

    Returns:
        var_list ([VariableExprAST]): list of ExprAST that are parsed from the rhs
    """
    var_list = []
    for var in var_names:
        type = parse_base_expr(var, table_vars)
        if isinstance(type, (VariableExprAST, SliceExprAST)):
            var_expr = map_variable(type, table_vars)  # get the variable from the table
            var_list.append(var_expr)  # add the variable to the function call
        else:
            var_list.append(type)
    return var_list


def parse_base_expr(expr: str, table_vars={}, var_notation=0):
    """
    Parse the AST composed of the base expression, including the numeric constant,
    variable, string which can be are composed of the binary expression, function call,
    etc.

    Args:
        expr (str): input string that need to be parsed
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.
        var_notation (int, optional): notation for new parsed variable. Defaults to 0.

    Raises:
        ValueError: if the expression cannot be parsed according to Matlab syntax

    Returns:
        ExprAST : parse result
    """
    expr = expr.strip()
    if expr == "":
        return ExprAST()
    if is_numeric(expr):
        return NumberExprAST(expr)
    if expr.isidentifier():
        return VariableExprAST(expr, "#" + str(var_notation))
    if (expr.startswith('"') and expr.endswith('"')) or (
        expr.startswith("'") and expr.endswith("'")
    ):
        return StringExprAST(expr[1:-1])
    if "(" in expr:
        return parse_paren_expr(expr, table_vars)

    if any(op in expr for op in operators):
        return parse_binary_expr(expr, table_vars)

    raise ValueError(f"Cannot parse the expression '{expr}'")


def parse_paren_expr(expr: str, table_vars={}):
    """
    Parse the expression enclosed in the parentheses, including the function call and
    slice expression.

    Args:
        expr (str): input string that need to be parsed
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.

    Returns:
        (ExprAST: SliceExprAST or CallExprAST) : parse result
    """
    ind_open_paren = expr.find("(")
    ind_close_paren = expr.rfind(")")
    if expr[:ind_open_paren] in table_vars:
        # if it is a variable, regard it as a slice of the existed variable
        # unconditionally
        var_in_use = table_vars[expr[:ind_open_paren]]
        return SliceExprAST(
            var_in_use, StringExprAST(expr[ind_open_paren + 1 : ind_close_paren])
        )

    # if it is a function call, recursively parse it
    function_call = CallExprAST(expr[:ind_open_paren], [])
    args = expr[ind_open_paren + 1 : ind_close_paren].split(",")
    for arg in args:
        type = parse_base_expr(arg, table_vars)
        if isinstance(type, VariableExprAST):
            type = table_vars[type.var_name]
            # TODO: check effect
            type.mark_parent_AST(function_call)
        function_call.args.append(type)
    return function_call


def parse_binary_expr(expr: str, table_vars={}):
    """
    Parse the math computation into binary expression, including the binary operator,
    struct operator, etc.

    Args:
        expr (str): input string that need to be parsed
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.

    Raises:
        ValueError: if the expression cannot be parsed according to Matlab syntax rules
        for binary expression

    Returns:
        _BinaryExprAST_: the returned top level expression is a binary expression AST
    """
    # The binary expression is only considered appeared in rhs
    cur_token = ""
    for [ind, ch] in enumerate(expr):
        if (cur_token + ch).isidentifier():
            cur_token += ch
            continue

        if is_numeric(cur_token + ch):
            cur_token += ch
            continue
        # handle the negative sign
        if ch == "-" and cur_token == "" and is_numeric(ch + expr[ind + 1]):
            cur_token += ch
            continue

        if (ch in binary_operator) or (expr[ind : ind + 2] in binary_operator):
            left_op = parse_base_expr(cur_token, table_vars)
            if isinstance(left_op, VariableExprAST):
                left_op = table_vars[left_op.var_name]
            # first consider combined operators like .*
            if expr[ind : ind + 2] in binary_operator:
                right_op = parse_base_expr(expr[ind + 2 :], table_vars)
                op = expr[ind : ind + 2]
            else:
                right_op = parse_base_expr(expr[ind + 1 :], table_vars)
                op = ch

            if isinstance(right_op, VariableExprAST):
                if op != ".":
                    right_op = table_vars[right_op.var_name]
                else:
                    # record the struct attribute
                    right_op.notation = right_op.var_name
            final_expr = BinaryExprAST(op, left_op, right_op)

            # Append the usage to the variable
            if isinstance(left_op, VariableExprAST):
                left_op.mark_parent_AST(final_expr)
            if isinstance(right_op, VariableExprAST):
                right_op.mark_parent_AST(final_expr)

            return final_expr

    raise ValueError(f"Cannot parse the binary expression '{expr}'")


def parse_FunctionAST(
    attr: tuple, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    """
    Parse the function declaration expression
    """
    function_def = FunctionAST(PrototypeAST(attr[0]))
    # rhs -> input variables
    for var in attr[1]:
        # generate the variable
        input_var = VariableExprAST(var, "#" + str(len(variable_list)), 1)
        input_var.set_block(cur_block)

        # set the block where the variable is used
        function_def.proto.add_arg(input_var)
        input_var.set_block(function_def)

        # store the variable in the table
        table_vars[var] = input_var
        variable_list.append(input_var)

    return function_def, variable_list, table_vars


def map_variable(var: VariableExprAST, table_vars: dict):
    """
    if the variable appears in the rhs, it is an existed variables
    replace the variables with the new existed one

    Args:
        var (VariableExprAST): The variable that need to be mapped
        table_vars (dict): Table of variable of current scope

    Returns:
        _VariableExprAST_: mapped result
    """
    if isinstance(var, VariableExprAST):
        if var.var_name not in table_vars:
            var.__error__(f"The variable '{var.var_name}' is not defined.")
        return table_vars[var.var_name]
    elif isinstance(var, SliceExprAST):
        if var.var.var_name not in table_vars:
            var.__error__(f"The variable '{var.var.var_name}' is not defined.")
        return table_vars[var.var.var_name]


def generate_new_var(
    var_expr: VariableExprAST,
    table_vars: dict,
    cur_block: BlockAST,
    generate_expr: ExprAST,
):
    """
    Generate the new variable that connect to its parent and child AST on the lhs, and
    update the variable table.

    Args:
        var_expr (VariableExprAST): base variable expression.
        table_vars (dict): dict of variable names : variable AST.
        cur_block (BlockAST): current block the AST is attached to.
        generate_expr (ExprAST): production expression that the variable is used.

    Returns:
        var_expr (VariableExprAST): valid variable expression.
        table_vars (dict): updated dict.
    """
    if isinstance(var_expr, SliceExprAST):
        # mark the slice produced variable as the parent of the variable
        var_expr.var = map_variable(var_expr.var, table_vars)
        var_expr.var.mark_parent_AST(var_expr)
        var_expr.revert_content_var()

        var_expr.set_block(cur_block)
        var_expr.child_AST(generate_expr, slice=var_expr.slice)
        table_vars[var_expr.var_name] = var_expr
    else:
        var_expr.set_block(cur_block)
        var_expr.child_AST(generate_expr, slice=ExprAST())
        table_vars[var_expr.var_name] = var_expr

    return var_expr, table_vars


def parse_CallExprAST(
    attr: tuple, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    """
    Parse the for function call expression
    """
    # parse the rhs to call expression AST
    rhs_args = parse_rhs_args_list(attr[1], table_vars)
    function_call = CallExprAST(attr[0], rhs_args)

    # parse the lhs to variable list and update the variable table
    out_var_list = []

    for var in attr[2]:
        if var == "~":
            continue
        output_var = parse_base_expr(var, table_vars, str(len(variable_list)))
        if isinstance(output_var, VariableExprAST):
            output_var, table_vars = generate_new_var(
                output_var, table_vars, cur_block, function_call
            )
            out_var_list.append(output_var)
            variable_list.append(output_var)
        else:
            raise ValueError(f"Cannot parse the output variable '{var}'.")

    # connect the produced lhs vars to the rhs variables' usage
    for var in rhs_args:
        if isinstance(var, VariableExprAST):
            var.mark_parent_AST(function_call)
        elif isinstance(var, SliceExprAST):
            var.var.mark_parent_AST(function_call)

    # parse the rhs to the production
    return function_call, variable_list, table_vars


def parse_ForLoopAST(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    """
    Parse the for loop expression
    """
    loop_varname = expr.split("=")[0].strip("for ")
    loop_range = expr.split("=")[1].split(":")

    loop_var = VariableExprAST(loop_varname, "#" + str(len(variable_list)))
    if len(loop_range) > 1:
        loop_start = parse_base_expr(loop_range[0], table_vars)
        loop_end = parse_base_expr(loop_range[1], table_vars)
        loop_for_block = ForLoopAST(loop_var, loop_start, loop_end)
    else:
        # TODO: consider loop range within a list
        pass
    loop_var.set_block(loop_for_block)
    variable_list.append(loop_var)
    table_vars[loop_varname] = loop_var
    return loop_for_block, variable_list, table_vars


def parse_IfExprAST(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    """
    Parse the control clause in if expression
    """
    expr = expr.strip()
    if expr.startswith("if"):
        cond = parse_base_expr(expr.split("if")[1], table_vars)
        if_expr = IfExprAST(cond)
        if_expr.set_block(cur_block)
        return if_expr, variable_list, table_vars
    elif expr.startswith("elseif"):
        cond = parse_base_expr(expr.split("elseif")[1], table_vars)
        cond.mark_attr("elseif", 1)
        return cond, variable_list, table_vars
    elif expr.startswith("else"):
        else_expr = ExprAST("else")
        else_expr.mark_attr("else", 1)

        return else_expr, variable_list, table_vars
