import os
from function_tag import remove_cmt_paragraph, parse_list
from utils.line import split_left_right, remove_empty_space_before_line

INCLASS_PATH = "/Users/yuxuan/Projects/23 fall/INCLASS/src_paper"


def save_vars_in_matlab(
    file_dir: str,
    call_pattern: dict,
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
    file_contents = remove_cmt_paragraph(file_contents)
    func_name = file_dir.split("/")[-1][:-2]  # remove the .m

    code_with_save = ""
    is_line_cmt = False
    is_par_cmt = False
    for [ind, line] in enumerate(code_line):
        # TODO: handle the case when the line is split by "..." when it is too long
        # TODO: handle the storage for the input variables
        code_with_save += line + "\n"

        # check if is comment
        if line.strip().startswith("%"):
            is_line_cmt = True
        elif line.strip().startswith("%{"):
            is_par_cmt = True
        elif line.strip().endswith("%}"):
            is_par_cmt = False
        else:
            is_line_cmt = False

        if is_line_cmt or is_par_cmt:
            continue

        # attrs = get_function_attributes(line, definition=True)
        left_expr, _ = split_left_right(line)

        # empty space to allow it align with the original code
        _, n_empty = remove_empty_space_before_line(line)
        empty_chars = " " * n_empty

        output_vars = parse_list(left_expr)
        # The function call can generate multiple outputs
        for output_var in output_vars:
            if output_var in call_pattern["cnt_vars_children"]:
                # if need to save the variables, add save cmd
                save_cmd = empty_chars + "if ~any(isnan({}))\n".format(output_var)
                save_cmd += empty_chars + "    save('{}', '{}');\n".format(
                    os.path.join(folder_dir, func_name + "_" + output_var), output_var
                )
                save_cmd += empty_chars + "end\n"
                # add additional empty line
                code_with_save += save_cmd

    return code_with_save


import json

demo = True
# TODO: create parser for command line
# jsonfile for function call analysis
call_pattern = "./function_call_pattern.json"
code_dir = "../src_paper/src/"
new_code_dir = "../src_paper/src_new/"
if demo:
    call_pattern = "./exp_script/function_call_pattern.json"
    code_dir = "./exp_script/"
    new_code_dir = "./exp_script/new/"
# Open the JSON file for reading
with open(call_pattern, "r") as file:
    call_pattern = json.load(file)

for file_dir in os.listdir(code_dir):
    func_name = file_dir[:-2]
    if file_dir.endswith(".m") and func_name in call_pattern:
        print("processing file: ", file_dir)
        save_cmd = save_vars_in_matlab(
            os.path.join(code_dir, file_dir), call_pattern[func_name]
        )
        # save the matlab code
        gen_code = open(os.path.join(new_code_dir, file_dir), "wt")
        gen_code.write(save_cmd)
        gen_code.close()
    else:
        # copy the file to the new folders
        os.system("cp {} {}".format(os.path.join(code_dir, file_dir), new_code_dir))
