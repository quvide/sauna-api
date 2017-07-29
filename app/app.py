import RPi.GPIO as gpio
import ruamel.yaml as yaml

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask.ext.restless import APIManager
from datetime import datetime


# Load configuration
with open('config.yaml', 'r') as f:
    C = yaml.safe_load(f)

    if not C:
        exit('Missing configuration file or it is invalid!')


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db'
db = SQLAlchemy(app)


class Door(db.Model):
    time = db.Column(db.DateTime, primary_key=True)
    closed = db.Column(db.Boolean)

    def __init__(self, time, status):
        self.time = time
        self.status = status

    def __repr__(self):
        return '{} -- door {}'.format(self.time, 'open' if self.open else 'closed')


class Temperature(db.Model):
    time = db.Column(db.DateTime, primary_key=True)
    temp = db.Column(db.Float)

    def __init__(self, time, temp):
        self.time = time
        self.temp = temp

    def __repr__(self, time, temp):
        return '{} -- {}\N{DEGREE CELSIUS}'.format(time, temp)


manager = APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(Door, methods=['GET'])


def door_changed(channel):
    # remember: door closed = LOW  = False (closed circuit to ground),
    #                  open = HIGH = True  (circuit is open and pulled up to 3.3V internally)
    door = Door(datetime.now(), not gpio.input(C['pin']))
    db.session.save(door)
    db.session.commit()


gpio.setmode(gpio.BCM)
gpio.setup(C['pin'], gpio.IN, pull_up_down=gpio.PUD_UP)
gpio.add_event_detect(C['pin'], gpio.BOTH, callback=door_changed)

# Ensure we have some initial data
door_changed(C['pin'])
