#!/usr/bin/python
import json
import requests

SERVER_NAME = "http://localhost:8080"

def getId(data):
    contentKey = unicode("content", "utf-8")
    idKey = unicode("id", "utf-8")
    #print data[contentKey]
    return data[contentKey][idKey]

with open('sampleBuildConfigs/dependantProjects.json') as f:
    bc_ids = []
    for line in f:
        headers = {'content-type': 'application/json'}
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/", data=line, headers=headers)
        data = json.loads(r.content)
        buildId = getId(data)
        bc_ids.append(buildId)

    print(bc_ids)

