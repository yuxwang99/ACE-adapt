# - parse_expr.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Provide support functions that parse the matlab expression into AST - - - - - - - - #
from utils.expr_class import *
import re

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

operator = [
    "~",
    "'",
    ",'",
    ":",  # consider slice operator : a special binary operator
    ",",
]
operators = operator + binary_operator


def is_numeric(s):
    # exclude the special case of NAN
    if s.upper() == "NAN":
        return False
    if s.isnumeric():
        return True
    try:
        float(s)  # Try to convert the string to a float
        return True
    except ValueError:
        return False


def higher_binary_precedence(expr: str, paren_type="()"):
    if paren_type == "()":
        ind_open_paren = expr.find("(")
        ind_close_paren = expr.rfind(")")
    elif paren_type == "[]":
        ind_open_paren = expr.find("[")
        ind_close_paren = expr.rfind("]")
    for op in binary_operator:
        if op in expr[:ind_open_paren] or op in expr[ind_close_paren + 1 :]:
            return True
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


def parse_base_expr(expr: str, table_vars={}, var_notation=0, lhs=False):
    """
    Parse the AST composed of the base expression, including the numeric constant,
    variable, string which can be are composed of the binary expression, function call,
    etc.

    Args:
        expr (str): input string that need to be parsed
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.
        var_notation (int, optional): notation for new parsed variable. Defaults to 0.
        lhs(bool, optional): whether the expression is in the lhs. Defaults to False.

    Raises:
        ValueError: if the expression cannot be parsed according to Matlab syntax

    Returns:
        ExprAST : parse result
    """
    if isinstance(expr, ExprAST):
        return expr

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

    paren_ind = expr.find("(")
    squ_par_ind = expr.find("[")
    curly_par_ind = expr.find("{")
    if paren_ind != -1 or squ_par_ind != -1 or curly_par_ind != -1:
        return parse_nested_expr(expr, table_vars, var_notation, lhs)

    if any(op in expr for op in operators):
        return parse_basic_computation(expr, table_vars, lhs)

    raise ValueError(f"Cannot parse the expression '{expr}'")


def parse_basic_computation(expr: str, table_vars={}, lhs=False):
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

        if (ch in operators) or (expr[ind : ind + 2] in binary_operator):
            left_op = parse_base_expr(cur_token, table_vars, lhs)
            if isinstance(left_op, VariableExprAST):
                if ch != ".":  # struct operator
                    left_op = table_vars[left_op.var_name]
                else:  # normal binary operator
                    left_op.notation = left_op.var_name

            # first consider combined operators like .*
            if expr[ind : ind + 2] in operators:
                right_op = parse_base_expr(expr[ind + 2 :], table_vars, lhs)
                op = expr[ind : ind + 2]
            else:
                right_op = parse_base_expr(expr[ind + 1 :], table_vars, lhs)
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


def parse_binary_expr(left_op, op, right_op, table_vars):
    if not isinstance(left_op, ExprAST):
        left_op = parse_base_expr(left_op, table_vars)
        if isinstance(left_op, VariableExprAST):
            left_op = map_variable(left_op, table_vars)

    if not isinstance(right_op, ExprAST):
        right_op = parse_base_expr(right_op)
        if isinstance(right_op, VariableExprAST):
            right_op = map_variable(right_op, table_vars)

    final_expr = BinaryExprAST(op, left_op, right_op)

    if isinstance(left_op, VariableExprAST):
        left_op.mark_parent_AST(final_expr)
    if isinstance(right_op, VariableExprAST):
        right_op.mark_parent_AST(final_expr)

    return final_expr


def parse_concat_expr(expr: str, table_vars={}):
    """
    Pass the Matlab supported concatenation expression, including the horizontal and
    vertical concatenation.

    Args:
        expr (str): input string
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.
    """
    # TODO: implemented before 30th Oct
    expr = expr.strip("; ")
    if expr.startswith("[") and expr.endswith("]"):
        expr = expr[1:-1]
    else:
        raise ValueError(f"Cannot parse the concatenation expression '{expr}'.")


