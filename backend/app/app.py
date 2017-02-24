from flask import Flask, jsonify
from redis import StrictRedis as Redis

app = Flask(__name__)
redis = Redis("db", decode_responses=True)

@app.route("/")
def index():
    return jsonify(
        {
            temperature: 20.0,
            door_closed: true
        })
