# - var_usage_analysis.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Parse the Matlab code and generate the variable usage table for analysis - - - - - -#
import re
from function_tag import get_function_attributes
from utils.parser.line import (
    remove_cmt_in_line,
    remove_empty_space_before_line,
    skip_line,
    merge_line,
)
from utils.parser.parse_expr import (
    map_variable,
    parse_base_expr,
    parse_FunctionAST,
    parse_TryExprAST,
    parse_ForLoopAST,
    parse_WhileLoopAST,
    parse_IfExprAST,
    parse_SwitchExprAST,
    generate_new_var,
)

from utils.parser.expr_class import (
    BlockAST,
    ExprAST,
    VariableExprAST,
    ConcatExprAST,
    BinaryExprAST,
    CallExprAST,
)

CONTROL_CLAUSE = ["for", "while", "if", "elseif", "else", "switch", "case", "try"]


def initialize_var_table(reserve_word: list[str]):
    var_dict = {}
    var_list = []
    if isinstance(reserve_word, list):
        for ind, var in enumerate(reserve_word):
            var_dict[var] = VariableExprAST(
                var, "#" + str(ind), varAttr=1, production=ExprAST()
            )
            var_list.append(var_dict[var])

    return var_dict, var_list


def parse_ctrl_clause(
    expr: str,
    variable_list=[],
    table_vars: dict = {},
    cur_block: BlockAST = BlockAST(),
):
    """Parse the control clause

    Args:
        expr (str): string expression of the control clause
        variable_list (list, optional): variable list of current scope. Defaults to [].
        table_vars (dict, optional): variable map of current scope. Defaults to {}.
        cur_block (BlockAST, optional): current block the code attached. Defaults to BlockAST().

    Returns:
        parse result of the control clause respecitvely
    """
    # whether For loop
    if expr.startswith("for"):
        return parse_ForLoopAST(expr, variable_list, table_vars, cur_block)

    # whether While loop
    if expr.startswith("while"):
        return parse_WhileLoopAST(expr, variable_list, table_vars, cur_block)

    # whether switch case
    if expr.startswith("switch") or expr.startswith("case"):
        return parse_SwitchExprAST(expr, variable_list, table_vars, cur_block)

    # whether If expression
    if expr.startswith("if") or expr.startswith("elseif") or expr.startswith("else"):
        return parse_IfExprAST(expr, variable_list, table_vars, cur_block)

    # whether try expression
    if expr.startswith("try") or expr.startswith("catch"):
        return parse_TryExprAST(expr, variable_list, table_vars, cur_block)


def produce_lhs_expr(lhs, line_ind, variable_list, table_vars, cur_block, rhs):
    """Generate the left hand side expression, and assign the production of the
    rhs to each VariableAST in lhs

    Args:
        lhs (exprAST): expression of the left hand side.
        line_ind (int): index of the line of the expression.
        variable_list (list): list of variable of in scope.
        table_vars (dict): table of variable of current scope.
        cur_block (BlockAST): current block the AST is attached to.
        rhs (exprAST): right hand side expression of the assignment

    Returns:
        lhs(exprAST)
        variable_list (list): updated list of variable of in scope with lhs
        table_vars (dict):updated  table of variable of current scope with lhs
    """
    if isinstance(lhs, ConcatExprAST):
        # if lhs is a list of variables, add them to the variable list
        for var in lhs.args:
            if not isinstance(var, VariableExprAST):
                continue
            var, table_vars = generate_new_var(
                var, line_ind, table_vars, cur_block, rhs, "#" + str(len(variable_list))
            )
            table_vars[var.var_name] = var
            variable_list.append(var)
    elif isinstance(lhs, BinaryExprAST) and lhs.op == ".":
        # if lhs is a struct, the parser return it as a binary expression
        # the left operation is the struct name, the right operation is the field name
        var = lhs.left_op
        var, table_vars = generate_new_var(
            var, line_ind, table_vars, cur_block, rhs, "#" + str(len(variable_list))
        )
        table_vars[var.var_name] = var
        variable_list.append(var)
    else:
        lhs, table_vars = generate_new_var(
            lhs, line_ind, table_vars, cur_block, rhs, "#" + str(len(variable_list))
        )
        table_vars[lhs.var_name] = lhs
        variable_list.append(lhs)

    return lhs, variable_list, table_vars


