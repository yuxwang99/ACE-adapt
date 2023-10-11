# - var_usage_analysis.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Parse the Matlab code and generate the variable usage table to analyze its - - - - -#
import re
from function_tag import get_function_attributes
from utils.line import (
    remove_cmt_in_line,
    remove_empty_space_before_line,
    skip_line,
    merge_line,
)
from utils.parse_expr import (
    parse_base_expr,
    parse_FunctionAST,
    parse_CallExprAST,
    parse_ForLoopAST,
    parse_IfExprAST,
    generate_new_var,
)

from utils.expr_class import BlockAST, ExprAST


def parse_primary_expr(
    expr: str, variable_list=[], table_vars: dict = {}, cur_block: BlockAST = None
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

    # whether For loop
    if expr.startswith("for"):
        return parse_ForLoopAST(expr, variable_list, table_vars, cur_block)

    # TODO: implement whether While loop

    # whether If expression
    if expr.startswith("if") or expr.startswith("elseif") or expr.startswith("else"):
        return parse_IfExprAST(expr, variable_list, table_vars, cur_block)

    # whether function call or slice
    attr = get_function_attributes(expr, definition=False)
    if attr:
        # table vars record the variables in the current scope
        if attr[0] in table_vars:
            # if found, regard it as a slice
            assert len(attr[2]) == 1, "Slice should only produce one variable"
        else:
            # if not found, regard it as a function call
            return parse_CallExprAST(attr, variable_list, table_vars, cur_block)

    # parse binary expression by default
    # RE split "=" for assignment but not split "==", ">=" , "<=" and "~="
    result = re.split(r"(?<=[^<>=~])=(?![<>=~])", expr)

    # If it is a statement without "=", return empty expression to notate no assignment
    if len(result) < 2:
        return ExprAST(expr), variable_list, table_vars
    lhs_content, rhs_content = result[0], result[1]
    rhs = parse_base_expr(rhs_content, table_vars)
    lhs = parse_base_expr(lhs_content, table_vars, len(variable_list))
    lhs, table_vars = generate_new_var(lhs, table_vars, cur_block, rhs)
    variable_list.append(lhs)
    table_vars[lhs.var_name] = lhs

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

    variable_list = []

    code_line = file_contents.split("\n")
    line_state = -1
    cond_line_ind = []

    AST_nodes = []
    top_expr = []
    code_with_save = ""

    # create variable tables to record the variable usage
    table_vars = {}
    for [ind, line] in enumerate(code_line):
        code_with_save += line + "\n"

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

        cur_block = AST_nodes[-1] if len(AST_nodes) else None

        if line.strip() == "end":
            AST_nodes.pop()
            continue

        AST, variable_list, table_vars = parse_primary_expr(
            line, variable_list, table_vars, cur_block
        )

        if cur_block:
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
    return variable_list, top_expr


var_list, expr_list = analyze_var_usage("../src_paper/src/my_Extract_features_Jep.m")
if __name__ == "main":
    pass
