# получение TMI_TOKEN
# https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=CLIENT_ID&redirect_uri=https://teslabot.tesla1856.repl.co/&scope=chat:read+chat:edit+channel:moderate+whispers:read+whispers:edit+user:read:email+user:read:follows+user:edit:follows+channel:read:redemptions

import os
from twitchio.ext import commands
from twitchio.ext.commands.errors import CommandNotFound
import twitchio
#import traceback
#import sys
import re
import asyncio
import json
from datetime import datetime, timezone
import dateutil.parser
from dateutil.relativedelta import relativedelta
from replit import db
from replit import database
from random import randint
import requests

import alive

#import logging
#import sys
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

USERS = {}
channels = list(map(lambda x: x.strip(), os.environ['CHANNELS'].split(',')))
bot_nick = os.environ['BOT_NICK']

loop = asyncio.new_event_loop()
bot = commands.Bot(
    irc_token=os.environ['TMI_TOKEN'],
    #api_token=os.environ['TMI_TOKEN'].split(":")[1],
    client_id=os.environ['CLIENT_ID'],
    client_secret=os.environ['CLIENT_SECRET'],
    scopes=['channel:read:redemptions','user:read:email'],
    loop=loop,
    nick=bot_nick,
    prefix=os.environ['BOT_PREFIX'],
    #webhook_server=True,
    #external_host="https://TeslaBot.tesla1856.repl.co",
    #port=443,
    #callback=bot_nick,
    initial_channels=channels)


#@bot.event
#async def event_error(error, data):
#    traceback.print_exception(type(error),
#                              error,
#                              error.__traceback__,
#                              file=sys.stderr)

#@bot.event
#async def event_raw_data(data):
#    print(data)
async def cache_users(u):
    users = await bot.get_users(*u)
    for u in users:
        USERS[u.login.lower()] = u


async def user_id(user_login):
    if not user_login in USERS:
        await cache_users([user_login])
    return USERS[user_login].id


### funcfor partitioning by key. Only 5K records in db limit.
def db_add_item_part(prefix: str, key: str, value: str):
    i = prefix + ':' + key[0]
    old = db.get(i)
    if old:
        old = database.to_primitive(db[i])
        db[i] = {**old, key: value}
    else:
        db[i] = {key: value}


def db_get_item_part(prefix: str, key: str):
    i = prefix + ':' + key[0]
    d = db.get(i)
    if d:
        return database.to_primitive(d).get(key)
    else:
        return None


###


async def say_after(delay, what):
    await asyncio.sleep(delay)
    print(what)


def get_hours_period(dt):
    period = datetime.now(
        timezone.utc).replace(microsecond=0) - dateutil.parser.parse(dt)
    return ':'.join(str(period).split(':')[:-1])


async def make_eventsub_request(method, data=None, params=[("", "")]):
    try:
        r = await bot.http.request(method=method,
                                   url='/eventsub/subscriptions',
                                   params=params,
                                   json=data)
        #print("\n==")
        #print("token", bot.http.token)
    except twitchio.http.HTTPException as e:
        if e.args[2] != 409:  # уже есть подписка на событие
            print(e.args)
        return None

    #print(r)
    return r


async def remove_event_sub():
    subs = await make_eventsub_request('GET')
    for s in subs:
        if s.get("id", "-") != "-":
            print('delete', s["type"])
            await make_eventsub_request('DELETE', params=[("id", s["id"])])


async def event_sub():

    await remove_event_sub()

    callback = "https://TeslaBot.tesla1856.repl.co/eventsub"
    secret = os.environ['EVENTSUB_SECRET']

    for c in channels:
        id = await user_id(c)
        print(c, id)
        data = [
            {
                "type": "channel.channel_points_custom_reward_redemption.add",
                "version": "1",
                "condition": {
                    "broadcaster_user_id": str(id)
                },
                "transport": {
                    "method": "webhook",
                    "callback": callback,
                    "secret": secret
                }
            },
            {
                "type": "channel.follow",
                "version": "1",
                "condition": {
                    "broadcaster_user_id": str(id)
                },
                "transport": {
                    "method": "webhook",
                    "callback": callback,
                    "secret": secret,
                }
            },
        ]

        for d in data:
            print("add", d["type"], d["condition"]["broadcaster_user_id"])
            await make_eventsub_request('POST', data=d, params=[("", "")])