def parse_nested_expr(nest_expr: str, table_vars={}, var_notation=0, lhs=False):
    expr_stack = []

    pre_word = ""
    pos_bracket = []
    # type_bracket includes {"()", "[]"}, non-detected parenthesis type at first
    type_bracket = ["  "]

    pre_paren_type = type_bracket[-1]
    str_notation = False

    for char in nest_expr:
        # determine current parenthesis type
        cur_paren_type = type_bracket[-1]

        if (pre_word + char).isidentifier():
            pre_word = pre_word + char
        elif is_numeric(pre_word + char):
            pre_word = pre_word + char
        elif pre_word + char in binary_operator:
            pre_word = pre_word + char
        elif str_notation:
            pre_word = pre_word + char
        elif char != " " or (cur_paren_type == "[]" and char == " "):
            if pre_word != pre_paren_type[1] and pre_word != "":
                expr_stack.append(pre_word)

            if char == "(" or char == "[" or char == "{":
                pos_bracket.append(len(expr_stack))
                if char == "(":
                    cur_paren_type = "()"
                elif char == "[":
                    cur_paren_type = "[]"
                elif char == "{":
                    cur_paren_type = "{}"
                type_bracket.append(cur_paren_type)

            if char == cur_paren_type[1]:
                expr = expr_stack[pos_bracket[-1] :] + [cur_paren_type[1]]
                # parse the non-nested expression
                expr_AST = parse_paren_expr(
                    expr, table_vars, cur_paren_type, var_notation, lhs
                )
                expr_AST.append(cur_paren_type)

                # pop current parsed expression
                expr_stack = expr_stack[: pos_bracket[-1]]
                expr_stack.append(expr_AST)
                pre_paren_type = type_bracket[-1]
                pos_bracket.pop()
                type_bracket.pop()

            pre_word = char

        # determine whether is string
        if char == '"' or (
            char == "'"
            and len(expr_stack) > 0
            and (
                (isinstance(expr_stack[-1], str) and expr_stack[-1] not in table_vars)
                or (isinstance(expr_stack[-1], ExprAST))
                or (isinstance(expr_stack[-1], list))
            )
        ):
            str_notation = not str_notation

    if pre_word != ")" and pre_word != "}" and pre_word != "]" and pre_word != ";":
        expr_stack.append(pre_word)

    final_call = get_args_from_lexical(expr_stack, table_vars, lhs=lhs)
    return final_call[0]


def get_args_from_lexical(lex_list: list, table_vars={}, var_list=[], lhs=False):
    """
    Get the arguments from the lexical list which is the list of string that consists of
    basic expression, e.g. identifier, number, etc. or expression AST.

    Args:
        lex_list (list): lexical list
        paren_type (str, optional): parenthesis type, e.g. (), []. Defaults to "()".
    """

    # concatenate the arguments to parse
    args = []
    arg = ""
    skip_flag = False
    for ind, lex in enumerate(lex_list):
        if skip_flag:
            skip_flag = False
            continue

        if (
            isinstance(lex, str)
            and ind < len(lex_list) - 1
            and isinstance(lex_list[ind + 1], str)
            and (lex_list[ind : ind + 2] in binary_operator)
        ):
            # is a two-symbol binary operator, combine with the next argument
            arg = parse_binary_expr(
                args[ind - 1],
                "".join(lex_list[ind : ind + 2]),
                get_args_from_lexical(lex_list[ind + 1])[0],
                table_vars,
            )
            args.pop()
            args.append(arg)
            skip_flag = True
        elif isinstance(lex, str) and (lex in binary_operator):
            # combine the binary operation to the latter argument
            arg = parse_binary_expr(
                args[-1],
                lex,
                get_args_from_lexical(lex_list[ind + 1 : ind + 2])[0],
                table_vars,
            )
            args.pop()
            args.append(arg)
            skip_flag = True
        elif isinstance(lex, list):
            # if is a list, consider combining with the previous lexis
            if len(args) < 1:
                concat_expr = ConcatExprAST(lex)
                args.append(concat_expr)
                continue

            # empty in bracket
            if len(lex) == 1:
                args.append(ExprAST())
                continue

            last_arg = args[-1]
            lex, paren_type = lex[:-1], lex[-1]

            if lhs or last_arg in table_vars:
                slicer = ""
                for ind in range(len(lex)):
                    slicer += lex[ind].get_content()

                if lhs:
                    slice_expr = SliceExprAST(
                        VariableExprAST(last_arg), StringExprAST(slicer)
                    )
                else:
                    slice_expr = SliceExprAST(
                        table_vars[last_arg], StringExprAST(slicer)
                    )
                args.pop()
                args.append(slice_expr)
            elif isinstance(last_arg, str) and last_arg.isidentifier():
                if paren_type == "()":
                    call_expr = CallExprAST(last_arg, lex)
                    args.pop()
                    args.append(call_expr)
                elif paren_type == "{}":
                    cell_expr = CellExprAST(last_arg, "#" + str(len(var_list)), 0, lex)
                    args.pop()
                    args.append(cell_expr)
            else:
                concat_expr = ConcatExprAST(lex)
                args.append(concat_expr)
        elif lex != "," and lex != ";":
            args.append(lex)

    return args


