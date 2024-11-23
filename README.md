# EQTravelBot
A Discord bot writtin in Python to help players of the game EverQuest find the shortest distance between two zones.

This bot requires a JSON file named zones.json
it must be formatted as such:
```
{
  "zones": {
    "<zone_name>": {
      "connections": [
        {
          "name": "<connected_zone>",
          "direction": "both",
          "method": "<optional: Magus>",
          "item": "<optional: item_name>",
          "description": "<optional: item_description>",
          "stone": <optional: stone_name>",
          "door": "<optional: door_number>"
        }
      ]
    }
  }
}
```
direction can be Both, Exit, or Entrance - With Exit meaning that connection exits to the destination only and Entrance meaning it comes from the destination only.

method is only to identify when it's via magus (and possibly other futre methods discovered or identified by the bot)

item is for guild hall use to identify items you can right click on to zone.

description is for the description of the item to help find it.

stone is for guild hall portal stones you can guy and give to the gnome.

door is for the door # in Laurion Inn.
