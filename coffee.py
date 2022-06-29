import slack
import os
import time
from datetime import datetime
from pytz import timezone
import pymongo
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
from apscheduler.schedulers.background import BackgroundScheduler

today = datetime.today().weekday()
todayHour = datetime.now().hour
channels = []

"""
@param [in] userId
@param [in] userName

returns userModel
"""


def createUser(userId, userName):
    return {
        "_id": userId,
        "name": userName,
        "drinks": [0, 0, 0, 0, 0]
    }

# If it friday at 4-5pm announce the winner and clear the database


def clean_database():
    # update time
    today = datetime.today().weekday()
    todayHour = datetime.now().hour

    if today == 4 and todayHour == 4:
        scoreboardData = []
        queryUsers = collection.find()
        for users in queryUsers:
            totalDrinks = 0
            for drinks in users["drinks"]:
                totalDrinks += drinks
            scoreboardData.append((users["name"], totalDrinks))

        scoreboardData.sort(key=lambda i: i[1], reverse=True)

        for channel in channels:
            client.chat_postMessage(
                channel=channel, text=f"☕ Congratulations to {scoreboardData[0][0]} drinking a total of {scoreboardData[0][1]} cups of coffee this week! ☕")

        collection.update_many({}, {"$set": {"drinks": [0, 0, 0, 0, 0]}})



scheduler = BackgroundScheduler()
scheduler.add_job(func=clean_database, trigger="interval", minutes=60)
scheduler.start()

# Load dotenv
env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

# init flask and slack event adapter
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)

# init client and bot_id

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")["user_id"]

# init mongo
mongoClient = pymongo.MongoClient(os.environ['MONGO_URL'])
db = mongoClient["coffee"]
collection = db["users"]


# Handles messages from anyone in the channel the bot is in
# @slack_event_adapter.on('message')
# def message(payload):
#     event = payload.get('event', {})
#     channel_id = event.get('channel')
#     user_id = event.get('user')
#     text = event.get('text')

#     if BOT_ID != user_id:
#         client.chat_postMessage(channel=channel_id, text=text)

@app.route("/")
def index():
    return "Welcome to Peety-Coffee-Counter Slackbot"

# Handles Tally


@app.route('/tally', methods=['POST'])
def tally():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    text = data.get('text')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"{user_name} has not joined the competition, use /join-comp to join")
        return Response(), 200

    if today > 4:
        client.chat_postMessage(
            channel=channel_id, text=f"Sorry {user_name}, No coffee on the weekend")
        return Response(), 200

    oldDrinks = queryUser["drinks"]
    if oldDrinks[today] > 9:
        client.chat_postMessage(
        channel=channel_id, text=f"{user_name} 🤔🤔🤔")
        return Response(), 200

    oldDrinks[today] += 1

    collection.update_one(
        {"_id": user_id}, {"$set": {"drinks": oldDrinks}})

    client.chat_postMessage(
        channel=channel_id, text=f"Hi {queryUser["name"]}, You have drinken {oldDrinks[today]} cups of coffee today!")

    return Response(), 200

# Handles reset-tally


@app.route('/reset-tally', methods=['POST'])
def resetTally():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    if today > 4:
        client.chat_postMessage(
            channel=channel_id, text=f"Sorry {user_name}, No coffee on the weekend")
    else:
        queryUser = collection.find_one({"_id": user_id})
        if queryUser is None:
            client.chat_postMessage(
                channel=channel_id, text=f"{user_name} has not joined the competition, use /join-comp to join")
            return Response(), 200

        oldDrinks = queryUser["drinks"]
        oldDrinks[today] = 0

        collection.update_one(
            {"_id": user_id}, {"$set": {"drinks": oldDrinks}})
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {user_name}, resetting your tally for today")
    return Response(), 200

# Handles Scoreboard


@app.route('/scoreboard', methods=['POST'])
def scoreboard():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    if today > 4:
        client.chat_postMessage(
            channel=channel_id, text=f"Sorry {user_name}, No coffee on the weekend")
    else:
        scoreboardData = []
        queryUsers = collection.find()
        for users in queryUsers:
            totalDrinks = 0
            for drinks in users["drinks"]:
                totalDrinks += drinks
            scoreboardData.append((users["name"], totalDrinks))

        scoreboardData.sort(key=lambda i: i[1], reverse=True)
        now_pst = datetime.now(timezone('US/Pacific'))
        client.chat_postMessage(
            channel=channel_id, text=f"Coffee Scoreboard {now_pst.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
        client.chat_postMessage(
            channel=channel_id, text="-----------------------------------------")
        for result in scoreboardData:
            client.chat_postMessage(
                channel=channel_id, text=f"{result[0]}: {result[1]} cups of coffee |")
        client.chat_postMessage(
            channel=channel_id, text="-----------------------------------------")

    return Response(), 200


@app.route('/join-comp', methods=['POST'])
def join():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {user_name}, you have already joined the fight!")
        return Response(), 200

    newUser = createUser(user_id, user_name)
    collection.insert_one(newUser)

    client.chat_postMessage(
        channel=channel_id, text=f"Hi {user_name}, Welcome to the battlefield!")
    return Response(), 200


@app.route('/change-name', methods=['POST'])
def changeName():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    text = data.get('text')

    queryUser = collection.find_one({"_id": user_id})
    if text is None:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {queryUser["name"]}, Please put new name after slash command")
        return Response(), 200

    newName = strip(text)
    if len(newName) > 12:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {queryUser["name"]}, Your new name is longer than 12 letters")
        return Response(), 200
    
    collection.update_one(
            {"_id": user_id}, {"$set": {"name": newName}})

    client.chat_postMessage(
            channel=channel_id, text=f"Hi {newName}, Nice Name!")
    return Response(), 200


@app.route('/leave-comp', methods=['POST'])
def leave():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {user_name}, you have already left the fight!")
        return Response(), 200

    collection.delete_one({"_id": user_id})

    client.chat_postMessage(
        channel=channel_id, text=f"Hi {user_name}, You have left the competition.")
    return Response(), 200


@app.route('/announce-winner-on', methods=['POST'])
def announce_on():
    data = request.form
    channel_id = data.get('channel_id')

    if channel_id in channels:
        client.chat_postMessage(
            channel=channel_id, text="channel has already turned on announement")
        return Response(), 200

    channels.append(channel_id)
    client.chat_postMessage(
        channel=channel_id, text="I will announce the winner on Friday from 4-5pm")
    return Response(), 200


@app.route('/announce-winner-off', methods=['POST'])
def announce_off():
    data = request.form
    channel_id = data.get('channel_id')

    if channel_id not in channels:
        client.chat_postMessage(
            channel=channel_id, text="channel has already turned off announement")
        return Response(), 200

    channels.remove(channel_id)
    client.chat_postMessage(
        channel=channel_id, text="I will not announce the winner")

    return Response(), 200


@app.route('/test', methods=['POST'])
def test():
    data = request.form
    channel_id = data.get('channel_id')
    client.chat_postMessage(
        channel=channel_id, text="Nice Try")
    print(data)
    return Response(), 200


if __name__ == "__main__":
    app.run(debug=True)
