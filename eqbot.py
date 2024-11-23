import discord
from discord.ext import commands
import json
import logging
from collections import deque
from rapidfuzz import process, fuzz

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load zones and connections from JSON file
def load_zones(file_path):
    """Load zone data from the specified JSON file."""
    with open(file_path, "r") as f:
        data = json.load(f)
    logger.debug(f"Loaded zones data: {list(data.keys())}")
    return data.get("zones", {})

# Preprocess zones to ensure all referenced zones are present
def preprocess_zones(zones):
    """Ensure all referenced zones are present in the data."""
    referenced_zones = set()
    for zone_data in zones.values():
        for connection in zone_data.get("connections", []):
            referenced_zones.add(connection["name"])
    for zone in referenced_zones:
        if zone not in zones:
            logger.debug(f"Adding placeholder for missing zone: {zone}")
            zones[zone] = {"connections": []}

# Preprocess aliases for better fuzzy matching
def preprocess_zones_with_aliases(zones):
    """Add aliases for zones with compound names to improve fuzzy matching."""
    aliases = {}
    for zone in zones.keys():
        base_name = zone.split(",")[0].strip()  # Use the first part of the name
        aliases[base_name.lower()] = zone
    return aliases

# Find the shortest route between two zones
def find_shortest_route(start, end, zones):
    """Find the shortest route between zones."""
    queue = deque([(start, [start])])  # (current_zone, path_so_far)
    visited = set()

    while queue:
        current_zone, path = queue.popleft()
        if current_zone in visited:
            continue
        visited.add(current_zone)

        if current_zone == end:
            return [{"name": zone, "method": None, "description": None, "door": None} for zone in path]

        connections = zones.get(current_zone, {}).get("connections", [])
        for connection in connections:
            if connection["direction"] in ["both", "exit"] and connection["name"] not in visited:
                queue.append((connection["name"], path + [connection["name"]]))

    return None

# Assign methods, descriptions, and door details to route steps
def assign_details(route, zones):
    """Assign methods, descriptions, and door details to route steps."""
    for i in range(len(route) - 1):
        current_zone = route[i]["name"]
        next_zone = route[i + 1]["name"]
        connections = zones.get(current_zone, {}).get("connections", [])

        for connection in connections:
            if connection["name"] == next_zone:
                # Check for Guild Hall items and stones
                if current_zone == "Guild Hall" and connection.get("item"):
                    route[i + 1]["method"] = f"Guild Hall Item ({connection['item']})"
                    route[i + 1]["description"] = connection.get("description", "Description not found")
                elif current_zone == "Guild Hall" and connection.get("stone"):
                    route[i + 1]["method"] = f"Guild Hall Stone ({connection['stone']})"
                    route[i + 1]["description"] = connection.get("description", "Description not found")

                # Check for Magus method
                if connection.get("method") == "Magus":
                    route[i + 1]["method"] = "Magus"
                    route[i + 1]["description"] = "Travel via Magus."

                # Check for Laurion Inn doors
                if current_zone == "Laurion Inn" and connection.get("door"):
                    route[i + 1]["method"] = f"Laurion Inn Door {connection['door']}"

    return route

# Format the route with cascading bullet points
def format_route(route):
    """Format the route with cascading bullet points."""
    formatted_route = []
    indent = "  "  # Base indent

    for i, step in enumerate(route):
        if i == 0:  # Skip the starting zone
            continue

        connection_text = f"{indent * (i - 1)}\u2022 Travel to {step['name']}"

        # Add Guild Hall item/stone or Laurion Inn door information
        if step.get("method"):
            if "Guild Hall Item" in step["method"]:
                item_name = step['method'].split('(')[1].split(')')[0]
                description = step.get("description", "Description not found")
                connection_text += f" using '{item_name}' ({description})."
            elif "Guild Hall Stone" in step["method"]:
                stone_name = step['method'].split('(')[1].split(')')[0]
                connection_text += f" using '{stone_name}'. Give the stone to Zeflmin Werlikanin."
            elif "Laurion Inn Door" in step["method"]:
                door_number = step['method'].split(' ')[-1]
                connection_text += f" via Door {door_number}."
            elif step.get("method") == "Magus":
                connection_text += " via Magus."

        formatted_route.append(connection_text)

    # Add final arrival message
    formatted_route.append(f"{indent * len(route)}\u2022 Arrived at {route[-1]['name']}!")
    return "\n".join(formatted_route)

# Match zone names using fuzzy matching
def match_zone_name(zone_name, zones, zone_aliases):
    """Match a zone name using fuzzy matching with aliases."""
    zone_list = list(zone_aliases.keys())
    logger.debug(f"Fuzzy matching for '{zone_name}' against: {zone_list}")
    matches = process.extract(zone_name.lower(), zone_list, scorer=fuzz.ratio, limit=5)
    logger.debug(f"Matches found: {matches}")

    if not matches:
        raise ValueError(f"No matches found for '{zone_name}'")

    best_match = matches[0][0]  # First element is the match
    score = matches[0][1]  # Second element is the score
    if score >= 50:  # Lower threshold for fuzzy match acceptance
        return zone_aliases[best_match]
    else:
        potential_matches = [zone_aliases[match[0]] for match in matches if match[1] >= 30]
        raise ValueError(f"No sufficiently close matches found for '{zone_name}'. Did you mean: {', '.join(potential_matches)}?")

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load zone data
zones = load_zones("zones.json")
zone_aliases = preprocess_zones_with_aliases(zones)
preprocess_zones(zones)

# Zone command
@bot.command(name="zone")
async def zone_command(ctx, zone1: str, zone2: str = "Guild Hall"):
    """Find the shortest route between two zones."""
    start_zone = zone2
    end_zone = zone1

    try:
        matched_zone1 = match_zone_name(zone1, zones, zone_aliases)
        matched_zone2 = match_zone_name(zone2, zones, zone_aliases)
    except ValueError as e:
        await ctx.send(str(e))
        return

    # Find shortest route
    route = find_shortest_route(matched_zone2, matched_zone1, zones)
    if not route:
        await ctx.send(f"No path found from {matched_zone2} to {matched_zone1}!")
        return

    # Assign details to the route
    detailed_route = assign_details(route, zones)

    # Format and send the route
    formatted_route = format_route(detailed_route)
    await ctx.send(formatted_route)

# Run the bot
bot.run("YOUR_DISCORD_BOT_TOKEN")
