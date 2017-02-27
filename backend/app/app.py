from flask import Flask, jsonify, request
from redis import StrictRedis as Redis

import threading
import time
import math
import requests

TEMP_KEY = "temperature"

app = Flask(__name__)
redis = Redis("db", decode_responses=True)

def format_point(data):
    data = data.split(":")
    return {"time": int(data[0]), "temperature": float(data[1])}

@app.route("/zrangebyscore")
def zrangebyscore():
    _min = float(request.args.get("min"))
    _max = float(request.args.get("max"))

    points = redis.zrangebyscore(TEMP_KEY, _min, _max)

    return jsonify(
        {
            "data": [format_point(point) for point in points]
        })

@app.route("/zrange")
def zrange():
    start = int(request.args.get("start"))
    stop = int(request.args.get("stop"))

    points = redis.zrange(TEMP_KEY, start, stop)

    return jsonify(
        {
            "data": [format_point(point) for point in points]
        })

def add_datapoint():
    threading.Timer(0.5, add_datapoint).start()
    now = int(time.time())

    data = requests.get("http://sauna.paivola.fi/api.cgi").text
    data = float(data.split("\n")[0])

    newest = redis.zrange(TEMP_KEY, -1, -1)[0]
    if newest:
        newest = format_point(newest)
        #print("comparing 2 floats... {} == {}".format(newest["temperature"], data))
        #print("difference is {}".format(newest["temperature"]-data))
        if newest["temperature"] == data:
            #print("abort the mission")
            return

    redis.zadd(TEMP_KEY, now, "{time}:{data}".format(time=now, data=data))
    print("added datapoint on {}: {}".format(now, data))


def cleanup():
    threading.Timer(60, cleanup).start()
    n = redis.zremrangebyscore(TEMP_KEY, 0, time.time() - 3600*24*7)
    print("cleaned up {} datapoints".format(n))

add_datapoint()
cleanup()
