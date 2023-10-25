# - save_vars_matlab.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Generate matlab variable save and load code - - - - - - - - - - - - - - - - - - - - #
import os
from function_tag import parse_list, get_function_attributes
from utils.line import (
    split_left_right,
    remove_empty_space_before_line,
    remove_cmt_in_line,
    remove_empty_space_before_line,
    skip_line,
    merge_line,
)
from var_usage_analysis import analyze_var_usage
from utils.expr_class import SliceExprAST, CallExprAST

INCLASS_PATH = "/Users/yuxuan/Projects/23 fall/INCLASS/src_paper"


def generate_save_cmd(orig_code, proces_func, folder_dir, empty_chars=""):
    left_expr = orig_code.split("=")[0].strip()
    output_vars = parse_list(left_expr)
    save_cmd = ""
    # detect whether the variable is saved in cache
    for output_var in output_vars:
        if output_var == "~":
            continue
        if save_cmd == "":
            save_cmd += empty_chars + "if isfile('{}')\n".format(
                os.path.join(folder_dir, proces_func + "_" + output_var + ".mat")
            )
        else:
            save_cmd += empty_chars + "and isfile('{}')\n".format(
                os.path.join(folder_dir, proces_func + "_" + output_var + ".mat")
            )

    # load the variable from the cache
    for output_var in output_vars:
        if output_var == "~":
            continue
        save_cmd += empty_chars + "    load('{}');\n".format(
            os.path.join(folder_dir, proces_func + "_" + output_var + ".mat")
        )
    # save_cmd += empty_chars + "    fprintf('%s\\n', 'load {}');\n".format(output_vars)
    save_cmd += empty_chars + "else\n"
    save_cmd += "    " + orig_code + "\n"
    save_cmd += empty_chars + "    save('{}', '{}');\n".format(
        os.path.join(folder_dir, proces_func + "_" + output_var), output_var
    )
    save_cmd += empty_chars + "end\n"
    # add additional empty line
    return save_cmd


def save_vars_in_matlab(
    file_dir: str,
    save_var_list: list,
    folder_dir: str = os.path.join(INCLASS_PATH, "cache_data"),
):
    """
    Generate the variable save code in matlab

    Args:
        file_name: the name of the file to process
        call_pattern: the function call pattern

    Return:
        save_cmd: the command to save the variables and add save cmd after the function call
    """

    try:
        with open(file_dir, "r") as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        raise ValueError(f"The file '{file_dir}' was not found.")

    # ignore the comments enclosed in %{ ... }%
    code_line = file_contents.split("\n")
    code_with_save = ""
    line_state = -1
    cond_line_ind = []
    # file_contents = remove_cmt_paragraph(file_contents)
    func_name = file_dir.split("/")[-1][:-2]  # remove the .m

    rewrite_line = []
    for var in save_var_list:
        rewrite_line.append(var._attr["line"])

    for [ind, line] in enumerate(code_line):
        # copy the original code
        if ind not in rewrite_line:
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
        cond_line_ind = []

        if ind in rewrite_line:
            save_cmd = generate_save_cmd(line, func_name, folder_dir)
            code_with_save += save_cmd

    return code_with_save


def is_once_called_func(func_dir: str, call_pattern: dict, parent_func=[]):
    # The variable propated to its children function can be regarded as constant if it is
    # produced once under the following conditions:
    # 1. it is not in a loop, or
    # 2. it is in and only in one if clause
    func_called = []
    block_expr, blocks = analyze_var_usage(func_dir)
    top_block = blocks[0]

    # Iterate over the block in each file, e.g. function definition.
    for _, var_list in block_expr.items():
        # Iterate over the variables in each block
        for var in var_list:
            # Exclude variables that are not attached in the top level block
            if var.get_block() != top_block:
                continue
            for _, expr in var.production.items():
                if isinstance(expr, CallExprAST) and expr.func_name in call_pattern:
                    if expr.func_name == "calculate_idxs_from_mask":
                        continue
                    if expr.func_name not in func_called:
                        func_called.append(expr.func_name)
                    else:
                        rep_ind = func_called.index(expr.func_name)
                        func_called.pop(rep_ind)

    # Recursively check the sub-function
    for func in func_called:
        if func in parent_func:
            rep_ind = func_called.index(func)
            parent_func.pop(rep_ind)
        else:
            parent_func.append(func)
            parent_func = is_once_called_func(
                os.path.join(os.path.dirname(func_dir), func + ".m"),
                call_pattern,
                parent_func,
            )
    return parent_func


# select which variables to save
def select_top_level_used_vars(
    block_expr,
    top_block,
    valid_save_func: list,
):
    save_var_list = []
    for block, var_list in block_expr.items():
        # Exclude variables that are used in the slice expression
        for var in var_list:
            if isinstance(var, SliceExprAST):
                continue
            # Exclude the input variables
            if var._varAttr == 1:
                continue
            # Exclude variables that are not used
            if len(var.usage) == 0:
                continue
            # Exclude variables that are not attached in the top level block
            if var.get_block() != top_block:
                continue
            for slice, expr in var.production.items():
                if isinstance(expr, CallExprAST) and expr.func_name in valid_save_func:
                    if expr.func_name == "calculate_idxs_from_mask":
                        continue
                    print("save var: ", var.var_name)
                    save_var_list.append(var)
    return save_var_list


if __name__ == "__main__":
    import argparse
    import os
    import json

    call_pattern = "./function_call_pattern.json"
    with open(call_pattern, "r") as file:
        call_pattern = json.load(file)
    func_call = "../src_paper/src/my_Extract_features_Jep.m"
    process_func_list = is_once_called_func(
        func_call, call_pattern, ["my_Extract_features_Jep"]
    )

    code_dir = "../src_paper/src"
    new_code_dir = "../src_paper/src_new"
    # first copy all .m file to the new folder
    for file_dir in os.listdir(code_dir):
        func_name = file_dir[:-2]
        if not file_dir.endswith(".m"):
            continue
        if os.path.isfile(os.path.join(code_dir, file_dir)):
            # copy the file to the new folders
            os.system(
                "cp {} {}".format(
                    os.path.join(code_dir, file_dir),
                    os.path.join(new_code_dir, file_dir),
                )
            )

    # re-write the script that need to save the variables
    for func in process_func_list:
        print(func)
        root_dir = "../src_paper/src/"
        var_list, expr_list = analyze_var_usage(os.path.join(root_dir, func + ".m"))
        save_var_list = select_top_level_used_vars(
            var_list, top_block=expr_list[0], valid_save_func=process_func_list
        )
        if len(save_var_list) > 0:
            save_cmd = save_vars_in_matlab(
                os.path.join(root_dir, func + ".m"), save_var_list
            )
            # save the matlab code
            gen_code = open(os.path.join(new_code_dir, func + ".m"), "wt")
            gen_code.write(save_cmd)
            gen_code.close()
