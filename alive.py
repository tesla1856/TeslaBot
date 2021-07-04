#for ping from https://uptimerobot.com/
#https://www.youtube.com/watch?v=SPTfmiYiuok&t=365s

from flask import Flask
from flask import request
from threading import Thread

import asyncio

app = Flask(__name__)
timers = {}


def sync_exec(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@app.route('/')
def pong():
    return "pong"


@app.route('/timers')
def get_timers():
    return timers


@app.route('/eventsub', methods=['POST'])
def post_eventsub():
    data = request.get_json()
    headers = request.headers
    if headers.get("Twitch-Eventsub-Message-Type",
                   "") == "webhook_callback_verification":
        return data["challenge"], 200

    if headers.get("Twitch-Eventsub-Message-Type", "") == "notification":
        #print("notification")
        on_notification(data)
        return "", 200

    print("Twitch-Eventsub-Message-Type:" +
          headers.get("Twitch-Eventsub-Message-Type", ""))
    return "", 200


#@app.route('/chatters')
#def get_chatters():

#    # submit the coroutine to the event loop thread
#    send_fut = asyncio.run_coroutine_threadsafe(bot.get_chatters("ya_ryadom"),
#                                                loop)
#    # wait for the coroutine to finish
#    info=send_fut.result()
#    print(f"{info!r}")
#    return "ok"


def set_timer(name, start, period):
    timers[name] = (start, period)


def run():
    app.run(host='0.0.0.0', port=8080)


def alive(b, l, on_notif):
    global bot, loop, on_notification
    bot, loop, on_notification = b, l, on_notif
    t = Thread(target=run)
    t.start()
