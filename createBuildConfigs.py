#!/usr/bin/python

import json
import requests
import random
import string
import ConfigParser
from time import sleep

CONFIG_FILE = "config.ini"
buildConfigIds = []
recordIds = []
buildTimes = []

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

    r = requests.post(keycloak_url + "/auth/realms/" + realm + "/tokens/grants/access",
                      params, verify=False)

    if r.status_code == 200:
        reply = json.loads(r.content)
        return reply['access_token']
    else:
        print("Could not get the token id");
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
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/" + str(i) + "/build",
                          headers=getHeaders(), verify=False)
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
        r = requests.get(SERVER_NAME + "/pnc-rest/rest/running-build-records/" + str(i), headers=getHeaders())
        if r.status_code == 200:
            return True
    return False

def getAllBuildTimes():
    for i in recordIds:
        time = int(i) / 1000 / 60
        buildTimes.append(int(getTime(i)))

def getTime(buildId):
    r = requests.get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(buildId), headers=getHeaders())
    content = json.loads(r.content)

    contentKey = unicode("content", "utf-8")
    startTimeKey = unicode("startTime", "utf-8")
    endTimeKey = unicode("endTime", "utf-8")

    return  int(content[contentKey][endTimeKey]) - int(content[contentKey][startTimeKey])

def randomName(size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for i in range(size))

def printStats():
    print("The build times are:", buildTimes)
    print("Total build times:", sum(buildTimes))
    print("Max build time:", max(buildTimes))
    print("Min build time:", min(buildTimes))
    print("Average build time:", sum(buildTimes)/len(buildTimes))

def loadBuildConfigs():
    with open('sampleBuildConfigs/dependantProjects.json') as f:
        for line in f:
            line = json.loads(line)
            line["name"] = randomName()
            line = json.dumps(line)
            r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/",
                              data=line, headers=getHeaders(), verify=False)
            print(r.content)
            data = json.loads(r.content)
            buildId = getId(data)
            buildConfigIds.append(buildId)
            print("Added build configuration " + str(buildId))

if __name__ == "__main__":
    SERVER_NAME = load("SERVER_NAME")
    USERNAME = load("USERNAME")
    PASSWORD = load("PASSWORD")
    REALM = load("REALM")
    CLIENT_ID = load("CLIENT_ID")
    KEYCLOAK_URL = load("KEYCLOAK_URL")

    loadBuildConfigs()
    fireBuilds(buildConfigIds)
    waitTillBuildsAreDone()
    getAllBuildTimes()
    printStats()
