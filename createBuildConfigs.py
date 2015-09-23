#!/usr/bin/python
import json
import requests

SERVER_NAME = "http://localhost:8080"

with open('sampleBuildConfigs/dependantProjects.json') as f:
    bc_ids = []
    for line in f:
        headers = {'content-type': 'application/json'}
        r = requests.post(SERVER_NAME + "/pnc-rest/rest/build-configurations/", data=line, headers=headers)
        print r.content
        data = json.loads(r.content)
        bc_ids.append(data["id"])
    print bc_ids