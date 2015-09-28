#!/usr/bin/python
import json
import requests
import random
import string
from time import sleep

SERVER_NAME = "http://ncl-test-vm-01.host.prod.eng.bos.redhat.com:8180"
USERNAME = 'pnc-admin'
PASSWORD = 'testme'
REALM = 'pncredhat'
CLIENT_ID = 'pncdirect'
KEYCLOAK_URL = 'https://keycloak3-pncauth.rhcloud.com'
TOKEN = ""
JSON_HEADER = ""
HEADER = ""
buildConfigIds = []
recordIds = []
buildTimes = []

# Note: when using it for actual requests, add to header: 'Authorization: Bearer <token>'
def getToken(username, password, realm, client_id, keycloak_url):

    params = {'grant_type': 'password',
              'client_id': client_id,
              'username': username,
              'password': password}

    r = requests.post(keycloak_url + "/auth/realms/" + realm + "/tokens/grants/access",params)

    if r.status_code == 200:
        reply = json.loads(r.content)
        return reply['access_token']
    else:
        print("Could not get the token id");
        return None

def getHeaders():

    return {'content-type': 'application/json', "Authorization": "Bearer " + TOKEN}

def getId(data):
    contentKey = unicode("content", "utf-8")
    idKey = unicode("id", "utf-8")
    return data[contentKey][idKey]

def fireBuilds(idList):
    for i in idList:
        print("Firing build " + str(i))
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/" + str(i) + "/build", headers=HEADER)
        print(r.text)
        print(r.status_code)
        jsonContent = json.loads(r.content)
        recordId = getId(jsonContent)
        recordIds.append(recordId)

def waitTillBuildsAreDone():
    print("Builds are running...")
    while True:
        if not buildsAreRunning():
            break
        sleep(1)
    print("Builds are done!")

def buildsAreRunning():
    for i in recordIds:
        r = requests.get(SERVER_NAME + "/pnc-rest/rest/running-build-records/" + str(i), headers=HEADER)
        if r.status_code == 200:
            return True
    return False

def getAllBuildTimes():
    for i in recordIds:
        buildTimes.append(getTime(i))

def getTime(buildId):
    r = requests.get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(buildId), headers=HEADER)
    content = json.loads(r.content)

    contentKey = unicode("content", "utf-8")
    startTimeKey = unicode("startTime", "utf-8")
    endTimeKey = unicode("endTime", "utf-8")

    time = int(content[contentKey][startTimeKey]) - int(content[contentKey][startTimeKey])
    return time

def randomName(size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for i in range(size))

TOKEN = getToken(USERNAME, PASSWORD, REALM, CLIENT_ID, KEYCLOAK_URL)
HEADER = getHeaders()

with open('sampleBuildConfigs/dependantProjects.json') as f:
    for line in f:
        line = json.loads(line)
        line["name"] = randomName()
        line = json.dumps(line)
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/", data=line, headers=HEADER)
        data = json.loads(r.content)
        buildId = getId(data)
        buildConfigIds.append(buildId)
        print("Added build configuration " + str(buildId))

fireBuilds(buildConfigIds)
waitTillBuildsAreDone()
getAllBuildTimes()
print(buildTimes)