@bot.event
async def event_ready():
    'Called once when the bot goes online.'
    print(f"{bot_nick} is online!")
    print(channels)
    await cache_users(channels)
    await event_sub()

    #for c in channels:
    #    print(c, await user_id(c))
    #    await bot.modify_webhook_subscription(
    #        mode=twitchio.enums.WebhookMode.subscribe,
    #        topic=twitchio.webhook.UserFollows(to_id=await user_id(c)),
    #    )

    db["ya_ryadom:shhh"] = 1

    #for c in channels:
    #   chan=bot.get_channel(c)
    #   chan.send_me()
    #ws = bot._ws
    #await ws.send_privmsg(os.environ['CHANNEL'], f"/me has landed!")

    #for c in channels:
    #print(await bot.get_following('Tesla_Bot'))


# @bot.event
# async def event_join(user):
#     print('JOIN', user.channel.name, user.name)


@bot.event
async def event_message(ctx):
    'Runs every time a message is sent in chat.'

    # make sure the bot ignores itself and the streamer
    if ctx.author.name.lower() == os.environ['BOT_NICK'].lower():
        return

    channel = ctx.channel.name.lower()
    author = ctx.author.name.lower()
    content_lower = ctx.content.lower()

    m = re.search(r'боты.*\s(.+)\sв чат', content_lower)
    if m:
        c = m.group(1)
        await asyncio.sleep(randint(0, 3))
        await ctx.channel.send(c)
        return

    if (channel == "grillushka" and author == "grillushkarobot"
            and re.search(r'Guesses are open', ctx.content)):
        print("Start round")
        alive.set_timer(channel, datetime.now().timestamp(), 120)
        await say_after(90, "Осталось 30 секунд")
        await say_after(20, "Осталось 10 секунд")
        await say_after(10, "Время вышло!")
        return

    if (channel == "ya_ryadom" and db["ya_ryadom:shhh"] == 1 and
        (re.match(r'shhh', content_lower) or re.match(r'шшш', content_lower))):

        await asyncio.sleep(randint(0, 3))
        await ctx.channel.send("Shhh...")

        db["ya_ryadom:shhh"] = 0
        await asyncio.sleep(300)
        db["ya_ryadom:shhh"] = 1
        return

    # print(ctx.channel.name, author, ctx.content)
    await bot.handle_commands(ctx)


@bot.event
async def event_raw_usernotice(channel, tags: dict):
    print("usernotice>" + str(tags))
    """
    https://dev.twitch.tv/docs/irc/tags#usernotice-twitch-tags
    подписка с помощью Prime, data:
    {
    'badge-info': '',
    'badges': 'premium/1',
    'color': '#0036CC',
    'display-name': 'stephendguo',
    'emotes': '',
    'flags': '',
    'id': '6ae9b5c0-2d1a-452f-b79a-815a797650f3',
    'login': 'stephendguo',
    'mod': 0,
    'msg-id': 'sub',
    'msg-param-cumulative-months': 1,
    'msg-param-months': 0,
    'msg-param-multimonth-duration': 0,
    'msg-param-multimonth-tenure': 0,
    'msg-param-should-share-streak': 0,
    'msg-param-sub-plan-name': 'Channel\\sSubscription\\s(ya_ryadom)',
    'msg-param-sub-plan': 'Prime',
    'msg-param-was-gifted': 'false',
    'room-id': 30650213,
    'subscriber': 1,
    'system-msg': 'stephendguo\\ssubscribed\\swith\\sPrime.',
    'tmi-sent-ts': 1626032253544,
    'user-id': 107321220,
    'user-type': ''
    }
    """


