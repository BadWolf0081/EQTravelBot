# EQTravelBot
A Discord bot writtin in Python to help players of the game EverQuest find the shortest distance between two zones.

Usage Options:
```
!zone ToZoneName (FromZoneName)
```
The From Zone Name is optional, it will assume Guild Hall if not provided.

You can provide the name in Quotes if you have the full exact spelling including multiple words, or you can try to truncate into single words to see if the bot will recognize, sometimes it does.

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

Here are some sample replies with a populated json file:

![image](https://github.com/user-attachments/assets/fd524ba5-0004-45ca-80b4-681307bd48f0)
![image](https://github.com/user-attachments/assets/b95b8c27-f568-499f-9305-109b2a905419)
![image](https://github.com/user-attachments/assets/7841ee1d-571f-4974-8f79-9d67c4f98a9a)


