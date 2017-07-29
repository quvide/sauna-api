# sauna-api

## Getting started
Docker is quite unpleasant to use on Raspbian so everything is ran manually.

```
cp nginx.conf /etc/nginx/
systemctl enable nginx
systemctl start nginx
mkdir /srv/nginx
systemctl reload nginx

apt install certbot
certbot certonly --webroot -d sauna-api.paivola.fi -w /srv/nginx

python3 -m venv venv
source venv/bin/activate

pip install -r app/requirements.txt

cp sauna-api.service /etc/systemd/system/
systemctl enable sauna-api
systemctl start sauna-api
```

## GPIO stuff

The wires are currently connected to BCM pin 17 (phys 11) and GND (phys 9). There's a 10K ohm resistor in the circuit to prevent accidentally frying the Pi. The wires are currently held in place by electrical tape so accidentally setting the pin as an output might not be the biggest concern...

The magnetic sensor works by closing the circuit when it's in a magnetic field. We use the Pi's internal pull up resistor to define the HIGH state. This is when the circuit is open. When the circuit closes, GND gets connected to the input pin and the state goes from HIGH to LOW.

The ARM chip interrupts when the GPIO changes so we get almost realtime data with no CPU blocking. The RPi.GPIO module uses epoll to read data and calls our callback function when we have some fresh data to read.
