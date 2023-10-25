# - var_usage_analysis.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Parse the Matlab code and generate the variable usage table for analysis - - - - - -#
import re
from function_tag import get_function_attributes
from utils.line import (
    remove_cmt_in_line,
    remove_empty_space_before_line,
    skip_line,
    merge_line,
)
from utils.parse_expr import (
    map_variable,
    parse_base_expr,
    parse_FunctionAST,
    parse_CallExprAST,
    parse_ForLoopAST,
    parse_WhileLoopAST,
    parse_IfExprAST,
    parse_SwitchExprAST,
    generate_new_var,
)

from utils.expr_class import (
    BlockAST,
    ExprAST,
    VariableExprAST,
    ConcatExprAST,
    BinaryExprAST,
)


def parse_primary_expr(
    expr: str,
    line_ind: int,
    variable_list=[],
    table_vars: dict = {},
    cur_block: BlockAST = None,
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

    # whether While loop
    if expr.startswith("while"):
        return parse_WhileLoopAST(expr, variable_list, table_vars, cur_block)

    # whether switch case
    if expr.startswith("switch") or expr.startswith("case"):
        return parse_SwitchExprAST(expr, variable_list, table_vars, cur_block)

    # whether If expression
    if expr.startswith("if") or expr.startswith("elseif") or expr.startswith("else"):
        return parse_IfExprAST(expr, variable_list, table_vars, cur_block)

    # whether function call or slice
    # attr = get_function_attributes(expr, definition=False)
    # if attr:
    #     # table vars record the variables in the current scope
    #     if attr[0] in table_vars:
    #         # if found, regard it as a slice
    #         assert len(attr[2]) == 1, "Slice should only produce one variable"
    #     else:
    #         # if not found, regard it as a function call
    #         return parse_CallExprAST(
    #             attr, line_ind, variable_list, table_vars, cur_block
    #         )

    # parse binary expression by default
    # RE split "=" for assignment but not split "==", ">=" , "<=" and "~="
    result = re.split(r"(?<=[^<>=~])=(?![<>=~])", expr)

    # If it is a statement without "=", return empty expression to notate no assignment
    if len(result) < 2:
        return ExprAST(expr), variable_list, table_vars
    lhs_content, rhs_content = result[0], result[1]
    rhs = parse_base_expr(rhs_content, table_vars)
    lhs = parse_base_expr(lhs_content, table_vars, len(variable_list))

    if isinstance(lhs, ConcatExprAST):
        # if lhs is a list of variables, add them to the variable list
        for var in lhs.value:
            if not isinstance(var, VariableExprAST):
                continue
            var, table_vars = generate_new_var(
                var, line_ind, table_vars, cur_block, rhs
            )
            table_vars[var.var_name] = var
            variable_list.append(var)
    elif isinstance(lhs, BinaryExprAST) and lhs.op == ".":
        # if lhs is a struct, the parser return it as a binary expression
        # the left operation is the struct name, the right operation is the field name
        var = lhs.left_op
        var, table_vars = generate_new_var(var, line_ind, table_vars, cur_block, rhs)
        table_vars[var.var_name] = var
        variable_list.append(var)
    else:
        lhs, table_vars = generate_new_var(lhs, line_ind, table_vars, cur_block, rhs)
        table_vars[lhs.var_name] = lhs
        variable_list.append(lhs)
    rhs = map_variable(rhs, table_vars)
    if isinstance(rhs, VariableExprAST):
        rhs.mark_parent_AST(lhs)

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
    top_var_list = {}
    top_expr = []

    # create variable tables to record the variable usage
    table_vars = {}
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

        cur_block = AST_nodes[-1] if len(AST_nodes) else None

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

        if ind == 76:
            pass
        AST, variable_list, table_vars = parse_primary_expr(
            line, ind, variable_list, table_vars, cur_block
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

    # append the last variable list to the top_var_list in case no end match the
    # function declaration
    if len(AST_nodes) > 0 and (AST_nodes[-1] not in top_var_list):
        top_var_list[AST_nodes[-1]] = variable_list
    return top_var_list, top_expr


var_list, expr_list = analyze_var_usage(
    "../src_paper/src/pan_tompkin_algorithm_segmented.m"
)
if __name__ == "__main__":
    import os

    code_dir = "../src_paper/src"
    for file_dir in os.listdir(code_dir):
        if file_dir.endswith(".m"):
            if (
                file_dir
                == "additional_fill_in_FeaturesData_Train_Test.m"
                # or file_dir == "fill_in_FeaturesData_Train_Test.m"
            ):
                continue
            if (
                "feature" in file_dir
                or "Feature" in file_dir
                or "Lorenz" in file_dir
                or "calc" in file_dir
            ):
                print("processing file: ", file_dir)
                analyze_var_usage(os.path.join(code_dir, file_dir))
