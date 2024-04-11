from graphviz import Digraph
from parse import parse


def traverse_call_graph(node, graph, simplify=True):
    if simplify:
        graph.node(node.func_name, shape="point")
    else:
        graph.node(node.func_name, node.func_name)
    for child in node.child_nodes:
        graph.edge(node.func_name, child.func_name, arrowsize="0.3")
        traverse_call_graph(child, graph, simplify=simplify)


def call_graph_viz(root_node, visual_method, graph_name="call_graph"):
    # Create a new Digraph object
    graph = Digraph(comment=graph_name)
    traverse_call_graph(root_node, graph, visual_method==1)
    graph.save(graph_name + ".dot")
    graph.view()
