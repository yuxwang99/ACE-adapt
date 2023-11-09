from graphviz import Digraph
from parse import parse


def traverse_call_graph(node, graph):
    for child in node.child_nodes:
        graph.node(child.func_name, child.func_name)
        graph.edge(node.func_name, child.func_name)
        traverse_call_graph(child, graph)


def call_graph_viz(root_node, graph_name="call_graph"):
    # Create a new Digraph object
    graph = Digraph(comment=graph_name)
    traverse_call_graph(root_node, graph)
    graph.save(graph_name + ".dot")
    graph.view()
