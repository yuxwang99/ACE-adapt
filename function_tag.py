from parse import parse
import warnings
from utils.parser.line import (
    generate_valid_code_line,
    remove_cmt_paragraph,
    remove_cmt_in_line,
)


# Remove leading and trailing whitespace
def get_valid_identifier(word: str):
    strpped_word = word.strip()
    if strpped_word.isidentifier():
        return strpped_word

    return strpped_word


# parse a string split by comma and return the elements
def parse_list(list_str: str):
    list_str = list_str.strip("; ")
    list_str = remove_cmt_in_line(list_str)
    while list_str.startswith("{") or list_str.startswith("["):
        list_str = list_str[1:-1]

    # Initialize variables
    elements = []
    current_element = ""
    brackets = []

    # Iterate through the input string character by character
    for char in list_str:
        if char == "(" or char == "[" or char == "{":
            brackets.append(char)
        elif char == ")":
            brackets.pop()

        if char == "," and len(brackets) == 0:
            # Found a comma outside of brackets, consider it as a separator
            elements.append(current_element.strip())
            current_element = ""
        else:
            current_element += char

    # Add the last element
    if current_element:
        elements.append(current_element.strip())

    return elements


# Return the function name, input variables, and output variables
def get_function_attributes(expr: str, definition=False) -> None:
    expr = expr.strip()
    if expr == "":
        return None

    if expr[-1] == ";":
        expr = expr[:-1]
    if definition:
        r = parse("function {output}={func_name}({input})", expr)
    else:
        # get function attributes when call it
        r1 = parse("{output}={func_name}({input})", expr)
        r2 = parse("{func_name}({input})", expr)
        r = r1 if r1 is not None else r2
    if r is not None:
        func_name = get_valid_identifier(r.named["func_name"])
        if not func_name.isidentifier():
            return None

        tmp_input_vars = r.named["input"]
        if tmp_input_vars.isidentifier():
            input_vars = [tmp_input_vars]
        else:
            input_vars = parse_list(tmp_input_vars)

        if "output" not in r.named:
            return func_name, input_vars, []
        else:
            tmp_ouput_vars = r.named["output"]
            if tmp_ouput_vars.isidentifier():
                output_vars = [tmp_ouput_vars]
            else:
                output_vars = parse_list(tmp_ouput_vars)

        return func_name, input_vars, output_vars


# Tag the function attributes of a Matlab function file
def tag_func(func_dir: str, prefix=""):
    try:
        with open(func_dir, "r") as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        print(f"The file '{func_dir}' was not found.")

    # ignore the comments enclosed in %{ ... }%
    file_contents = remove_cmt_paragraph(file_contents)
    if file_contents == "":
        warnings.warn("No function is found in {}".format(func_dir))
        return [""] * 3

    # process the keyword 'function'
    for line in generate_valid_code_line(file_contents):
        attrs = get_function_attributes(line, definition=True)
        if attrs:
            func_name, input_vars, output_vars = attrs
            if prefix != "":
                func_name = prefix + "/" + func_name

            return func_name, input_vars, output_vars

    return [""] * 3


if __name__ == "__main__":
    import argparse
    import os
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--codedir", required=True, help="Path to the code directory")
    parser.add_argument(
        "--subdir",
        required=False,
        action="append",
        default=[],
        help="Path to the code directory",
    )
    parser.add_argument(
        "--outdir", required=True, help="Path to store the output json analysis file"
    )
    args = parser.parse_args()

    code_dir = args.codedir
    subdir = args.subdir
    out_dir = args.outdir

    subdir.append(".")  # add current directory

    function_attributes = {}

    for sub_folder in subdir:
        for file_dir in os.listdir(os.path.join(code_dir, sub_folder)):
            if not file_dir.endswith(".m"):
                continue

            if sub_folder == ".":
                cur_file = os.path.join(code_dir, file_dir)
                prefix = ""
                print("processing file: ", cur_file)
            else:
                print("processing file in subfolder: ", sub_folder + "/" + file_dir)
                cur_file = os.path.join(code_dir, sub_folder, file_dir)
                prefix = sub_folder

            func_name, input_vars, output_vars = tag_func(cur_file, prefix=prefix)
            if not func_name:
                continue
            func_attr = {func_name: {"input": input_vars, "output": output_vars}}
            function_attributes = {**function_attributes, **func_attr}
            print("done =====\n")

    with open(out_dir, "w") as outfile:
        json.dump(function_attributes, outfile, indent=4)
