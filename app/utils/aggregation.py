from typing import List

from app.domain.models import Payment


def sum_payments_by_category(payments: List[Payment], category_tree: dict, start_date=None, end_date=None):
    """
    Aggregate payment amounts by all categories and parent categories.
    Returns: dict {category_name: sum, "metadata": {...}}
    Adds 'no category' and 'invalid category' keys for uncategorized and unknown payments.
    Metadata includes total sum and invalid categories list.
    """

    def collect_paths(tree, path=None, paths=None):
        if paths is None:
            paths = []
        if path is None:
            path = []
        for k, v in tree.items():
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
    for p in payments:
        # Make p.date naive
        p_date = p.date
        if p_date.tzinfo is not None:
            p_date = p_date.replace(tzinfo=None)

        # Make start_date naive
        sd = start_date
        if sd and sd.tzinfo is not None:
            sd = sd.replace(tzinfo=None)

        # Make end_date naive
        ed = end_date
        if ed and ed.tzinfo is not None:
            ed = ed.replace(tzinfo=None)

        # Filtering
        if sd and p_date < sd:
            continue
        if ed and p_date > ed:
            continue

        filtered_payments.append(p)

    # Aggregate amounts
    for p in filtered_payments:
        total_sum += p.amount
        cat = p.cust_category.strip() if p.cust_category else None
        if not cat:
            result["no category"] += p.amount
            continue
        path = leaf_to_path.get(cat)
        if not path:
            # Try partial match (for parent categories)
            for k, v in leaf_to_path.items():
                if cat == k or cat in v:
                    path = v
                    break
        if not path:
            result["invalid category"] += p.amount
            invalid_categories_set.add(cat)
            continue
        for cat_in_path in path:
            result[cat_in_path] += p.amount
    # Round all sums to zero decimal places
    for key in result:
        result[key] = round(result[key])

    result = {k: v for k, v in result.items() if (k in ["no category", "invalid category", "metadata"] or v >= 80)}

    result["metadata"] = {
        "total sum": total_sum,
        "invalid categories": sorted(list(invalid_categories_set))
    }

    return result


def build_sankey_data(result: dict, category_tree: dict):
    """
    Build Sankey diagram nodes and links from aggregation result and category tree.
    """
    nodes = []
    node_map = {}
    idx = 0

    def add_node(name):
        nonlocal idx
        if name in node_map:
            return node_map[name]
        value = 0
        if name == "Total Sum" and "metadata" in result and "total sum" in result["metadata"]:
            value = result["metadata"]["total sum"]
        elif name in result:
            value = result[name]
        nodes.append({"name": name, "value": value})
        node_map[name] = idx
        idx += 1
        return node_map[name]

    add_node("Total Sum")

    links = []
    def traverse(tree, parent):
        for k, v in tree.items():
            add_node(k)
            value = result.get(k, 0)
            if value > 0:
                links.append({
                    "source": node_map[parent],
                    "target": node_map[k],
                    "value": value
                })
            if isinstance(v, dict):
                traverse(v, k)

    for top_cat in category_tree:
        add_node(top_cat)
        value = result.get(top_cat, 0)
        if value > 0:
            links.append({
                "source": node_map["Total Sum"],
                "target": node_map[top_cat],
                "value": value
            })
        traverse(category_tree[top_cat], top_cat)

    for special in ["no category", "invalid category"]:
        if result.get(special, 0) > 0:
            add_node(special)
            links.append({
                "source": node_map["Total Sum"],
                "target": node_map[special],
                "value": result[special]
            })

    return {"nodes": nodes, "links": links}
