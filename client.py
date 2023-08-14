import os
import requests

from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from dotenv import load_dotenv
load_dotenv()

host_name = os.getenv("HOSTNAME")
server_port = int(os.getenv("SERVER_PORT"))
stamp_uid = os.getenv("STAMP_UID")
server = os.getenv("SERVER_URL")
server_secret_token = os.getenv("SERVER_SECRET_TOKEN")
request_uri = os.getenv("REQUEST_URI")

pnconfig = PNConfiguration()
# FIXME generate a random id
userId = os.path.basename(__file__)
pnconfig.subscribe_key = os.getenv("SUBSCRIBE_KEY")
pnconfig.user_id = userId
pnconfig.ssl = True
pubnub = PubNub(pnconfig)

secret_token = ""

class MySubscribeCallback(SubscribeCallback):
    def presence(self, pubnub, presence):
        pass
    def status(self, pubnub, status):
        pass
    def message(self, pubnub, message):
        print ("from device " + message.publisher + ": " + message.message)
        global secret_token
        secret_token = message.message

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/test_stamp':
            self.test_stamp()
        else:
            self.send_error(404)

    def test_stamp(self):
        if self.headers.get('content-length') is not None:
            self.send_error(400)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response_json = {
            "request_uri" : request_uri,
            "uid" : stamp_uid,
            "secret_token" : secret_token
        }
        self.wfile.write(json.dumps(response_json).encode(encoding='utf_8'))

def incoming_request():
    # init web server
    web_server = HTTPServer((host_name, server_port), MyServer)
    print("Server started http://%s:%s" % (host_name, server_port))
    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass
    web_server.server_close()
    print("Server stopped.")

# get the last secret token for the stamp
request_input = {
    "uid": stamp_uid
}
headers = {"Authorization": "Bearer {}".format(server_secret_token)}
get_first_token_url = "{}/first_stamp".format(server)
response = requests.get(get_first_token_url, data=json.dumps(request_input), headers=headers)
response_json = response.json()
secret_token = response_json["secret_token"]
print("Secret token received for stamping: {}".format(secret_token))
# create a thread for incoming requests 
thread = Thread(target=incoming_request)
thread.start()

# add listener for later secret token
pubnub.add_listener(MySubscribeCallback())
channel_id = "chan-{}".format(stamp_uid)
print("Subscribe to {}".format(channel_id))
pubnub.subscribe().channels(channel_id).execute()