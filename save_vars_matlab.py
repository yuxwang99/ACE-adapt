import os
from function_tag import remove_cmt_paragraph, parse_list, get_function_attributes
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
    is_cond_line = False
    cond_line_ind = []
    for [ind, line] in enumerate(code_line):
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

        # check if is unfinished line
        if line.strip().endswith("..."):
            cond_line_ind.append(ind)
            is_cond_line = True
        else:
            is_cond_line = False

        if is_cond_line:
            continue

        # empty space to allow it align with the original code
        _, n_empty = remove_empty_space_before_line(line)
        empty_chars = " " * n_empty

        # process the complete line
        pre_line = empty_chars
        for pre_ind in cond_line_ind:
            pre_line = pre_line + code_line[pre_ind].strip(". ") + " "
        line = pre_line + line.strip()
        cond_line_ind = []

        left_expr, right_expr = split_left_right(line)

        # process input variables in function definition
        if "function" in left_expr:
            attr = get_function_attributes(right_expr)
            if attr is not None:
                for input_var in attr[1]:
                    if input_var not in call_pattern["cnt_vars_children"]:
                        continue
                    # if need to save the variables, add save cmd
                    save_cmd = "    save('{}', '{}');\n".format(
                        os.path.join(folder_dir, func_name + "_" + input_var),
                        input_var,
                    )
                    # add additional empty line
                    code_with_save += save_cmd

        # process the internal variables
        else:
            output_vars = parse_list(left_expr)
            # The function call can generate multiple outputs
            for output_var in output_vars:
                if output_var not in call_pattern["cnt_vars_children"]:
                    continue
                # if need to save the variables, add save cmd
                save_cmd = empty_chars + "if ~any(isnan({}))\n".format(output_var)
                save_cmd += empty_chars + "    save('{}', '{}');\n".format(
                    os.path.join(folder_dir, func_name + "_" + output_var), output_var
                )
                save_cmd += empty_chars + "end\n"
                # add additional empty line
                code_with_save += save_cmd

    return code_with_save


if __name__ == "__main__":
    import argparse
    import os
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--call_pattern", required=True, help="Json file for function call pattern"
    )
    parser.add_argument(
        "--codedir", required=True, help="Path to the analyze code directory"
    )
    parser.add_argument(
        "--newdir",
        required=True,
        help="Path to the folders that store the generated .m file with variables code",
    )
    args = parser.parse_args()
    call_pattern = args.call_pattern
    code_dir = args.codedir
    new_code_dir = args.newdir

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
        elif os.path.isfile(os.path.join(code_dir, file_dir)):
            # copy the file to the new folders
            os.system("cp {} {}".format(os.path.join(code_dir, file_dir), new_code_dir))
