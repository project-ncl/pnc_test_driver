#!/usr/bin/python
import json
import requests
import random
import string
from time import sleep

SERVER_NAME = "http://localhost:8080"
buildConfigIds = []
recordIds = []
buildTimes = []

def getId(data):
    contentKey = unicode("content", "utf-8")
    idKey = unicode("id", "utf-8")
    return data[contentKey][idKey]

def fireBuilds(idList):
    for i in idList:
        print("Firing build " + str(i))
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/" + str(i) + "/build")
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
        r = requests.get(SERVER_NAME + "/pnc-rest/rest/running-build-records/" + str(i))
        if r.status_code == 200:
            return True
    return False

def getAllBuildTimes():
    for i in recordIds:
        buildTimes.append(getTime(i))

def getTime(buildId):
    r = requests.get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(buildId))
    content = json.loads(r.content)

    contentKey = unicode("content", "utf-8")
    startTimeKey = unicode("startTime", "utf-8")
    endTimeKey = unicode("endTime", "utf-8")

    time = int(content[contentKey][startTimeKey]) - int(content[contentKey][startTimeKey])
    return time

def randomName(size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
   return ''.join(random.choice(chars) for i in range(size))

with open('sampleBuildConfigs/dependantProjects.json') as f:
    for line in f:
        line = json.loads(line)
        line["name"] = randomName()
        line = json.dumps(line)
        headers = {'content-type': 'application/json'}
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/", data=line, headers=headers)
        data = json.loads(r.content)
        buildId = getId(data)
        buildConfigIds.append(buildId)

fireBuilds(buildConfigIds)
waitTillBuildsAreDone()
getAllBuildTimes()
print(buildTimes)
