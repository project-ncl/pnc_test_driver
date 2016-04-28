
import argparse
import ConfigParser
import json
import logging
import os
import re
import requests
import sys
import tempfile
import traceback

from git import Repo
from time import sleep

requests.packages.urllib3.disable_warnings()

# setup logging to print timestamps
logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_CONFIG_FILE = "config.ini"
DEFAULT_RESULTS_LIST_JSON = 'driver_results.json'

configFile = DEFAULT_CONFIG_FILE
resultsFile = DEFAULT_RESULTS_LIST_JSON

CONTENT_KEY = unicode("content", "utf-8")
SCM_REPO_URL_KEY = unicode("scmRepoURL", "utf-8")
SCM_REVISION_KEY = unicode("scmRevision", "utf-8")
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
            logger.error("An error occured while making a remote request to: {} [request_type={}]".format(rest_point, request_type))
            traceback.print_exc(file=sys.stdout)
        logger.warn("Retrying in 10 seconds...")
        sleep(10)

    logger.error("Retries exceeded! Could not get valid response.")
    sys.exit(1)


def load(value):
    parser = ConfigParser.ConfigParser()
    parser.read(configFile)
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

    logger.error("Could not get keycloak token")
    return None

def getHeaders():
    token = getToken(USERNAME, PASSWORD, REALM, CLIENT_ID, KEYCLOAK_URL)
    return {'content-type': 'application/json', "Authorization": "Bearer " + token}

def getRecord(recordId):
    """ Return json object containing build record info"""
    response = get(SERVER_NAME + "/pnc-rest/rest/build-records/" + str(recordId), headers=getHeaders())
    return json.loads(response.content)

def checkoutGitSources(repoUrl, revision):
    repoDir = os.path.join(tempfile.gettempdir(), revision)
    if (os.path.isdir(repoDir)):
        logger.warn("Found existing git checkout directory: " + str(repoDir))
        gitRepo = Repo(repoDir)
    else:
        gitRepo = Repo.clone_from(repoUrl, repoDir)
    gitRepo.head.reference = gitRepo.commit(revision)
    gitRepo.head.reset(index=True, working_tree=True)
    return gitRepo

def getSourceChangesInLastCommit(repo):
    """ Get the changes made in the most recent commit"""
    return repo.git.diff('HEAD~1')

def examinePom(diff):
    """Check the POM file in the given directory for automated modifications"""
    checkPomForRedhatVersionUpdate(diff)

POM_VERSION_UPDATE_REGEX_STR = r'^-\s*<version>([-\.\w]+)</version>\s*\+\s*<version>\1-redhat-1</version>'
POM_VERSION_UPDATE_REGEX = re.compile(POM_VERSION_UPDATE_REGEX_STR, re.MULTILINE)

def checkPomForRedhatVersionUpdate(diff):
    """Check the POM file diff for the redhat version update"""
    search = POM_VERSION_UPDATE_REGEX.search(diff)
    assert(search is not None)

def checkBuilds(recordIds):
    """Given a list of build record Ids, check the for a correct build result"""

    for recordId in recordIds:
        record = getRecord(recordId)

        recordContent = getRecord(recordId)
        if (not hasValidScmRepoUrlAndRevision(recordContent)):
            logger.warn("Unable to find valid scm info for build record id: " + str(recordId))
            continue

        gitRepo = checkoutGitSources(recordContent[CONTENT_KEY][SCM_REPO_URL_KEY], recordContent[CONTENT_KEY][SCM_REVISION_KEY])
        logger.info("Checked out sources to: " + gitRepo.working_dir)
        diff = getSourceChangesInLastCommit(gitRepo)
        examinePom(diff)

def hasValidScmRepoUrlAndRevision(buildRecord):
    if buildRecord is None:
        return False
    if buildRecord[CONTENT_KEY][SCM_REPO_URL_KEY] is None:
        return False
    if buildRecord[CONTENT_KEY][SCM_REVISION_KEY] is None:
        return False
    return True

def loadResultsFile(filename):
    with open(filename) as f:
        results = json.loads(f.read())
        return results
    return None


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description='Check out sources from a git repo and verify contents.')
    argparser.add_argument('results_file', default=DEFAULT_RESULTS_LIST_JSON,
                           help='ini file containing remote server info and execution config')
    argparser.add_argument('-c', '--config', default=DEFAULT_CONFIG_FILE,
                           help='ini file containing remote server info and execution config')

    args = argparser.parse_args()

    configFile = args.config
    resultsFile = args.results_file

    SERVER_NAME = load("SERVER_NAME").rstrip('/')
    USERNAME = load("USERNAME")
    PASSWORD = load("PASSWORD")
    REALM = load("REALM")
    CLIENT_ID = load("CLIENT_ID")
    KEYCLOAK_URL = load("KEYCLOAK_URL")
    NUMBER_OF_BUILDS = int(load("NUMBER_OF_BUILDS"))

    if not REALM:
        logger.error("No auth realm found, check config file: " + str(configFile))
        sys.exit()

    results = loadResultsFile(resultsFile)
    recordIds = results["record_ids"]
    logger.info("Checking record ids: " + str(recordIds))
    checkBuilds(recordIds)

