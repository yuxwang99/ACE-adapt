from graphviz import Digraph
from parse import parse


def traverse_call_graph(node, graph):
    for child in node.child_nodes:
        graph.node(child.func_name, child.func_name)
        graph.edge(node.func_name, child.func_name)
        traverse_call_graph(child, graph)


def get_var_name(var) -> None:
    if var.isidentifier():
        return var, None
    else:
        r = parse("{var_name}({index})", var)
        if r is not None:
            return r.named["var_name"], "(" + r.named["index"] + ")"

    # TODO: check whether the var is constant
    # raise ValueError("The variable name is not valid.")
    return var, None


def get_cnt_pair(node, connection):
    cnt_pair = {}
    for key, cnts in connection.items():
        # a variable can be passed to multiple child nodes
        # or used by a child node multiple times
        for conn in cnts:
            if conn[0] == node.func_name:
                if key in cnt_pair.keys():
                    cnt_pair[key].append(conn[1])
                else:
                    cnt_pair[key] = [conn[1]]

    return cnt_pair


def traverse_call_graph_var(
    node, graph, back_trace=False, parent_sub=None, from_par_cnt={}, to_par_cnt={}
):
    # plot nodes to represent variables
    with graph.subgraph(name="cluster_" + node.func_name) as sub:
        sub.attr(label=node.func_name)
        type = ["in", "out", "cnt"]
        init_type_nodes = [node.input_vars, node.output_vars, node.cnt_vars_children]
        colors = [
            "#CBD6E2",
            "#4FB99F",
            "#EBB8DD",
        ]  # light gray, light green, light pink
        for ind, init_type in enumerate(init_type_nodes):
            # init nodes in each type
            for var in init_type:
                var_name, op = get_var_name(var)
                sub.node(
                    type[ind] + "_" + str(node.func_name) + "_" + var_name,
                    var_name,
                    fillcolor=colors[ind],
                    style="filled",
                )

    # create nodes to in parent nodes to receive the return values
    if back_trace:
        for _, parent_var in node.cnt_vars_parents.items():
            for var in parent_var:
                var_name, _ = get_var_name(var[1])
                if var_name == "~":
                    continue
                with graph.subgraph(name=parent_sub.name) as parent_sub:
                    parent_sub.node(
                        "cnt_" + var[0] + "_" + var_name,
                        var_name,
                        fillcolor="#EBB8DD",  # light pink
                        style="filled",
                    )

    # plot edges to connect variables
    if parent_sub is not None:
        parent_prefix = parent_sub.name[len("cluster_") :]
        for parent_var, children_vars in from_par_cnt.items():
            parent_var_name, op = get_var_name(parent_var)
            for child in children_vars:
                if op is None:
                    graph.edge(
                        "cnt_" + parent_prefix + "_" + parent_var_name,
                        "in_" + str(node.func_name) + "_" + child,
                    )
                else:
                    graph.edge(
                        "cnt_" + parent_prefix + "_" + parent_var_name,
                        "in_" + str(node.func_name) + "_" + child,
                        label=op,
                    )

    if parent_sub is not None and back_trace:
        for children_var, parent_vars in to_par_cnt.items():
            for parent_var in parent_vars:
                parent, op = get_var_name(parent_var)
                if parent == "~":
                    continue
                if op is None:
                    graph.edge(
                        "out_" + str(node.func_name) + "_" + children_var,
                        "cnt_" + parent_prefix + "_" + parent,
                        color="blue",
                        style="dashed",
                    )
                # consider non direct output
                else:
                    graph.edge(
                        "out_" + str(node.func_name) + "_" + children_var,
                        "cnt_" + parent_prefix + "_" + parent,
                        label=op,
                        color="blue",
                        style="dashed",
                    )

    # iterate over child nodes
    for child in node.child_nodes:
        cnt_child = get_cnt_pair(child, node.cnt_vars_children)
        cnt_parent = get_cnt_pair(node, child.cnt_vars_parents)
        traverse_call_graph_var(child, graph, back_trace, sub, cnt_child, cnt_parent)


def call_graph_viz(root_node, graph_name="call_graph", via_var=False, back_prop=False):
    # Create a new Digraph object
    graph = Digraph(comment=graph_name)
    if via_var:
        traverse_call_graph_var(root_node, graph, back_prop)
    else:
        traverse_call_graph(root_node, graph)
    graph.save(graph_name + ".dot")
    graph.view()
