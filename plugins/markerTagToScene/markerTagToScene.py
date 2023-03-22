import json
import sys
import time
import requests
import log

START_TIME = time.time()
FRAGMENT = json.loads(sys.stdin.read())

FRAGMENT_SERVER = FRAGMENT["server_connection"]
PLUGIN_DIR = FRAGMENT_SERVER["PluginDir"]

def callGraphQL(query, variables=None):
    # Session cookie for authentication
    graphql_port = str(FRAGMENT_SERVER['Port'])
    graphql_scheme = FRAGMENT_SERVER['Scheme']
    graphql_cookies = {'session': FRAGMENT_SERVER['SessionCookie']['Value']}
    graphql_headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
    }
    graphql_domain = FRAGMENT_SERVER['Host']
    if graphql_domain == "0.0.0.0":
        graphql_domain = "localhost"
    # Stash GraphQL endpoint
    graphql_url = f"{graphql_scheme}://{graphql_domain}:{graphql_port}/graphql"

    json = {'query': query}
    if variables is not None:
        json['variables'] = variables
    try:
        response = requests.post(graphql_url, json=json, headers=graphql_headers, cookies=graphql_cookies, timeout=20)
    except Exception as e:
        exit_plugin(err=f"[FATAL] Error with the graphql request {e}")
    if response.status_code == 200:
        result = response.json()
        if result.get("error"):
            for error in result["error"]["errors"]:
                raise Exception(f"GraphQL error: {error}")
            return None
        if result.get("data"):
            return result.get("data")
    elif response.status_code == 401:
        exit_plugin(err="HTTP Error 401, Unauthorised.")
    else:
        raise ConnectionError(f"GraphQL query failed: {response.status_code} - {response.content}")



def exit_plugin(msg=None, err=None):
    if msg is None and err is None:
        msg = "plugin ended"
    log.LogDebug("Execution time: {}s".format(round(time.time() - START_TIME, 5)))
    output_json = {"output": msg, "error": err}
    print(json.dumps(output_json))
    sys.exit()



def graphql_getSceneTags(sceneID):
    query = """
        query FindScene($id:ID!) {
            findScene(id: $id) {
                tags {
                    id
                }
            }
        }
    """
    variables = {
        "id": sceneID
    }
    result = callGraphQL(query, variables)
    findScene = result.get('findScene')
    if findScene.get('tags') is not None:
        return findScene.get('tags')

    return []



def graphql_setSceneTags(sceneID, tagIDs: list):
    query = """
        mutation SceneUpdate($input: SceneUpdateInput!) {
            sceneUpdate(input: $input) {
                id
            }
        }
    """
    variables = {
        "input": {
            "id": sceneID,
            "tag_ids": tagIDs
        }
    }
    result = callGraphQL(query, variables)
    return result



def main():

    CONTEXT = FRAGMENT['args']['hookContext']['input']

    primaryTagID = CONTEXT['primary_tag_id']
    sceneID = CONTEXT['scene_id']

    if not primaryTagID or not sceneID:
        return

    sceneTags = graphql_getSceneTags(sceneID)
    tagIDs = []

    for sceneTags in sceneTags:
        tagID = sceneTags['id'];
        if tagID == primaryTagID:
            log.LogDebug("Primary tag already exists on scene")
            return

        tagIDs.append(tagID);

    # set the tag on the scene if not present
    tagIDs.append(primaryTagID);

    graphql_setSceneTags(sceneID, tagIDs);
    log.LogDebug("Added primary tag " + primaryTagID + " to scene " + sceneID)



if __name__ == '__main__':
	main()