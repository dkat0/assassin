import requests
from math import sin, cos, sqrt, atan2, radians
import time
from twilio.rest import Client
import traceback
import json

with open('config.json') as f:
    config = json.load(f)

# =================
bot_version = "v2.4"
username = config["username"]
password = config["password"]
access_token = config["bearer_token"]
circle_name = config["circle_name"]
closest_allowed_distance = config["closest_allowed_distance"]  # miles
safe_zones = {}
refresh_rate = config["refresh_rate"]  # seconds
bot_users = config["bot_users"]
alert_recipients = config["alert_recipients"]
assassins = None
blacklisted_players = []
twilio_sid = config["twilio_sid"]
twilio_auth_token = config["twilio_auth_token"]
twilio_from = config["twilio_from_number"]
# =================

base_url = "https://www.life360.com/"
s = requests.Session()
twilio_client = Client(twilio_sid, twilio_auth_token)
sent_operational_msg = False

headers = {
    'Accept': 'application/json',
    'X-Application': 'life360-web-client',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
}


def login(username, password):
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password
    }

    token = \
        s.get("https://app.life360.com/config.js", headers=headers).text.split('AUTH_SECRET_TOKEN":"')[1].split('"')[0]
    headers["Authorization"] = "Basic " + token

    r = s.post("https://api.life360.com/v3/oauth2/token.json", data=payload, headers=headers).json()
    user = r["user"]
    headers["Authorization"] = "Bearer" + r["access_token"]
    return "Bearer" + r["access_token"]


def check_locations(circle_id):
    r = s.get(f"https://api.life360.com/v3/circles/{circle_id}/members", headers=headers).json()

    members = []
    for data in r['members']:
        member = {
            "name": (data["firstName"] + " " + data["lastName"]).strip(),
            "id": data["id"]
        }

        location = data["location"]
        if location is not None:
            if location["address1"] is not None:
                address = location["address1"] + ", " + location["address2"]
            else:
                address = None

            member.update({
                "location": [float(location["latitude"]), float(location["longitude"])],
                "address": address,
                "startTime": location["startTimestamp"],
                "lastUpdatedTime": location["timestamp"]
            })
            members.append(member)
        else:
            member.update({
                "location": None,
                "address": None,
                "startTime": None,
                "lastUpdatedTime": None
            })
            members.append(member)

    return members


def calc_distance(location1, location2):
    lat1, lon1 = location1
    lat2, lon2 = location2

    R = 6373.0

    lat1, lon1, lat2, lon2 = radians(lat1), radians(lon1), radians(lat2), radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c * 0.621371

    return distance  # miles


def in_safe_zone(my_location):
    lat, lon = my_location
    for zone_name, zone in safe_zones.items():
        lat_range = zone["lat"]
        lon_range = zone["lon"]
        if lat_range[0] <= lat <= lat_range[1] and lon_range[0] <= lon <= lon_range[1]:
            return zone_name
    return None


def main():
    global sent_operational_msg

    if access_token:
        headers["Authorization"] = access_token
    else:
        headers["Authorization"] = login(username, password)

    r = s.get("https://api.life360.com/v3/circles", headers=headers).json()
    circle = next(c for c in r["circles"] if c["name"] == circle_name)
    circle_member_count = circle["memberCount"]
    circle_id = circle["id"]

    if assassins is None:
        watching_str = "👀 Currently watching all players for suspicious activity."
    else:
        if len(assassins) <= 2:
            ee = " and ".join(list(assassins.values()))
        else:
            ee = ', '.join(list(assassins.values())[:-1]) + ", and " + list(assassins.values())[-1]
        watching_str = f"👀 Currently watching {ee} for suspicious activity."

    if not sent_operational_msg:
        for twilio_to in alert_recipients:
            message = twilio_client.messages.create(body="✅ Assassin Alert " + bot_version + " is operational.\nIf any assassins are detected, it's on sight.", from_=twilio_from, to=twilio_to)
            time.sleep(1)
            message = twilio_client.messages.create(body=watching_str, from_=twilio_from, to=twilio_to)
        sent_operational_msg = True

    time.sleep(1)

    player_distances = {}
    while 1:
        players = check_locations(circle_id)

        main_users = []
        for name in bot_users:
            main_users.append(next(p for p in players if p["name"] == name))

        for player in main_users.copy():
            players.remove(player)

            safe_zone = in_safe_zone(player["location"])
            if safe_zone is not None:
                print(f"{player['name']} in safe zone: {safe_zone}")
                main_users.remove(player)

        if not main_users:
            print(f"Main user(s) in zone. Waiting {refresh_rate}s.")
            time.sleep(refresh_rate)
            print()
            continue

        players = [player for player in players if player["id"] not in blacklisted_players]
        if assassins is not None:
            players = [player for player in players if player["id"] in list(assassins.keys())]

        if not player_distances:
            for user in main_users:
                if user['id'] not in player_distances:
                    player_distances[user['id']] = {}

                for player in players:
                    player_distances[user['id']][player["id"]] = 1000

        print(f"Scanning {len(players)} players for potential assassin...")

        for player in players:
            if player["location"] is None:
                continue

            if in_safe_zone(player["location"]) is not None:
                continue

            for user in main_users:
                dist = calc_distance(user["location"], player["location"])

                if dist <= 0.3:
                    msg = "‼️🚨Urgent Alert‼️🚨\n" + f"{player['name']} is {round(dist, 2)} miles away from {user['name']}."
                    print(msg)
                    #print("Address: " + str(player["address"]))

                    if player_distances[user['id']][player['id']] > 0.3:
                        for twilio_to in alert_recipients:
                            message = twilio_client.messages.create(body=msg, from_=twilio_from, to=twilio_to)
                elif dist <= closest_allowed_distance:
                    msg = "⚠️🚨Alert⚠️🚨\n" + f"{player['name']} is {round(dist, 2)} miles away from {user['name']}."
                    print(msg)
                    #print("Address: " + str(player["address"]))

                    if player_distances[user['id']][player['id']] > closest_allowed_distance:
                        for twilio_to in alert_recipients:
                            message = twilio_client.messages.create(body=msg, from_=twilio_from, to=twilio_to)
                else:
                    if player_distances[user['id']][player['id']] <= closest_allowed_distance:
                        for twilio_to in alert_recipients:
                            msg = f"😮‍💨 {player['name']} is no longer within a {closest_allowed_distance} mile radius of {user['name']}."
                            print(msg)
                            print("Address: " + str(player["address"]))
                            message = twilio_client.messages.create(body=msg, from_=twilio_from, to=twilio_to)

                player_distances[user['id']][player['id']] = dist

        print(f"Waiting {refresh_rate}s.")
        time.sleep(refresh_rate)
        print()


for i in range(8):
    try:
        main()
    except:
        traceback.print_exc()
        time.sleep(150)
else:
    for twilio_to in alert_recipients:
        message = twilio_client.messages.create(body="❌ Assassin Alert " + bot_version + " is NOT operational.", from_=twilio_from, to=twilio_to)