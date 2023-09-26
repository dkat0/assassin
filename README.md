# assassin

Bot for Senior Assassin, a live-action game played by high school seniors where teams of 2 are assigned a target and work towards eliminating them by shooting them with a water gun when they least expect it. The name of the game is that you can view anyone's location via a Life360 circle that all players are in. This tool pools the Life360 API every so often to detect if there are potential assassins (players within a specified radius of the bot users, who may be planning to attack). If so, users will be notified immediately via text through the Twilio API so they can hide and take cover.

Instructions to use:

1. First install dependencies using "pip install -r requirements.txt".
2. Enter your Life360 email and password into the "username" and "password" section, respectively, in config.json.
3. Enter your Life360 auth token into the "bearer_token" section of config.json. This can be retrieved by viewing the Authorization header after logging into https://www.life360.com/.
4. Enter the circle name for your Assassin Life360 group in the "circle_name" field in config.json.
5. In the "bot_users" field of config.json, specify the two players that are on your team.
6. Enter your and your teammate's phone numbers into the "alert_recipients" list in config.json.
7. Create an account on Twilio via https://www.twilio.com/en-us.
8. Enter your Twilio SID into "twilio_sid", Twilio Authorization Token in "twilio_auth_token", and your Twilio Number in "from_number" (all in config.json)
9. Run assassin.py.
