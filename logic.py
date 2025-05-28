import json

def extract_route(data, return_all=False, route_index=None, route_name=None):
    routes = data.get("routes", [])
    if not routes:
        return None

    # Determine route by length if requested
    if isinstance(route_index, str):
        if route_index == "shortest":
            route_index = min(range(len(routes)), key=lambda i: routes[i].get("distance", float("inf")))
        elif route_index == "longest":
            route_index = max(range(len(routes)), key=lambda i: routes[i].get("distance", 0))
        else:
            raise ValueError(f"Unknown route_index mode: {route_index}")

    selected_routes = [routes[route_index]] if route_index is not None else routes
    features = []

    for i, route in enumerate(selected_routes):
        coords = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                geom = step.get("geometry", {})
                if geom.get("type") == "LineString":
                    coords.extend(geom.get("coordinates", []))

        name = route_name or (f"route_{i+1}" if len(selected_routes) > 1 else "route")
        feature = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"name": name}
        }
        features.append(feature)

    # If requested, return all routes as separate FeatureCollections
    if return_all:
        return [
            {
                "type": "FeatureCollection",
                "features": [feature]
            }
            for feature in features
        ]
    # Otherwise, return only the first route
    if features:
        return {
            "type": "FeatureCollection",
            "features": [features[0]]
        }
    # No routes found
    return {
        "type": "FeatureCollection",
        "features": []
    }