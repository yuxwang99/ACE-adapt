import os
from function_tag import parse_list
from utils.parser.line import (
    remove_empty_space_before_line,
    remove_cmt_in_line,
    remove_empty_space_before_line,
    skip_line,
    merge_line,
)
from utils.parser.expr_class import VariableExprAST, CallExprAST

INCLASS_PATH = "/Users/yuxuan/Projects/23 fall/INCLASS/src_paper"


def is_mask_related_func(
    func: CallExprAST, mask_compute_funcname="calculate_idxs_from_mask"
) -> bool:
    """Determine whether the function is related to the mask computation"""

    if func.func_name == mask_compute_funcname:
        return True

    for in_arg in func.args:
        if isinstance(in_arg, VariableExprAST) and ("mask" in in_arg.var_name):
            return True

    return False


def generate_save_cmd(orig_code, proces_func, folder_dir, empty_chars=""):
    """
    Generate the save command in matlab

    Args:
        orig_code (str): original matlab code
        proces_func (str): processed function name
        folder_dir (str): directory of the folder to save the useful data
        empty_chars (str, optional): empty chars before the orignal code. Defaults to "".

    Returns:
        str: save command

    Example:
        orig_code = "y = user_f(x)"

        Return
            if isfile('cache_data/user_f_y.mat')
                load('cache_data/user_f_y.mat');
            else
                y = user_f(x);
                save('cache_data/user_f_y.mat', 'y');
            end
    """
    left_expr = orig_code.split("=")[0].strip()
    output_vars = parse_list(left_expr)
    save_cmd = ""

    if_clause = ""
    for output_var in output_vars:
        if output_var == "~":
            continue

        if if_clause:
            if_clause += " || "

        if_clause += f"ctrl_vec(get_var_index('{output_var}'))"

    save_cmd += f"if {if_clause}\n"
    save_cmd += orig_code + "\n"

    # not allowed write anymore
    for output_var in output_vars:
        if output_var == "~":
            continue

        # if exists, load the file
        # save_cmd += empty_chars + f"    {output_var}_g = {output_var};\n"
        save_cmd += empty_chars + f"    ctrl_vec(get_var_index('{output_var}'))=0;\n"

    # otherwise, read from the pre-computed
    # save_cmd += empty_chars + "else\n"

    # # further save the result
    # save_cmd += (
    #     empty_chars
    #     + "    "
    #     + "    save('{}.mat', ...\n ".format(
    #         os.path.join(folder_dir, proces_func + var_file_name)
    #     )
    # )

    # for output_var in output_vars:
    #     if output_var == "~":
    #         continue
    #     save_cmd += empty_chars + f"    {output_var} = {output_var}_g;\n"

    # save_cmd = save_cmd[:-2]  # remove the last comma
    # save_cmd += ");\n"
    save_cmd += empty_chars + "end\n"

    return save_cmd


def is_rewrite_line(lines, start_ind, rewrite_line):
    """Determine whether the line needs to be rewritten"""
    for [ind, line] in enumerate(lines):
        if not line.endswith("..."):
            return start_ind + ind in rewrite_line
    return False


def save_vars_in_matlab(
    file_dir: str,
    save_var_list: list,
    folder_dir: str = os.path.join(INCLASS_PATH, "cache_data"),
    maximum_looklen=10,
):
    """
    Generate the variable save code in matlab

    Args:
        file_name: the name of the file to process
        call_pattern: the function call pattern
        maximum_looklen: maximum number of lines to look ahead

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
    func_defined = False
    # file_contents = remove_cmt_paragraph(file_contents)
    func_name = file_dir.split("/")[-1][:-2]  # remove the .m

    rewrite_line = []
    global_vars = []
    for var in save_var_list:
        rewrite_line.append(var._attr["line"])
        global_vars.append(var.var_name)

    for [ind, line] in enumerate(code_line):
        if func_defined:
            code_with_save += "global ctrl_vec;\n"
            global_declare = ["global " + item + ";" for item in global_vars]
            code_with_save += "\n".join(global_declare)
            func_defined = False
        # copy the original code
        if not is_rewrite_line(
            code_line[ind : ind + maximum_looklen], ind, rewrite_line
        ):
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

        if line.strip().startswith("function"):
            func_defined = True

        if ind in rewrite_line:
            save_cmd = generate_save_cmd(line, func_name, folder_dir)
            code_with_save += save_cmd

    return code_with_save
