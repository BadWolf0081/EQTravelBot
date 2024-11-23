import discord
from discord.ext import commands
import json
import logging
from collections import deque

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

        connection_text = f"{indent * (i - 1)}• Travel to {step['name']}"

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
    formatted_route.append(f"{indent * len(route)}• Arrived at {route[-1]['name']}!")
    return "\n".join(formatted_route)

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load zone data
zones = load_zones("zones.json")
preprocess_zones(zones)

# Zone command
@bot.command(name="zone")
async def zone_command(ctx, zone1: str, zone2: str = "Guild Hall"):
    """Find the shortest route between two zones."""
    start_zone = zone2
    end_zone = zone1

    # Match zone names
    def match_zone_name(zone_name, zones):
        """Match a zone name with partial or initial input."""
        zone_list = list(zones.keys())
        matches = [z for z in zone_list if z.lower().startswith(zone_name.lower())]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous matches for '{zone_name}': {matches}")
        else:
            raise ValueError(f"No matches found for {zone_name}")

    try:
        matched_zone1 = match_zone_name(zone1, zones)
        matched_zone2 = match_zone_name(zone2, zones)
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