def connect_rhs_expr(var_expr, lhs, table_vars):
    """add the lhs variable to the rhs variable usage

    Args:
        var_expr (_type_): _description_
        lhs (_type_): _description_
        table_vars (_type_): _description_
    """
    if isinstance(var_expr, VariableExprAST):
        var_expr.mark_parent_AST(lhs)

    if (
        isinstance(var_expr, CallExprAST)
        or isinstance(var_expr, ConcatExprAST)
        or isinstance(var_expr, BinaryExprAST)
    ):
        for arg in var_expr.args:
            connect_rhs_expr(arg, lhs, table_vars)


def parse_primary_expr(
    expr: str,
    line_ind: int,
    variable_list=[],
    table_vars: dict = {},
    cur_block: BlockAST = BlockAST(),
):
    """
    Parse the primary expression including the control clause, function call, binary
    expression, etc.
    """
    # if it is empty, return empty expression
    expr = expr.strip("; ")
    if expr == "":
        return ExprAST(), variable_list, table_vars

    # whether a FunctionAST
    attr = get_function_attributes(expr, definition=True)
    if attr:
        return parse_FunctionAST(attr, variable_list, table_vars, cur_block)

    # try to parse the expression as a control clause
    if expr.split(" ")[0] in CONTROL_CLAUSE or expr.split("(")[0] in CONTROL_CLAUSE:
        return parse_ctrl_clause(expr, variable_list, table_vars, cur_block)

    # RE split "=" for assignment but not split "==", ">=" , "<=" and "~="
    result = re.split(r"(?<=[^<>=~])=(?![<>=~])", expr)

    # If it is a statement without "=", return root expression to notate no assignment
    if len(result) < 2:
        return ExprAST(expr), variable_list, table_vars

    # parse the left and right hand side of the expression
    lhs_content, rhs_content = result[0], result[1]
    rhs = parse_base_expr(rhs_content, table_vars, lhs=False)
    lhs = parse_base_expr(lhs_content, table_vars, len(variable_list), lhs=True)

    if isinstance(rhs, VariableExprAST):
        rhs = map_variable(rhs, table_vars)

    lhs, variable_list, table_vars = produce_lhs_expr(
        lhs, line_ind, variable_list, table_vars, cur_block, rhs
    )

    connect_rhs_expr(rhs, lhs, table_vars)

    return lhs, variable_list, table_vars


def analyze_var_usage(
    func_dir: str,
    #   , call_pattern: dict, func_name: str
):
    try:
        with open(func_dir, "r") as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        raise ValueError(f"The file '{func_dir}' was not found.")

    code_line = file_contents.split("\n")
    line_state = -1
    cond_line_ind = []

    AST_nodes = []
    top_var_list = {}
    top_expr = []

    # create variable tables to record the variable usage
    table_vars, variable_list = initialize_var_table(["nargin", "pi", "exp"])
    for [ind, line] in enumerate(code_line):
        # skip the comment line
        line_state = skip_line(line, line_state)
        if line_state == 4:
            cond_line_ind.append(ind)
        if line_state != 0:
            continue

        # empty space to allow it align with the original code
        _, n_empty = remove_empty_space_before_line(line)
        empty_chars = " " * n_empty

        # process the complete line
        pre_lines = [remove_cmt_in_line(code_line[i]) for i in cond_line_ind]
        line = merge_line(remove_cmt_in_line(line), pre_lines, empty_chars)
        cond_line_ind = []

        cur_block = AST_nodes[-1] if len(AST_nodes) else BlockAST([])

        if line.strip() == "end":
            top_node = AST_nodes[-1]
            AST_nodes.pop()
            # if AST_nodes is empty, means it is the end of the function
            # clear the variable list and table
            if len(AST_nodes) == 0:
                top_var_list[top_node] = variable_list
                variable_list = []
                table_vars = {}
            continue

        AST, variable_list, table_vars = parse_primary_expr(
            line, ind, variable_list, table_vars, cur_block
        )

        if cur_block.type:
            # Attach the expression to its belonging block
            cur_block.add_body(AST)
        else:
            # If no parent node, add to top_expr
            top_expr.append(AST)

        # if the returned type is a block, add it to the AST_nodes,
        # the following expression until the end will be attached to it
        if isinstance(AST, BlockAST):
            # save current variable list to the block
            AST_nodes.append(AST)

    # append the last variable list to the top_var_list in case no end match the
    # function declaration
    if len(AST_nodes) > 0 and (AST_nodes[-1] not in top_var_list):
        top_var_list[AST_nodes[-1]] = variable_list
    return top_var_list, top_expr