#@bot.event
#async def event_webhook(self, data):
#    print("webhook>" + str(data))


@bot.event
async def event_raw_pubsub(data):
    print("pubsub>" + str(data))


@bot.event
async def event_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error


@bot.command(name='age', aliases=['follow', 'стаж', 'срок'])
async def cmd_age(ctx):
    t_id = await user_id(ctx.channel.name)
    f_id = await user_id(ctx.author.name)

    if t_id == f_id:
        await ctx.send(f'@{ctx.author.name}, Kappa')
        return

    info = await bot.get_follow(f_id, t_id)
    if info:
        rdelta = relativedelta(datetime.now(timezone.utc),
                               dateutil.parser.parse(info["followed_at"]))

        await ctx.send(
            f'@{ctx.author.name}, ты преследуешь стримера уже - ' +
            (f' лет: {rdelta.years}, ' if rdelta.years > 0 else '') +
            (f' месяцев: {rdelta.months}, ' if rdelta.months > 0 else '') +
            f' дней: {rdelta.days}')
    else:
        await ctx.send(
            f'@{ctx.author.name}, PogChamp а ну-ка быстро подписался на этот канал! :)'
        )


@bot.command(name='roll', aliases=['шанс'])
async def cmd_roll(ctx):
    await ctx.send(f'@{ctx.author.name}, {randint(0, 100)}')


@bot.command(name='ping')
async def cmd_ping(ctx):
    await ctx.send('pong')


@bot.command(name='info', aliases=['uptime'])
async def cmd_info(ctx):
    info = await bot.get_stream(ctx.channel.name)
    if info:
        period = get_hours_period(info['started_at'])
        await ctx.send(
            f"@{ctx.author.name} стрим идет: {period}, зрителей: {info['viewer_count']}"
        )
    else:
        await ctx.send(f"@{ctx.author.name} stream offline")


@bot.command(name='tg', aliases=["телега"])
async def cmd_tg(ctx):
    tg = json.loads(os.environ['MAP_TG'])
    channel = ctx.channel.name.lower()

    if channel in tg:
        await ctx.send(f"@{ctx.author.name}, {tg[channel]}")


@bot.command(name='discord', aliases=["ds", "дискорд"])
async def cmd_discord(ctx):
    disc = json.loads(os.environ['MAP_DISCORD'])
    channel = ctx.channel.name.lower()

    if channel in disc:
        await ctx.send(f"@{ctx.author.name}, {disc[channel]}")


@bot.command(name='goose', aliases=["гусь"])
async def cmd_goose(ctx):
    await ctx.send(
        "ЗАПУСКАЕМ ░ГУСЯ░▄▀▀▀▄░РАБОТЯГИ░░ ▄███▀░◐░░░▌░░░░░░░ ░░░░▌░░░░░▐░░░░░░░ ░░░░▐░░░░░▐░░░░░░░ ░░░░▌░░░░░▐▄▄░░░░░ ░░░░▌░░░░▄▀▒▒▀▀▀▀▄ ░░░▐░░░░▐▒▒▒▒▒▒▒▒▀▀▄ ░░░▐░░░░▐▄▒▒▒▒▒▒▒▒▒▒▀▄ ░░░░▀▄░░░░▀▄▒▒▒▒▒▒▒▒▒▒▀▄ ░░░░░░▀▄▄▄▄▄█▄▄▄▄▄▄▄▄▄▄▄▀▄ ░░░░░░░░░░░▌▌▌▌░░░░░ ░░░░░░░░░░░▌▌░▌▌░░░░░ ░░░░░░░░░▄▄▌▌▄▌▌░░░░░"
    )


@bot.command(name='table', aliases=["таблица"])
async def cmd_ефиду(ctx):
    channel = ctx.channel.name.lower()
    if channel in ("ya_ryadom", "tesla_1856"):
        await ctx.send(
            f"@{ctx.author.name}, https://docs.google.com/spreadsheets/d/1Bw3o1dBzCGMRC-voWEX_EIEdvv_uyPOkFrjIr-qeAhs"
        )


