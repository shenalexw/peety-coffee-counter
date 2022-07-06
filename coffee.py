import slack
import os
import time
from datetime import datetime
from pytz import timezone
import pymongo
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response

"--------------- inits ----------------"
# Load dotenv
env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)

# init flask and slack event adapter
app = Flask(__name__)

# init client and bot_id
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")["user_id"]

# init mongo
mongoClient = pymongo.MongoClient(os.environ['MONGO_URL'])
db = mongoClient["coffee"]
collection = db["users"]

# init time
today = datetime.now(timezone('US/Pacific')).weekday()
todayHour = datetime.now(timezone('US/Pacific')).hour

# options
DRINKOPTIONS = {
    "coffee" : 1,
    "tea" : 0.5
}

"--------------- Functions ----------------"
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



def announceWinner(channel_id):
    scoreboardData = []
    queryUsers = collection.find()
    for users in queryUsers:
        totalDrinks = 0
        for drinks in users["drinks"]:
            totalDrinks += drinks
        scoreboardData.append((users["name"], totalDrinks))

    scoreboardData.sort(key=lambda i: i[1], reverse=True)

    if scoreboardData[0][1] == scoreboardData[1][1]:
        chugOff(channel_id, scoreboardData[0][0], scoreboardData[1][0])
    else:
        client.chat_postMessage(
            channel=channel_id, text=f"☕ Congratulations to {scoreboardData[0][0]} drinking a total of {scoreboardData[0][1]} cups of coffee this week! ☕")

    client.chat_postMessage(
        channel=channel_id, text=f"Final Scoreboard")
    client.chat_postMessage(
            channel=channel_id, text="-------------------------------")

    for result in scoreboardData:
        displayTotalCupsCoffee = result[1]
        if isinstance(displayTotalCupsCoffee, float):
            if displayTotalCupsCoffee.is_integer():
                displayTotalCupsCoffee = int(displayTotalCupsCoffee)
        client.chat_postMessage(
            channel=channel_id, text=f"{result[0]}: {displayTotalCupsCoffee} cups of coffee")

    client.chat_postMessage(
            channel=channel_id, text="-------------------------------")
    
    

def cleanDatabase():
    collection.update_many({}, {"$set": {"drinks": [0, 0, 0, 0, 0]}})

def chugOff(channel_id, firstPerson, secondPerson):
    client.chat_postMessage(
            channel=channel_id, text="Uh oh LOOKS LIKE WE GOT A CHUG OFF!!!")
    client.chat_postMessage(
            channel=channel_id, text=f"{firstPerson}, {secondPerson} Meet at the cold brew stand for the CHUG OFF!!!!")



"--------------- Routes ----------------"
@app.route("/")
def index():
    return "Welcome to Peety-Coffee-Counter Slackbot"


@app.route('/tally', methods=['POST'])
def tally():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    text = data.get('text')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"{user_name} has not joined the competition, use /join-comp to join")
        return Response(), 200
    
    displayName = queryUser["name"]

    if today >= 4 and todayHour >= 17:
        client.chat_postMessage(
            channel=channel_id, text=f"Sorry {displayName}, No coffee at this time")
        return Response(), 200

    oldDrinks = queryUser["drinks"]
    if oldDrinks[today] > 9:
        client.chat_postMessage(
        channel=channel_id, text=f"{displayName} Are you sure about that? 🤔🤔🤔")
        return Response(), 200

    userChoice = text.strip().lower()
    choiceKey = ""
    if userChoice == "" or userChoice == "coffee":
        choiceKey = "coffee"
    elif userChoice == "tea" or userChoice == "espresso":
        choiceKey = "tea"
    else:
        client.chat_postMessage(
        channel=channel_id, text=f"Hi {displayName}, {userChoice} is not a valid drink")
        return Response(), 200

    oldDrinks[today] += DRINKOPTIONS[choiceKey]

    collection.update_one(
        {"_id": user_id}, {"$set": {"drinks": oldDrinks}})

    displayTodayDrink = oldDrinks[today]
    if isinstance(displayTodayDrink, float):
        if displayTodayDrink.is_integer():
            displayTodayDrink = int(displayTodayDrink)
    
    client.chat_postMessage(
        channel=channel_id, text=f"Hi {displayName}, You have drinken {displayTodayDrink} cups of coffee today!")

    return Response(), 200


