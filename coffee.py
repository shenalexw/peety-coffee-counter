import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter

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
    user_name = data.get('user_name')
    text = data.get('text')
    client.chat_postMessage(
        channel=channel_id, text=f"Hi {user_name}, Got your /tally for {text}")
    return Response(), 200

# Handles reset-tally


@app.route('/reset-tally', methods=['POST'])
def resetTally():
    data = request.form
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
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
    client.chat_postMessage(
        channel=channel_id, text=f"Hi {user_name}, Here is your scoreboard")
    return Response(), 200


if __name__ == "__main__":
    app.run(debug=True)
