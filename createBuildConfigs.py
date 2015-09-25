#!/usr/bin/python
import json
import requests
import random
import string

SERVER_NAME = "http://localhost:8080"
buildConfigIds = []
recordIds = []

def getId(data):
    contentKey = unicode("content", "utf-8")
    idKey = unicode("id", "utf-8")
    return data[contentKey][idKey]

def fireBuilds(idList):
    for i in idList:
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/" + str(i) + "/build")
        jsonContent = json.loads(r.content)
        recordId = getId(jsonContent)
        recordIds.append(recordId)

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
