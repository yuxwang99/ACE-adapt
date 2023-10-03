from parse import parse
import warnings
from utils.line import (
    generate_valid_code_line,
    remove_cmt_paragraph,
)


def get_valid_identifier(word: str):
    # Remove leading and trailing whitespace
    strpped_word = word.strip()
    if strpped_word.isidentifier():
        return strpped_word

    return strpped_word


# parse a string split by comma and return the elements
def parse_list(list_str: str):
    list_str = list_str.strip("{}[] ")

    # Initialize variables
    elements = []
    current_element = ""
    inside_brackets = 0

    # Iterate through the input string character by character
    for char in list_str:
        if char == "(":
            inside_brackets += 1
        elif char == ")":
            inside_brackets -= 1

        if char == "," and inside_brackets == 0:
            # Found a comma outside of brackets, consider it as a separator
            elements.append(current_element.strip())
            current_element = ""
        else:
            current_element += char

    # Add the last element
    if current_element:
        elements.append(current_element.strip())

    return elements


def get_function_attributes(expr: str, definition=False) -> None:
    expr = expr.strip()
    if expr == "":
        return None

    if expr[-1] == ";":
        expr = expr[:-1]
    if definition:
        r = parse("function {output}={func_name}({input})", expr)
    else:
        # TODO: manually parse w.r.t the rules
        # get function attributes when call it
        r1 = parse("{output}={func_name}({input})", expr)
        r2 = parse("{func_name}({input})", expr)
        r = r1 if r1 is not None else r2
    if r is not None:
        func_name = get_valid_identifier(r.named["func_name"])

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


def tag_func(func_dir: str):
    try:
        with open(func_dir, "r") as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        print(f"The file '{func_dir}' was not found.")

    # ignore the comments enclosed in %{ ... }%
    file_contents = remove_cmt_paragraph(file_contents)
    # process the keyword 'function'
    for line in generate_valid_code_line(file_contents):
        if file_contents == "":
            warnings.warn("No function is found in {}".format(func_dir))
            return None, None, None
        attrs = get_function_attributes(line, definition=True)
        if attrs is not None:
            func_name, input_vars, output_vars = attrs
            return func_name, input_vars, output_vars

    return None, None, None


if __name__ == "__main__":
    import argparse
    import os
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--codedir", required=True, help="Path to the code directory")
    args = parser.parse_args()

    code_dir = args.codedir

    function_attributes = {}
    for file_dir in os.listdir(code_dir):
        if file_dir.endswith(".m"):
            print("processing file: ", file_dir)
            func_name, input_vars, output_vars = tag_func(
                os.path.join(code_dir, file_dir)
            )
            if func_name is None:
                continue
            func_attr = {func_name: {"input": input_vars, "output": output_vars}}
            function_attributes = {**function_attributes, **func_attr}
            print("done =====\n")

    with open("./function_attributes.json", "w") as outfile:
        json.dump(function_attributes, outfile, indent=4)