def parse_paren_expr(
    expr: str, table_vars={}, paren_type="()", var_notation=0, lhs=False
):
    """
    Parse the expression enclosed in the parentheses, including the function call and
    slice expression.

    Args:
        expr (str): input string that need to be parsed
        table_vars (dict, optional): Table of variable of current scope. Defaults to {}.

    Returns:
        (ExprAST: SliceExprAST or CallExprAST) : parse result
    """

    for ind in range(len(expr)):
        if expr[ind] == paren_type[0]:
            open_paren = ind
            break
    for ind in range(len(expr) - 1, -1, -1):
        if expr[ind] == paren_type[1]:
            close_paren = ind
            break

    args = get_args_from_lexical(expr[open_paren + 1 : close_paren], table_vars)
    args_expr = []
    for arg in args:
        type = parse_base_expr(arg, table_vars)
        if isinstance(type, VariableExprAST):
            if not lhs:
                # if in the rhs, map to the existed variable
                type = map_variable(type, table_vars)
        args_expr.append(type)
    return args_expr


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
        if var.var_name in table_vars:
            return table_vars[var.var_name]
        return var
    elif isinstance(var, SliceExprAST):
        if var.var.var_name in table_vars:
            return table_vars[var.var.var_name]
        return var.var


def generate_new_var(
    var_expr: VariableExprAST,
    line_ind: int,
    table_vars: dict,
    cur_block: BlockAST,
    generate_expr: ExprAST,
    notation: str = "",
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
        if notation != "":
            var_expr.notation = notation
        # mark the slice produced variable as the parent of the variable
        if var_expr.var in table_vars:
            var_expr.var = map_variable(var_expr.var, table_vars)
            var_expr.var.mark_parent_AST(var_expr)
            var_expr.revert_content_var()

        var_expr.set_block(cur_block)
        var_expr.child_AST(generate_expr, slice=var_expr.slice)
        table_vars[var_expr.var_name] = var_expr
    else:
        if notation != "":
            var_expr.notation = notation
        var_expr.set_block(cur_block)
        var_expr.child_AST(generate_expr, slice=ExprAST())
        table_vars[var_expr.var_name] = var_expr

    var_expr.mark_attr("line", line_ind)
    return var_expr, table_vars


def parse_CallExprAST(
    attr: tuple,
    line_ind: int,
    variable_list=[],
    table_vars: dict = {},
    cur_block: BlockAST = None,
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
                output_var, line_ind, table_vars, cur_block, function_call
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
        loop_start = parse_base_expr(loop_range[0], table_vars)
        loop_for_block = ForLoopAST(loop_var, loop_start, loop_start)
    loop_var.set_block(loop_for_block)
    variable_list.append(loop_var)
    table_vars[loop_varname] = loop_var
    return loop_for_block, variable_list, table_vars


def parse_WhileLoopAST(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    loop_cond = parse_base_expr(expr.split("while")[1], table_vars)
    loop_expr = WhileLoopAST(loop_cond, [])
    return loop_expr, variable_list, table_vars


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
        cur_block.cond_ind += 1
        cond = parse_base_expr(expr.split("elseif")[1], table_vars)
        cond.mark_attr("elseif", 1)
        return cond, variable_list, table_vars
    elif expr.startswith("else"):
        else_expr = ExprAST("else")
        else_expr.mark_attr("else", 1)

        return else_expr, variable_list, table_vars


def parse_TryExprAST(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    """
    Parse the control clause in try-catch expression
    """
    expr = expr.strip()
    if expr.startswith("try"):
        try_expr = TryExprAST()
        try_expr.set_block(cur_block)
        return try_expr, variable_list, table_vars
    elif expr.startswith("catch"):
        cur_block.catch = 1
        return ExprAST("catch"), variable_list, table_vars


def parse_SwitchExprAST(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
):
    expr = expr.strip()
    if expr.startswith("switch"):
        swtich_var = parse_base_expr(expr.split("switch")[1], table_vars)
        switch_expr = SwitchExprAST(swtich_var, [])
        switch_expr.set_block(cur_block)

        variable_list.append(swtich_var)
        table_vars[swtich_var.var_name] = swtich_var
        return switch_expr, variable_list, table_vars

    elif expr.startswith("case"):
        case_cond = parse_base_expr(expr.split("case")[1], table_vars)
        case_cond.mark_attr("case", 1)
        cur_block.case.append(case_cond)
        return case_cond, variable_list, table_vars
