from koza.model.biolink import Association, NamedThing


class KGXConverter:
    """
    Converts the biolink model to the KGX format, which splits
    data into nodes (Entity) and edges (Association)

    This format is designed around labelled property graphs
    that allow for scalar and lists as properties (Neo4J)

    https://github.com/biolink/kgx/blob/master/specification/kgx-format.md

    """

    def convert(self, *args) -> (dict, dict):

        nodes = []
        edges = []

        for entity in args:
            if isinstance(entity, NamedThing):
                nodes.append(vars(entity))
            elif isinstance(entity, Association):
                edges.append(vars(entity))

        return nodes, edges
