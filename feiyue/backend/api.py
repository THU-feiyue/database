import requests

api_base = None
base_token = None
dtable_uuid = None


def seatable_request(method: str, path: str, params: dict = None, data: dict = None):
    # make request
    response = requests.request(
        method,
        f"{api_base}/dtables/{dtable_uuid}{path}",
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
    response = requests.request(
        "GET",
        "https://cloud.seatable.io/api/v2.1/dtable/app-access-token/",
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
    response = seatable_request("GET", "/rows", {"table_name": table_name})

    ret = {}
    for row in response["rows"]:
        ret[row["_id"]] = row

    return ret
