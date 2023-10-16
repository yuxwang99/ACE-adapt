# - function_call_analysis.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Parse the Matlab code and analyze the sub-function call pattern - - - - - - - - - - #
from parse import parse
import os
from utils.line import generate_valid_code_line, split_left_right
from utils.visualization import call_graph_viz
from function_tag import remove_cmt_paragraph, parse_list, get_function_attributes
from var_usage_analysis import analyze_var_usage
from save_vars_matlab import select_top_level_used_vars


class FunctionCall:
    """
    FunctionCall implements a function node that includes the function name,
    input variables, output variables, and the connection to the parent and child nodes.
    """

    def __init__(self, func_name, input_vars=[], output_vars=[]):
        self.func_name = func_name
        self.input_vars = input_vars
        self.output_vars = output_vars
        self.cnt_vars_parents = {}
        self.cnt_vars_children = {}

        self.child_nodes = []
        self.parent_nodes = []

    def add_child_node(self, child_func, local_vars=[], child_var_names=[]):
        """
        Connect the child node to the current node
        Args:
            child_func: the child node
            local_vars: internal variables
            child_var_names: variable names w.r.t the child node in the same order as local_vars
        """
        self.child_nodes.append(child_func)
        if len(local_vars) > len(child_var_names):
            raise ValueError("The number of variables does not match.")
        for ind, var in enumerate(local_vars):
            if var in self.cnt_vars_children.keys():
                self.cnt_vars_children[var].append(
                    (child_func.func_name, child_var_names[ind])
                )
            else:
                self.cnt_vars_children[var] = [
                    (child_func.func_name, child_var_names[ind])
                ]

    def add_parent_node(
        self, parent_func, local_vars=[], parent_var_names=[], top_output=""
    ):
        """
        Connect the parent node to the current node
        Args:
            parent_func: the parent node local_vars: internal variables
            parent_var_names: variable names w.r.t the parent node in the same order as local_vars
            top_output: the top level output variable names as the parent var names when the call pattern is nested
        """
        self.parent_nodes.append(parent_func)
        if len(parent_var_names) > len(self.output_vars):
            raise ValueError("The number of variables does not match.")
        for ind, var in enumerate(local_vars):
            if var in self.cnt_vars_parents.keys():
                self.cnt_vars_parents[var].append(
                    (parent_func.func_name, parent_var_names[ind])
                )
            else:
                if len(parent_var_names) == 0:
                    self.cnt_vars_parents[var] = [
                        # differs from direct output
                        (parent_func.func_name, top_output[ind] + "(@)")
                    ]
                else:
                    self.cnt_vars_parents[var] = [
                        (parent_func.func_name, parent_var_names[ind])
                    ]


def is_function_call(line: str) -> bool:
    expr = line.strip()
    if expr == "":
        return False

    if expr[-1] == ";":
        expr = expr[:-1]

    if (
        expr.startswith("if")
        or expr.startswith("while")
        or expr.startswith("for")
        or expr.startswith("elseif")
    ):
        return False

    r1 = parse("{output}={func_name}({input})", expr)
    r2 = parse("{func_name}({input})", expr)
    r = r1 if r1 is not None else r2
    if r is not None:
        func_name = r.named["func_name"].strip()
        return func_name.isidentifier()

    return False


def decompose_nested_function_call(line: str):
    """
    Decompose the nested expression in a line, and return the decomposed
    expression split by () without ";"
    e.g.
    Args
        line:
              "Slope=abs(my_slope(tHRV(i-x0+1:i),RR_Interv(i-x0+1:i)));"

    Returns
        map_table:
              {'#0': 'tHRV(i-x0+1:i)',
               '#1': 'RR_Interv(i-x0+1:i)',
               '#2': 'my_slope(#0,#1)',
               '#3': 'abs(#2)'}
        final_call: 'Slope=#3'
    """
    expr_stack = []
    map_table = {}

    pre_word = ""
    pos_bracket = []
    for char in line:
        if (pre_word + char).isidentifier():
            pre_word = pre_word + char
        elif char != " ":
            if pre_word != ")":
                expr_stack.append(pre_word)
            if char == "(":
                pos_bracket.append(len(expr_stack))

            if char == ")":
                expr = ""
                for var in expr_stack[pos_bracket[-1] - 1 :]:
                    expr = expr + var
                expr_stack = expr_stack[: pos_bracket[-1] - 1]
                expr_stack.append("#" + str(len(map_table)))
                map_table["#" + str(len(map_table))] = expr + ")"
                pos_bracket = pos_bracket[:-1]

            pre_word = char
    if pre_word != ")" and pre_word != ";":
        expr_stack.append(pre_word)

    final_call = ""
    for exp in expr_stack:
        final_call = final_call + exp
    return map_table, final_call


def compose_nested_function_call(input_string, replace_map):
    """
    Compose the nested expression, and return the composed
    expression by replacing the pre-computed results in the replace_map
    e.g.

    Args:
        input_string :input_string = "Slope=#3"

    Returns
        replace_map:
              {'#0': 'tHRV(i-x0+1:i)',
               '#1': 'RR_Interv(i-x0+1:i)',
               '#2': 'my_slope(#0,#1)',
               '#3': 'abs(#2)'}
              "Slope=abs(my_slope(tHRV(i-x0+1:i),RR_Interv(i-x0+1:i)));"
        input_string: "Slope=abs(my_slope(tHRV(i-x0+1:i),RR_Interv(i-x0+1:i)))"
    """
    while True:
        found = False
        for key, value in replace_map.items():
            placeholder = f"{key}"
            if placeholder in input_string:
                input_string = input_string.replace(placeholder, value)
                found = True
        if not found:
            break
    return input_string


