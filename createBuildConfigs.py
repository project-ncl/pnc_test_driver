#!/usr/bin/python

import json
import math
import requests
import random
import string
import ConfigParser
import sys
import traceback
from time import sleep

requests.packages.urllib3.disable_warnings()

CONFIG_FILE = "config.ini"
buildConfigIds = []
recordIds = []
buildTimes = []
statuses = []
RETRIES = 6

def get(rest_point, params = {}, headers = {}):
    return request_with_retry(requests.get, rest_point, params, headers)

def post(rest_point, params = {}, headers = {}):
    return request_with_retry(requests.post, rest_point, params, headers)

def request_with_retry(request_type, rest_point, params, headers):
    for i in range(RETRIES):
        try:
            response = request_type(rest_point, data=params, headers=headers, verify=False)
            json_content = json.loads(response.content)
            return response
        except Exception:
            traceback.print_exc(file=sys.stdout)
        print "Retrying in 10 seconds..."
        sleep(10)

    print "Retries exceeded could not get valid response."
    sys.exit(1)


def load(value):
    parser = ConfigParser.ConfigParser()
    parser.read(CONFIG_FILE)
    return parser.get("CREDENTIALS", value)

# Note: when using it for actual requests, add to header: 'Authorization: Bearer <token>'
def getToken(username, password, realm, client_id, keycloak_url):
    params = {'grant_type': 'password',
              'client_id': client_id,
              'username': username,
              'password': password}
    response =  post(keycloak_url + "/auth/realms/" + realm + "/tokens/grants/access", params)

    if response.status_code == 200:
        token = json.loads(response.content)['access_token']
        return token

    print "WARNING: Could not get keycloak token"
    return None

def getHeaders():

    token = getToken(USERNAME, PASSWORD, REALM, CLIENT_ID, KEYCLOAK_URL)
    return {'content-type': 'application/json', "Authorization": "Bearer " + token}

def getId(data):
    idKey = unicode("id", "utf-8")
    contentKey = unicode("content", "utf-8")

    return data[contentKey][idKey]

def fireBuilds(idList):
    for i in idList:
        print("Firing build " + str(i))
        r = post(SERVER_NAME + "/pnc-rest/rest/build-configurations/" + str(i) + "/build", headers = getHeaders())
        jsonContent = json.loads(r.content)
        recordId = getId(jsonContent)
        recordIds.append(recordId)
        sleep(2)

def waitTillBuildsAreDone():
    print("Builds are running...")
    while True:
        if not buildsAreRunning():
            break
        sleep(5)
    print("Builds are done!")

def buildsAreRunning():
    for i in recordIds:
            r = get(SERVER_NAME + "/pnc-rest/rest/running-build-records/" + str(i), headers=getHeaders())
            if r.status_code == 200:
                return True
    return False

def getAllBuildTimes():
    for i in recordIds:
        time = int(getTime(i)) / 1000
        buildTimes.append(time)

def getTime(buildId):
    r = get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(buildId), headers=getHeaders())
    content = json.loads(r.content)

    contentKey = unicode("content", "utf-8")
    startTimeKey = unicode("startTime", "utf-8")
    endTimeKey = unicode("endTime", "utf-8")

    return  int(content[contentKey][endTimeKey]) - int(content[contentKey][startTimeKey])

def getStatuses():
    for i in recordIds:
        statuses.append(getStatus(i))

def getStatus(recordId):
    r = get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(recordId), headers=getHeaders())
    content = json.loads(r.content)

    contentKey = unicode("content", "utf-8")
    statusKey = unicode("status", "utf-8")

    return content[contentKey][statusKey]

def randomName(size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for i in range(size))


def calculate_standard_deviation(list_of_items):
    n = len(list_of_items)
    mean = float(sum(list_of_items)) / n

    sum_val = 0
    for item in list_of_items:
        sum_val += math.pow(item - mean, 2)

    std_dev = math.sqrt(float(sum_val) / (n - 1))
    return std_dev

def calculate_standard_error(list_of_items):
    std_dev = calculate_standard_deviation(list_of_items)
    return std_dev / math.sqrt(len(list_of_items))

def printStats():
    print "#####STATS#####"
    print "Number of successes:", len(filter(lambda x: x == "SUCCESS", statuses))
    print "Number of failures:", len(filter(lambda x: x != "SUCCESS", statuses))
    print "The build times are:", buildTimes, "seconds"
    print "Total build times:", sum(buildTimes), "seconds"
    print "Max build time:", max(buildTimes), "seconds"
    print "Min build time:", min(buildTimes), "seconds"
    print "Average build time:", sum(buildTimes)/len(buildTimes), "seconds"
    print "Standard error: ", calculate_standard_error(buildTimes)


def printRecordIds():
    print('')
    for recordId, status in zip(recordIds, statuses):
        print(SERVER_NAME + "/pnc-web/#/record/" + str(recordId) + "/info :: " + status)

    print('')

def sendBuildConfigsToServer(numberOfConfigs, repeat):
    buildConfigList = getBuildConfigList()

    for _ in range(repeat + 1):
        for i in range(numberOfConfigs):
            config = buildConfigList[i%len(buildConfigList)]
            config["name"] = randomName()
            config = json.dumps(config)
            r = post(SERVER_NAME + "/pnc-rest/rest/build-configurations/", config, headers=getHeaders())
            data = json.loads(r.content)
            buildId = getId(data)
            buildConfigIds.append(buildId)
            print("Added build configuration " + str(buildId))

def getBuildConfigList():
    configList = []
    with open('sampleBuildConfigs/dependantProjects.json') as f:
        for line in f:
            config = json.loads(line)
            configList.append(config)
    return configList

if __name__ == "__main__":
    SERVER_NAME = load("SERVER_NAME")
    USERNAME = load("USERNAME")
    PASSWORD = load("PASSWORD")
    REALM = load("REALM")
    CLIENT_ID = load("CLIENT_ID")
    KEYCLOAK_URL = load("KEYCLOAK_URL")
    NUMBER_OF_BUILDS = int(load("NUMBER_OF_BUILDS"))

    # if REPEAT_BUILDS = 0, do no repeat same build configurations
    # if REPEAT_BUILDS > 0, repeat the same build configurations REPEAT_BUILDS
    # times
    REPEAT_BUILDS = int(load("REPEAT"))

    sendBuildConfigsToServer(NUMBER_OF_BUILDS, REPEAT_BUILDS)
    fireBuilds(buildConfigIds)
    waitTillBuildsAreDone()
    getAllBuildTimes()
    getStatuses()
    printRecordIds()
    printStats()
