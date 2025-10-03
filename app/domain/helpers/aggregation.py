from datetime import datetime
from typing import List

from app.domain.helpers.sum import get_signed_amount
from app.domain.models.payment import Payment


def sum_payments_by_category(
    payments: List[Payment], category_tree: dict, start_date=None, end_date=None
):
    """
    Aggregate payment amounts by all categories and parent categories.
    Returns: dict {category_name: sum, "metadata": {...}}
    Adds 'no category' and 'invalid category' keys.
    Metadata includes total sum and invalid categories list.
    """

    def collect_paths(tree, path=None, paths=None):
        if tree is None:
            return paths if paths is not None else []
        if paths is None:
            paths = []
        if path is None:
            path = []
        for k, v in tree.items() if isinstance(tree, dict) else []:
            current_path = path + [k]
            if v is None:
                paths.append(current_path)
            elif isinstance(v, dict):
                if not v:
                    paths.append(current_path)
                else:
                    collect_paths(v, current_path, paths)
        return paths

    # Build all category paths
    all_paths = collect_paths(category_tree)
    # Map leaf to its full path
    leaf_to_path = {}
    for p in all_paths:
        leaf_to_path[p[-1]] = p

    # Prepare result dict for all categories
    result = {}
    for path in all_paths:
        for cat in path:
            result[cat] = 0.0
    result["no category"] = 0.0
    result["invalid category"] = 0.0

    total_sum = 0.0
    invalid_categories_set = set()

    # Filter payments by date if needed
    filtered_payments = []
    # Convert start_date/end_date to date if provided
    sd = start_date.date() if start_date else None
    ed = end_date.date() if end_date else None
    for p in payments:
        # Make p.date naive and get date only
        p_date = p.date.date() if isinstance(p.date, datetime) else p.date
        # Filtering (inclusive)
        if sd and p_date < sd:
            continue
        if ed and p_date > ed:
            continue
        filtered_payments.append(p)

    # Aggregate amounts
    for p in filtered_payments:
        signed_amount = get_signed_amount(p)
        total_sum += signed_amount
        cat = p.category.strip() if p.category else None
        if not cat:
            result["no category"] += signed_amount
            continue
        path = leaf_to_path.get(cat)
        if not path:
            # Try partial match (for parent categories)
            for k, v in leaf_to_path.items():
                if cat == k or cat in v:
                    path = v
                    break
        if not path:
            result["invalid category"] += signed_amount
            invalid_categories_set.add(cat)
            continue
        for cat_in_path in path:
            result[cat_in_path] += signed_amount
    # Round all sums to zero decimal places
    for key in result:
        result[key] = round(result[key])

    output = {k: -v for k, v in result.items() if v != 0.0}
    metadata = {
        "total sum": total_sum,
        "invalid categories": sorted(list(invalid_categories_set)),
    }

    return output, metadata


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
        if name == "Total Sum":
            value = metadata["total sum"]
        elif name in result:
            value = result[name]
        nodes.append({"name": name, "value": value})
        node_map[name] = idx
        idx += 1
        return node_map[name]

    add_node("Total Sum")

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
                    "source": node_map["Total Sum"],
                    "target": node_map[top_cat],
                    "value": value,
                }
            )
        elif value < 0:
            links.append(
                {
                    "source": node_map[top_cat],
                    "target": node_map["Total Sum"],
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
                    "source": node_map["Total Sum"],
                    "target": node_map[special],
                    "value": val,
                }
            )
        elif val < 0:
            add_node(special)
            links.append(
                {
                    "source": node_map[special],
                    "target": node_map["Total Sum"],
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