@app.route('/reset-tally', methods=['POST'])
def resetTally():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"{user_name} has not joined the competition, use /join-comp to join")
        return Response(), 200
    
    displayName = queryUser["name"]
    oldDrinks = queryUser["drinks"]
    oldDrinks[today] = 0

    collection.update_one(
        {"_id": user_id}, {"$set": {"drinks": oldDrinks}})
    client.chat_postMessage(
        channel=channel_id, text=f"Hi {displayName}, resetting your tally for today")
    return Response(), 200

@app.route('/scoreboard', methods=['POST'])
def scoreboard():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    text = data.get('text')
    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"{user_name} has not joined the competition, use /join-comp to join")
        return Response(), 200
    
    displayName = queryUser["name"]

    userText = text.strip()
    if userText == "":
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
            channel=channel_id, text="-------------------------------")

        for result in scoreboardData:
            displayTotalCupsCoffee = result[1]
            if isinstance(displayTotalCupsCoffee, float):
                if displayTotalCupsCoffee.is_integer():
                    displayTotalCupsCoffee = int(displayTotalCupsCoffee)
            client.chat_postMessage(
                channel=channel_id, text=f"{result[0]}: {displayTotalCupsCoffee} cups of coffee")

        client.chat_postMessage(
            channel=channel_id, text="-------------------------------")
        return Response(), 200
    
    queryOtherUser = collection.find_one({"name": userText})
    if queryOtherUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"Sorry {displayName}, {userText} is not on the leaderboard")
        return Response(), 200
    
    totalDrink = 0
    displayOtherName = queryOtherUser["name"]
    displayOtherDrinks = queryOtherUser["drinks"]
    index = 0

    for drink in displayOtherDrinks:
        totalDrink += drink
        if isinstance(drink, float):
            if drink.is_integer():
                displayOtherDrinks[index] = int(drink)
        index += 1

    if isinstance(totalDrink, float):
        if totalDrink.is_integer():
            totalDrink = int(totalDrink)

    client.chat_postMessage(
            channel=channel_id, text=f"Displaying Stats for {displayOtherName}")
    client.chat_postMessage(
            channel=channel_id, text=f"Total Cups of Coffee: {totalDrink}")
    client.chat_postMessage(
            channel=channel_id, text=f"Mon: {displayOtherDrinks[0]}, Tues: {displayOtherDrinks[1]}, Wed: {displayOtherDrinks[2]}, Thurs {displayOtherDrinks[3]}, Fri: {displayOtherDrinks[4]}")
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
    user_name = data.get('user_name')
    text = data.get('text')

    queryUser = collection.find_one({"_id": user_id})
    if queryUser is None:
        client.chat_postMessage(
            channel=channel_id, text=f"{user_name} has notjoined the competition, use /join-comp to join")
        return Response(), 200
    
    displayName = queryUser["name"]
    
    newName = text.strip().lower().capitalize()

    if newName == "":
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {displayName}, Please put new name after slash command")
        return Response(), 200

    if len(newName) > 12:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {displayName}, Your new name is longer than 12 letters")
        return Response(), 200

    queryName = collection.find_one({"name": newName})
    if queryName is not None:
        client.chat_postMessage(
            channel=channel_id, text=f"Hi {user_name}, an existing user is already using {newName}")
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

@app.route('/congrats', methods=['POST'])
def congrats():
    data = request.form
    channel_id = data.get('channel_id')
    text = data.get('text')
    if text == os.environ['PASSWORD']:
        client.chat_postMessage(
            channel=channel_id, text="Announcing the winner")
        announceWinner(channel_id)
        cleanDatabase()
    else:
        client.chat_postMessage(
            channel=channel_id, text="Access Denied")
    return Response(), 200

@app.route('/test', methods=['POST'])
def test():
    data = request.form
    channel_id = data.get('channel_id')
    client.chat_postMessage(
        channel=channel_id, text=f"Nice Try {todayHour}")
    print(data)
    return Response(), 200

if __name__ == "__main__":
    app.run(debug=True)
