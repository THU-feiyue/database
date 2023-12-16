import argparse
import requests
import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

api_base = "https://cloud.seatable.io/dtable-server/api/v1"
api_key = None
base_token = None
dtable_uuid = None

file_path = Path(os.path.dirname(os.path.realpath(__file__)))


def _seatable_request(method: str, path: str, params: dict = None, data: dict = None):
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


def get_base_token() -> tuple[str, str]:
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
    return response["access_token"], response["dtable_uuid"]


def _get_all_rows(table_name: str):
    print("Getting all rows from", table_name, "...", end=" ", flush=True)
    response = _seatable_request("GET", "/rows", {"table_name": table_name})

    ret = {}
    for row in response["rows"]:
        ret[row["_id"]] = row

    print("done, got", len(response["rows"]), "rows")
    return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, required=True)
    parser.add_argument(
        "--api-base", type=str, default="https://cloud.seatable.io/dtable-server/api/v1"
    )
    parser.add_argument("--output-dir", type=str, default="output")
    args = parser.parse_args()

    api_key = args.api_key
    api_base = args.api_base

    # TODO: Filtering

    # get base token
    print("Getting base token...", end=" ", flush=True)
    base_token, dtable_uuid = get_base_token()
    print("done")

    # get all majors
    all_majors = _get_all_rows("本科专业")

    # get all applicants
    all_applicants = _get_all_rows("申请人")

    # get programs
    all_programs = _get_all_rows("项目")

    # get all datapoints
    all_datapoints = _get_all_rows("数据点")

    # get the terms that each applicant applied for
    for applicant in all_applicants.values():
        applied_terms = set()
        if "数据点" not in applicant:
            continue
        for datapoint in applicant["数据点"]:
            datapoint = all_datapoints[datapoint]
            applied_terms.add((datapoint["学年"], datapoint["学期"]))

        applied_terms = sorted(list(applied_terms), key=lambda x: x[0])
        applicant["__terms"] = "/".join(
            [f"{term[0]}{term[1]}" for term in applied_terms]
        )

    print("Generating applicant pages...", end=" ", flush=True)

    env = Environment(loader=FileSystemLoader(file_path / "templates"))
    applicant_template = env.get_template("applicant.jinja")
    mkdocs_template = env.get_template("mkdocs_config.jinja")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    mkdocs_docs_dir = output_dir / "docs"
    mkdocs_docs_dir.mkdir(exist_ok=True)

    applicant_keys = sorted(
        list(all_applicants.keys()), key=lambda x: all_applicants[x]["ID"]
    )

    print(all_datapoints)

    for applicant_id in applicant_keys:
        applicant = all_applicants[applicant_id]

        applicant_md = applicant_template.render(
            metadata={},
            applicant=applicant,
            majors=all_majors,
            programs=all_programs,
            datapoints=all_datapoints,
        )

        output_path = mkdocs_docs_dir / "applicant" / f"{applicant['ID']}.md"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            f.write(applicant_md)

    print("done")

    mkdocs_config = mkdocs_template.render(
        applicants=[all_applicants[x]["ID"] for x in applicant_keys],
    )
    with open(output_dir / "mkdocs.yml", "w") as f:
        f.write(mkdocs_config)

    shutil.copy(file_path / "templates" / "index.md", mkdocs_docs_dir / "index.md")
