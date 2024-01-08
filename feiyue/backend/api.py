import requests

_api_key = None
api_base = None
base_token = None
dtable_uuid = None


def seatable_request(method: str, path: str, params: dict = None, data: dict = None):
    # make request
    response = requests.request(
        method,
        f"{api_base}/dtable-server/api/v1/dtables/{dtable_uuid}{path}",
        params=params,
        data=data,
        headers={"Accept": "application/json", "Authorization": "Bearer " + base_token},
    )

    # check response
    if response.status_code != 200:
        raise Exception(
            f"Request failed with status {response.status_code} and message {response.text}"
        )

    return response.json()


def init_base_token(api_key: str):
    global _api_key
    _api_key = api_key
    response = requests.request(
        "GET",
        f"{api_base}/api/v2.1/dtable/app-access-token/",
        headers={"Accept": "application/json", "Authorization": "Bearer " + api_key},
    )

    if response.status_code != 200:
        raise Exception(
            f"Request failed with status {response.status_code} and message {response.text}"
        )

    response = response.json()
    global base_token, dtable_uuid
    base_token = response["access_token"]
    dtable_uuid = response["dtable_uuid"]


def get_all_rows(table_name: str):
    ret = {}
    query_start = 0
    BATCH_SIZE = 100
    while True:
        response = seatable_request(
            "GET",
            "/rows",
            {"table_name": table_name, "start": query_start, "limit": BATCH_SIZE},
        )

        for row in response["rows"]:
            ret[row["_id"]] = row
        if len(response["rows"]) < BATCH_SIZE:
            break
        query_start += BATCH_SIZE

    return ret


def get_image_direct_url(file_name: str) -> str:
    response = requests.request(
        "GET",
        f"{api_base}/api/v2.1/dtable/app-download-link",
        params={"path": f"{file_name}"},
        headers={"Accept": "application/json", "Authorization": "Bearer " + _api_key},
    )
    return response.json()["download_link"]
