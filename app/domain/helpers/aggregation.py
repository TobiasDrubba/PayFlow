def build_sankey_data(result: dict, metadata: dict, category_tree: dict):
    """
    Build Sankey diagram nodes and links from aggregation result and category tree.
    Exclude nodes with value 0 and links to/from such nodes.
    If a node has a negative value, create a link from child to parent.
    """
    nodes = []
    node_map: dict = {}  # Add type annotation
    idx = 0

    def add_node(name):
        nonlocal idx
        if name in node_map:
            return node_map[name]
        value = 0
        if name == "Total Expenses":
            value = metadata["Total Expenses"]
        elif name in result:
            value = result[name]
        nodes.append({"name": name, "value": value})
        node_map[name] = idx
        idx += 1
        return node_map[name]

    add_node("Total Expenses")

    links = []

    def traverse(tree, parent):
        if tree is None:
            return
        for k, v in tree.items() if isinstance(tree, dict) else []:
            add_node(k)
            value = result.get(k, 0)
            if value > 0:
                links.append(
                    {"source": node_map[parent], "target": node_map[k], "value": value}
                )
            elif value < 0:
                links.append(
                    {
                        "source": node_map[k],
                        "target": node_map[parent],
                        "value": abs(value),
                    }
                )
            if isinstance(v, dict):
                traverse(v, k)

    for top_cat in category_tree or {}:
        add_node(top_cat)
        value = result.get(top_cat, 0)
        if value > 0:
            links.append(
                {
                    "source": node_map["Total Expenses"],
                    "target": node_map[top_cat],
                    "value": value,
                }
            )
        elif value < 0:
            links.append(
                {
                    "source": node_map[top_cat],
                    "target": node_map["Total Expenses"],
                    "value": abs(value),
                }
            )
        traverse(category_tree[top_cat], top_cat)

    for special in ["no category", "invalid category"]:
        val = result.get(special, 0)
        if val > 0:
            add_node(special)
            links.append(
                {
                    "source": node_map["Total Expenses"],
                    "target": node_map[special],
                    "value": val,
                }
            )
        elif val < 0:
            add_node(special)
            links.append(
                {
                    "source": node_map[special],
                    "target": node_map["Total Expenses"],
                    "value": abs(val),
                }
            )

    # Filter out nodes with value 0
    filtered_nodes = [n for n in nodes if n["value"] != 0]
    valid_names = set(n["name"] for n in filtered_nodes)
    # Map node name to new index
    name_to_new_idx = {n["name"]: i for i, n in enumerate(filtered_nodes)}

    # Filter links to only those whose source and target are in valid_names
    filtered_links = []
    for link in links:
        src_name = None
        tgt_name = None
        # Find names by old idx
        for name, old_idx in node_map.items():
            if old_idx == link["source"]:
                src_name = name
            if old_idx == link["target"]:
                tgt_name = name
        if src_name in valid_names and tgt_name in valid_names:
            filtered_links.append(
                {
                    "source": name_to_new_idx[src_name],
                    "target": name_to_new_idx[tgt_name],
                    "value": link["value"],
                }
            )

    return {"nodes": filtered_nodes, "links": filtered_links}
