import json
import socket
import time
import sys

GRAPHITE_SERVER = '0.0.0.0'
GRAPHITE_PORT = 2003

def get_data(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
        return data

def report_to_graphite(data):
    num_builds = data['num_builds']
    repeat = data['repeat']
    server_name = data['server_name']

    # for graphite to work, it needs to send a key, value and timestamp
    key = "jenkins.pnc_test_driver." + "buildNum" + str(num_builds) + \
          "repeat" + str(repeat) + "."

    timestamp = int(time.time())
    send_to_graphite(key + "average", data['average'], timestamp)
    send_to_graphite(key + "standard_error", data['standard_error'], timestamp)
    send_to_graphite(key + "successes", data['successes'], timestamp)
    send_to_graphite(key + "failures", data['failures'], timestamp)

def send_to_graphite(key, value, timestamp):

    sock = socket.socket()
    sock.connect((GRAPHITE_SERVER, GRAPHITE_PORT))
    string_to_send = key + " " + str(value) + " " + str(timestamp)
    print "Sending this to graphite: " + string_to_send
    # I need to end the string with "\n", otherwise graphite ignores it
    sock.sendall(string_to_send + "\n")

    sock.close()

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print("Usage: <script> <Graphite server> <Graphite port>")
    GRAPHITE_SERVER = sys.argv[1]
    GRAPHITE_PORT = int(sys.argv[2])

    data = get_data("driver_results.json")
    report_to_graphite(data)
