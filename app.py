from flask import Flask, render_template, request
from flask_cors import CORS
import json
from collections import deque
from rapidfuzz import process, fuzz

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load zones data
def load_zones(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data.get("zones", {})

# Preprocess zones to ensure all referenced zones are present
def preprocess_zones(zones):
    referenced_zones = set()
    for zone_data in zones.values():
        for connection in zone_data.get("connections", []):
            referenced_zones.add(connection["name"])
    for zone in referenced_zones:
        if zone not in zones:
            zones[zone] = {"connections": []}

# Ensure every connection carries the "buy_handin" and "gh_item" flags.
# Missing flags are inferred from the legacy "stone"/"item" keys.
def normalize_connection_flags(zones):
    for zone_data in zones.values():
        for connection in zone_data.get("connections", []):
            connection.setdefault("buy_handin", bool(connection.get("stone")))
            connection.setdefault("gh_item", bool(connection.get("item")))

def connection_allowed(connection, use_buy_handin, use_gh_items):
    if connection.get("buy_handin") and not use_buy_handin:
        return False
    if connection.get("gh_item") and not use_gh_items:
        return False
    return True

# Preprocess aliases for fuzzy matching
def preprocess_zone_aliases(zones):
    aliases = {}
    for zone in zones.keys():
        base_name = zone.split(",")[0].strip()
        aliases[base_name.lower()] = zone
    return aliases

# Match a zone name using fuzzy logic
def match_zone_name(zone_name, zones, zone_aliases):
    if not zone_name.strip():
        raise ValueError("Zone name cannot be empty. Please provide a valid zone name.")

    zone_list = list(zone_aliases.keys())
    fuzzy_matches = process.extract(zone_name.lower(), zone_list, scorer=fuzz.ratio, limit=1)
    if fuzzy_matches and fuzzy_matches[0][1] >= 70:
        return zone_aliases[fuzzy_matches[0][0]]
    else:
        raise ValueError(f"No sufficiently close matches found for '{zone_name}'.")

# Find the shortest route and count the routes checked
def find_shortest_route_and_count(start, end, zones, use_buy_handin=True, use_gh_items=True):
    queue = deque([(start, [start])])
    visited = set()
    total_routes_checked = 0

    while queue:
        current_zone, path = queue.popleft()
        total_routes_checked += 1
        if current_zone in visited:
            continue
        visited.add(current_zone)

        if current_zone == end:
            return [{"name": zone, "method": None, "description": None, "door": None} for zone in path], total_routes_checked

        connections = zones.get(current_zone, {}).get("connections", [])
        for connection in connections:
            if not connection_allowed(connection, use_buy_handin, use_gh_items):
                continue
            if current_zone == "Guild Lobby" and connection["name"] in ["Guild Hall", "Plane of Knowledge"]:
                queue.appendleft((connection["name"], path + [connection["name"]]))
            elif connection["direction"] in ["both", "exit"] and connection["name"] not in visited:
                queue.append((connection["name"], path + [connection["name"]]))

    return None, total_routes_checked

# Assign details to route steps
def assign_details(route, zones):
    for i in range(len(route) - 1):
        current_zone = route[i]["name"]
        next_zone = route[i + 1]["name"]
        connections = zones.get(current_zone, {}).get("connections", [])

        for connection in connections:
            if connection["name"] == next_zone:
                if current_zone == "Guild Hall" and connection.get("item"):
                    route[i + 1]["method"] = f"Guild Hall Item ({connection['item']})"
                    route[i + 1]["description"] = connection.get("description", "Description not found")
                elif current_zone == "Guild Hall" and connection.get("stone"):
                    route[i + 1]["method"] = f"Guild Hall Stone ({connection['stone']})"
                    route[i + 1]["description"] = connection.get("description", "Description not found")
                if connection.get("method") == "Magus":
                    route[i + 1]["method"] = "Magus"
                    route[i + 1]["description"] = "Travel via Magus."
    return route

# Format route as cascading bullet points with a summary
def format_route(route, from_zone, to_zone, total_routes_checked):
    summary = (
        f"I checked {total_routes_checked} different routes. \nThe shortest path from {from_zone} to {to_zone} has been calculated to be:\n\n\n"
    )
    formatted_route = []
    indent = "  "
    for i, step in enumerate(route):
        if i == 0:
            continue
        connection_text = f"{indent * (i - 1)}• Travel to {step['name']}"
        if step.get("method"):
            if "Guild Hall Item" in step["method"]:
                item_name = step['method'].split('(')[1].split(')')[0]
                description = step.get("description", "Description not found")
                connection_text += f" using '{item_name}' ({description})."
            elif "Guild Hall Stone" in step["method"]:
                stone_name = step['method'].split('(')[1].split(')')[0]
                connection_text += f" using '{stone_name}'. Give the stone to Zeflmin Werlikanin."
        formatted_route.append(connection_text)
    formatted_route.append(f"{indent * len(route)}• Arrived at {route[-1]['name']}!")
    return summary + "\n".join(formatted_route)

# Load and preprocess zones
zones = load_zones("zones.json")
preprocess_zones(zones)
normalize_connection_flags(zones)
zone_aliases = preprocess_zone_aliases(zones)
all_zones = list(zones.keys())

# Web interface for user input
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    use_buy_handin = True
    use_gh_items = True

    if request.method == "POST":
        use_buy_handin = request.form.get("use_buy_handin") == "on"
        use_gh_items = request.form.get("use_gh_items") == "on"
        to_zone = request.form.get("to_zone", "").strip()
        from_zone = request.form.get("from_zone", "Guild Hall").strip()

        if not from_zone:
            from_zone = "Guild Hall"

        try:
            if not to_zone:
                raise ValueError("The 'To Zone' field is required.")

            matched_from_zone = match_zone_name(from_zone, zones, zone_aliases)
            matched_to_zone = match_zone_name(to_zone, zones, zone_aliases)

            route, total_routes_checked = find_shortest_route_and_count(matched_from_zone,             matched_to_zone, zones, use_buy_handin, use_gh_items)
            if not route:
                error = f"No path found from {matched_from_zone} to {matched_to_zone}!"
            else:
                detailed_route = assign_details(route, zones)
                result = format_route(detailed_route, matched_from_zone, matched_to_zone, total_routes_checked)
        except ValueError as e:
            error = str(e)

    return render_template("index.html", result=result, error=error, all_zones=all_zones,
                           use_buy_handin=use_buy_handin, use_gh_items=use_gh_items)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
