"""Contains a method that creates a partially-connected mesh network topology adapted from [1].

[1] Zilic, Josip, Atakan Aral, and Ivona Brandic. "EFPO: Energy efficient and failure predictive edge offloading."
    Proceedings of the 12th IEEE/ACM International Conference on Utility and Cloud Computing. 2019.
"""

# Python libraries
import random
import sys

# EdgeSimPy components
from ...components.network_link import NetworkLink
from ...components.topology import Topology


def partially_connected_hexagonal_mesh(network_nodes: list, link_specifications: list) -> Topology:
    """Creates a partially-connected mesh network topology.

    Args:
        network_nodes (list): Objects that will be assigned as network nodes.
        link_specifications (list): Technical specifications for the network links.

    Returns:
        topology (object): Created topology
    """
    # Creating topology and creating initial nodes according to the map coordinates
    topology = Topology()
    topology.add_nodes_from(network_nodes)

    # Gathering the list of coordinates of all network nodes
    map_coordinates = [node.coordinates for node in network_nodes]

    # Adding links to each network node
    for i, node in enumerate(network_nodes):
        if i % 100 == 0:
            sys.stdout.write("\r")
            sys.stdout.write(f"{i}/{len(network_nodes)}")
            sys.stdout.flush()
        neighbors = find_neighbors_hexagonal_grid(current_position=node.coordinates, map_coordinates=map_coordinates)

        for neighbor_coordinates in neighbors:
            neighbor = next((n for n in network_nodes if n.coordinates == neighbor_coordinates), None)
            # FIXME: optimize this call ⬆

            if not neighbor:
                raise Exception(f"Cannot find network node with coordinates: {neighbor_coordinates}")

            # Creating network link object
            if not topology.has_edge(node, neighbor):
                link = NetworkLink()
                link.topology = topology

                # List of network nodes connected by the link
                link.nodes = [node, neighbor]

                # Replacing NetworkX's default link dictionary with the NetworkLink object
                topology.add_edge(node, neighbor)
                topology._adj[node][neighbor] = link
                topology._adj[neighbor][node] = link
    sys.stdout.write("\r")
    sys.stdout.flush()

    # Checking if the number of link specifications is equal to the number of links in the network topology
    if len(link_specifications) == 1 and "number_of_objects" not in link_specifications[0]:
        link_specifications[0]["number_of_objects"] = len(topology.edges())
    elif sum([spec["number_of_objects"] for spec in link_specifications]) != len(topology.edges()):
        raise Exception(
            f"You must specify the properties for {len(topology.edges())} links or ignore the 'link_specifications' parameter."
        )

    # Applying the user-specified attributes to the network links
    links = (link for link in random.sample(NetworkLink.all(), NetworkLink.count()))
    for spec in link_specifications:
        for _ in range(spec["number_of_objects"]):
            link = next(links)
            for key, value in spec.items():
                if key != "number_of_objects":
                    link[key] = value

    return topology


def find_neighbors_hexagonal_grid(map_coordinates: list, current_position: tuple) -> list:
    """Finds the set of adjacent positions of coordinates 'current_position' on a hexagonal grid.

    Args:
        map_coordinates (list): List of map coordinates.
        current_position (tuple): Current position on the map.

    Returns:
        neighbors (list): List of neighbor positions on the map.
    """
    x = current_position[0]
    y = current_position[1]

    candidates = [(x - 2, y), (x - 1, y + 1), (x + 1, y + 1), (x + 2, y), (x + 1, y - 1), (x - 1, y - 1)]

    neighbors = [
        neighbor
        for neighbor in candidates
        if neighbor[0] >= 0 and neighbor[1] >= 0 and (neighbor[0], neighbor[1]) in map_coordinates
    ]

    return neighbors