@bot.command(name='weather', aliases=["погода"])
async def cmd_weather(ctx, *args):
    in_city = ' '.join(args)
    city = re.sub(r'[^A-Za-z \-,]', ' ', in_city)
    if in_city != city:
        await ctx.send(
            f"@{ctx.author.name}, пиши название города на английском.")
        return
    url = f"https://api.openweathermap.org/data/2.5/weather"
    querystring = {
        "q": city,
        "cnt": "1",
        "lang": "ru",
        "type": "accurate",
        "units": "metric",
        "appid": os.environ['OWM_API_KEY']
    }
    response = requests.request("GET", url, params=querystring)
    info = response.json()
    if not info or not "cod" in info or info["cod"] != 200:
        await ctx.send(
            f"@{ctx.author.name}, упс, что-то пошло не так, не находится город"
        )

    w = ''
    if "weather" in info:
        w = ', '.join([i["description"] for i in info["weather"]])

    await ctx.send(
        f'@{ctx.author.name}, {info["name"]}: {w}, {info["main"]["temp"]}°C (ощущается как {info["main"]["feels_like"]}°C), влажность {info["main"]["humidity"]}%, ветер {info["wind"]["speed"]} м/с'
    )


@bot.command(name='song', aliases=["песня"])
async def cmd_song(ctx):

    channel = ctx.channel.name.lower()
    vk_ids = json.loads(os.environ['MAP_VK'])
    if not channel in vk_ids:
        return

    url = "https://api.vk.com/method/users.get"
    querystring = {
        "user_ids": vk_ids[channel],
        "fields": "status",
        "access_token": os.environ['VK_ACCESS_TOKEN'],
        "v": "5.131",
    }
    response = requests.request("GET", url, params=querystring)
    info = response.json()
    if not "response" in info or len(info["response"]) == 0:
        return

    info = info["response"][0]
    if "status_audio" in info:
        status_audio = info["status_audio"]
        await ctx.send(
            f'@{ctx.author.name}, сейчас играет: {status_audio["artist"]} - {status_audio["title"]}'
        )


def on_notification(data):
    if data["subscription"]["type"] == 'channel.follow' and data[
            "subscription"]["status"] == 'enabled':
        channel = data["event"]["broadcaster_user_login"]
        channel_id = data["event"]["broadcaster_user_id"]
        channel_name = data["event"]["broadcaster_user_name"]

        if channel in ["tesla_1856", "ya_ryadom"]:
            user = data["event"]["user_name"]
            ts = data["event"]["followed_at"]
            index = f"{channel.lower()}:follows:{user.lower()}"

            msg = ""
            if not index in db:
                asyncio.run_coroutine_threadsafe(asyncio.sleep(3),
                                                 loop).result()
                followers = asyncio.run_coroutine_threadsafe(
                    bot.get_followers(user_id=channel_id, count=True),
                    loop).result()
                db[index] = ts
                msg = f"/me @{channel_name}, новый преследователь на канале ({followers})! @{user}, welcome! KonCha <3 <3 <3"
            else:
                msg = f"/me {user} захотел преследовать стримера повторно. Welcome back! KonCha <3 <3 <3"

            if msg != "":
                ws = bot._ws
                asyncio.run_coroutine_threadsafe(
                    ws.send_privmsg(
                        channel,
                        msg,
                    ), loop).result()
            return
        else:
            return
    elif data["subscription"][
            "type"] == 'channel.channel_points_custom_reward_redemption.add' and data[
                "subscription"]["status"] == 'enabled':
        print('channel.channel_points_custom_reward_redemption.add',
              data["event"])

    print(data)


if __name__ == "__main__":
    print("start")
    alive.alive(bot, loop, on_notification)
    bot.run()
    print("stop")
