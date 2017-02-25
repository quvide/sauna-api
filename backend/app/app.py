from flask import Flask, jsonify, request
from redis import StrictRedis as Redis

import threading
import time
import math

TEMP_KEY = "temperature"

app = Flask(__name__)
redis = Redis("db", decode_responses=True)

def format_point(data):
    data = data.split(":")
    return {"time": data[0], "temperature": data[1]}

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
    threading.Timer(10.0, add_datapoint).start()
    now = int(time.time())
    data = abs(50*math.sin(now/100))+20
    redis.zadd(TEMP_KEY, now, "{time}:{data}".format(time=now, data=data))
    print("added datapoint on {}: {}".format(now, data))

    n = redis.zremrangebyscore(TEMP_KEY, 0, time.time() - 3600)
    print("cleaned up {} datapoints".format(n))

add_datapoint()
