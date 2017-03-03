from flask import Flask, jsonify, request, abort
from redis import StrictRedis as Redis

import threading
import time
import math
import requests
import ruamel.yaml as yaml
import RPi.GPIO as gpio

##################
# General config #
##################

TEMP_KEY = "temperature"
DOOR_KEY = "door_open"

with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

    if not CONFIG:
        exit("Missing configuration file or it is invalid!")


##################
# Redis and s12n #
##################

redis = Redis(CONFIG["redis_host"], decode_responses=True)

def encode_point(time, data):
    return "{}:{}".format(time, data)

def format_point(point, data_type):

    # This function should probably be renamed to decode_point  

    point = point.split(":")
    return {"time": float(point[0]), "data": data_type(point[1])}

def format_points(points, type):
    time_type = float
    if type == TEMP_KEY:
        data_type = float
    elif type == DOOR_KEY:
        data_type = lambda x: bool(int(x))

    res = []
    for point in points:
        res.append(format_point(point, data_type))

    return res


#############
# Flask API #
#############

app = Flask(__name__)

def point_wrapper(temp_points, door_points):
    return jsonify({
        TEMP_KEY: format_points(temp_points, TEMP_KEY),
        DOOR_KEY: format_points(door_points, DOOR_KEY)
    })

@app.route("/zrangebyscore")
def zrangebyscore():
    # https://redis.io/commands/zrangebyscore

    # Return scores based on their scores (timestamp)

    # The command supports non-inclusive ranges in addition
    # to the inf syntax, but I won't be adding support unless
    # someone explicitly requests it.

    _min = request.args.get("min")
    _max = request.args.get("max")

    if _min != "+inf" and _min != "-inf":
        _min = float(_min)
    
    if _max != "+inf" and _max != "-inf":
        _max = float(_max)

    temp_points = redis.zrangebyscore(TEMP_KEY, _min, _max)
    door_points = redis.zrangebyscore(DOOR_KEY, _min, _max)

    return point_wrapper(temp_points, door_points)

@app.route("/zrange")
def zrange():
    # https://redis.io/commands/zrange

    # Return points based on their position in the sorted set

    start = int(request.args.get("start"))
    stop = int(request.args.get("stop"))

    temp_points = redis.zrange(TEMP_KEY, start, stop)
    door_points = redis.zrange(DOOR_KEY, start, stop)

    return point_wrapper(temp_points, door_points)

@app.route("/zcard")
def zcard():
    return jsonify({TEMP_KEY: redis.zcard(TEMP_KEY), DOOR_KEY: redis.zcard(DOOR_KEY)})

@app.route("/zscan")
def zscan():
    temp_points = [point[0] for point in redis.zscan_iter(TEMP_KEY)]
    door_points = [point[0] for point in redis.zscan_iter(DOOR_KEY)]

    return point_wrapper(temp_points, door_points)

####################
# Recurring timers #
####################

def add_datapoint():
    threading.Timer(10, add_datapoint).start()
    now = time.time()

    data = requests.get("http://sauna.paivola.fi/api.cgi").text
    data = float(data.split("\n")[0])

    if redis.zcard(TEMP_KEY) != 0:
        newest = redis.zrange(TEMP_KEY, -1, -1)[0]
        if format_point(newest, float)["data"] == data:
            return

    redis.zadd(TEMP_KEY, now, encode_point(now, data))
    print("added datapoint on {}: {}".format(now, data))


def cleanup():
    threading.Timer(60, cleanup).start()
    n = redis.zremrangebyscore(TEMP_KEY, 0, time.time() - 3600*24*7)
    n += redis.zremrangebyscore(DOOR_KEY, 0, time.time() - 3600*24*7)
    print("cleaned up {} datapoints".format(n))

add_datapoint()
cleanup()


##############
# GPIO stuff #
##############

# The wires are currently connected to BCM pin 17 (phys 11)
# and GND (phys 9). There's a 10K ohm resistor in the circuit
# to prevent accidentally frying the Pi. The wires are currently
# held in place by electrical tape so accidentally setting the pin
# as an output might not be the biggest concern...

# The magnetic sensor works by closing the circuit when it's
# in a magnetic field. We use the Pi's internal pull up resistor
# to define the HIGH state. This is when the circuit is open.
# When the circuit closes, GND gets connected to the input pin
# and the state goes from HIGH to LOW.

# The ARM chip interrupts when the GPIO changes so we get almost
# realtime data with no CPU blocking. The RPi.GPIO module uses
# epoll to read data and calls our callback function when we
# have some fresh data to read.

def door_changed(channel):
    # remember: door closed = LOW  = False (closed circuit to ground),
    #                  open = HIGH = True  (circuit is open and pulled up to 3.3V internally)
    door_open = int(gpio.input(CONFIG["pin"]))
    now = time.time()

    redis.zadd(DOOR_KEY, now, encode_point(now, door_open))
    print("added door point on {}: {}".format(now, door_open))

gpio.setmode(gpio.BCM)
gpio.setup(CONFIG["pin"], gpio.IN, pull_up_down=gpio.PUD_UP)
gpio.add_event_detect(CONFIG["pin"], gpio.BOTH, callback=door_changed)

# Ensure we have some initial data
door_changed(CONFIG["pin"])