def get_call_pattern(line: str):
    if not is_function_call(line):
        return [], None

    left_expr, right_expr = split_left_right(line)
    call_map, final_expr = decompose_nested_function_call(right_expr)

    nested_attrs = []

    # handle the top most function call
    # first get the output variable names from the left expression
    output_var_names = parse_list(left_expr)
    attr = get_function_attributes(compose_nested_function_call(final_expr, call_map))
    func_name = attr[0] if attr is not None else ""

    # handle the nested function calls
    for _, value in call_map.items():
        # get func_name, input_vars, output_vars
        attr = get_function_attributes(value)
        if attr is not None:
            if attr[0] == func_name:
                attr[2].extend(output_var_names)

            for i in range(len(attr[1])):
                attr[1][i] = compose_nested_function_call(attr[1][i], call_map)
            nested_attrs.append(attr)

    top_level_output = output_var_names
    return nested_attrs, top_level_output


def function_called(func_name: str, callee: list) -> None:
    for func in callee:
        if func.func_name == func_name:
            return func


def call_analysis(
    func_dir: str,
    function_attributes: dict,
    func_list=[],
    parent_func=None,
    input_var_callnames=[],
    output_var_callnames=[],
    top_output=None,
):
    try:
        with open(func_dir, "r") as file:
            # Read the contents of the file
            file_contents = file.read()
    except FileNotFoundError:
        raise ValueError(f"The file '{func_dir}' was not found.")

    # ignore the comments enclosed in %{ ... }%
    file_contents = remove_cmt_paragraph(file_contents)
    root_dir, filename = os.path.split(func_dir)

    # initialize the function
    input_vars = []
    output_vars = []
    if filename[:-2] in function_attributes.keys():
        input_vars = function_attributes[filename[:-2]]["input"]
        output_vars = function_attributes[filename[:-2]]["output"]

    function = function_called(filename[:-2], func_list)
    if function is None:
        function = FunctionCall(filename[:-2], input_vars, output_vars)
        func_list.append(function)

    if parent_func is not None:
        parent_func.add_child_node(function, input_var_callnames, input_vars)
        function.add_parent_node(
            parent_func, output_vars, output_var_callnames, top_output
        )

    for line in generate_valid_code_line(file_contents):
        # skip the function definition
        if line.strip().startswith("function"):
            continue
        call_patern, top_output = get_call_pattern(line)
        for attr in call_patern:
            sub_func = attr[0]
            left_expr = attr[2]
            input_var_names = attr[1]
            if sub_func in function_attributes.keys():
                call_analysis(
                    os.path.join(root_dir, sub_func + ".m"),
                    function_attributes,
                    func_list,
                    parent_func=function,
                    input_var_callnames=input_var_names,
                    output_var_callnames=left_expr,
                    top_output=top_output,
                )

    return function


def once_call_analysis(
    file_dir: str,
    call_pattern: dict,
    once_call_list=[],
):
    var_list, expr_list = analyze_var_usage(file_dir)
    save_var_list = select_top_level_used_vars(
        var_list, top_block=expr_list[0], call_pattern=call_pattern
    )
    for var in save_var_list:
        for slice, production in var.production.items():
            call_func = production.func_name
            once_call_list.append(call_func)
            if call_func in call_pattern.keys():
                once_call_analysis(
                    os.path.join(os.path.dirname(file_dir), call_func + ".m"),
                    call_pattern,
                    once_call_list,
                )
    return once_call_list


def save_cnt_map(root_node: FunctionCall, json_map: dict):
    json_key = root_node.func_name
    json_value = {}

    json_value["child_nodes"] = []
    for child_func in root_node.child_nodes:
        json_value["child_nodes"].append(child_func.func_name)

    json_value["parent_nodes"] = []
    for parent_func in root_node.parent_nodes:
        json_value["parent_nodes"].append(parent_func.func_name)

    json_value["input"] = root_node.input_vars
    json_value["output"] = root_node.output_vars
    json_value["cnt_vars_parents"] = root_node.cnt_vars_parents
    json_value["cnt_vars_children"] = root_node.cnt_vars_children

    json_node = {json_key: json_value}
    json_map = {**json_map, **json_node}

    for child_node in root_node.child_nodes:
        json_map = save_cnt_map(child_node, json_map)

    return json_map


if __name__ == "__main__":
    import argparse
    import os
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codedir", required=True, help="Path to the analyze code directory"
    )
    parser.add_argument(
        "--jsontag", required=True, help="Path to the function feature file"
    )
    parser.add_argument(
        "--visualize",
        required=False,
        default=0,
        help="whether to visualize the call graph",
    )
    args = parser.parse_args()
    visualize = int(args.visualize)
    code_dir = args.codedir
    json_tag = args.jsontag

    # Open the JSON file for reading
    with open(json_tag, "r") as file:
        tag_data = json.load(file)

    if code_dir.endswith(".m"):
        print("\nprocessing file: ", code_dir)
        root_node = call_analysis(code_dir, tag_data)
        if visualize > 0:
            if visualize == 1:
                call_graph_viz(root_node, "test1", False, False)
            elif visualize == 2:
                call_graph_viz(root_node, "test2", True, False)
            else:
                call_graph_viz(root_node, "test3", True, True)
        json_file = save_cnt_map(root_node, {})
        with open("./function_call_pattern.json", "w") as outfile:
            json.dump(json_file, outfile, indent=4)
