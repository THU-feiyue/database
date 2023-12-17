import argparse
import requests
import os
import shutil
import statistics
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


def _term_converted(year: str, term: str) -> float:
    if year is None:
        return 0

    year = int(year)
    if term == "Spring":
        year += 0.1
    elif term == "Summer":
        year += 0.2
    elif term == "Fall":
        year += 0.3
    elif term == "Winter":
        year += 0.4

    return year


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
        last_year, last_term = None, None
        latest_term_value = 0
        for datapoint in applicant.get("数据点", []):
            datapoint = all_datapoints[datapoint]
            term_converted_value = _term_converted(datapoint["学年"], datapoint["学期"])
            if term_converted_value > latest_term_value:
                last_year = datapoint["学年"]
                last_term = datapoint["学期"]
                latest_term_value = term_converted_value

        applicant["__term"] = (last_year, last_term)

    applicants_by_term = {}

    for datapoint in all_datapoints.values():
        if datapoint["学年"] is None:
            continue
        applicants_by_term.setdefault((datapoint["学年"], datapoint["学期"]), set()).add(
            datapoint["申请人"][0]
        )

    applicants_by_term = sorted(
        [(term, applicants) for term, applicants in applicants_by_term.items()],
        key=lambda x: _term_converted(*x[0]),
        reverse=True,
    )

    for i, term_tuple in enumerate(applicants_by_term):
        applicants_by_term[i] = (
            term_tuple[0],
            sorted(
                list(term_tuple[1]),
                key=lambda x: (all_applicants[x]["ID"]),
                reverse=False,
            ),
        )

    # ====================

    env = Environment(loader=FileSystemLoader(file_path / "templates"))
    applicant_template = env.get_template("applicant.jinja")
    major_template = env.get_template("major.jinja")
    program_template = env.get_template("program.jinja")
    mkdocs_template = env.get_template("mkdocs_config.jinja")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    mkdocs_docs_dir = output_dir / "docs"
    mkdocs_docs_dir.mkdir(exist_ok=True)

    print("Generating applicant pages...", end=" ", flush=True)

    for applicant in all_applicants.values():
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

    # ====================

    print("Generating major pages...", end=" ", flush=True)

    # get top programs & terms & GPA median & total programs for each major
    for major in all_majors.values():
        major["__applicants_by_term"] = [
            (
                term,
                [
                    applicant
                    for applicant in applicants
                    if all_applicants[applicant]["专业"][0] == major["_id"]
                ],
            )
            for term, applicants in applicants_by_term
        ]

        major["__programs"] = {}
        major["__program_count"] = 0
        gpas = []
        for applicant in major.get("申请人", []):
            applicant = all_applicants[applicant]
            for datapoint in applicant.get("数据点", []):
                datapoint = all_datapoints[datapoint]
                if datapoint["项目"][0] not in major["__programs"]:
                    major["__programs"][datapoint["项目"][0]] = 0
                major["__programs"][datapoint["项目"][0]] += 1
                major["__program_count"] += 1

            if "GPA" in applicant:
                gpas.append(applicant["GPA"])

        major["__programs"] = sorted(
            list(major["__programs"].items()), key=lambda x: x[1], reverse=True
        )
        major["__gpa_median"] = (
            round(statistics.median(gpas), 2) if len(gpas) > 0 else None
        )

    for major in all_majors.values():
        major_md = major_template.render(
            metadata={},
            major=major,
            applicants=all_applicants,
            programs=all_programs,
            datapoints=all_datapoints,
        )

        output_path = mkdocs_docs_dir / "major" / f"{major['ID']}.md"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            f.write(major_md)
    print("done")

    # ====================

    print("Generating program pages...", end=" ", flush=True)

    # get terms for each program
    for program in all_programs.values():
        program["__applicants_by_term"] = [
            (
                term,
                [
                    applicant
                    for applicant in applicants
                    if any(
                        all_datapoints[datapoint]["项目"][0] == program["_id"]
                        for datapoint in all_applicants[applicant]["数据点"]
                    )
                ],
            )
            for term, applicants in applicants_by_term
        ]

    for program in all_programs.values():
        program_md = program_template.render(
            metadata={},
            program=program,
            majors=all_majors,
            applicants=all_applicants,
            datapoints=all_datapoints,
        )

        output_path = mkdocs_docs_dir / "program" / f"{program['ID']}.md"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            f.write(program_md)
    print("done")

    # ====================

    sorted_majors = [
        x for x in list(all_majors.values()) if "申请人" in x and len(x["申请人"]) > 0
    ]
    sorted_majors = sorted(
        sorted_majors,
        key=lambda x: len(x["申请人"]),
        reverse=True,
    )

    sorted_programs = [
        x for x in list(all_programs.values()) if "数据点" in x and len(x["数据点"]) > 0
    ]
    sorted_programs = sorted(
        sorted_programs,
        key=lambda x: len(x["数据点"]),
        reverse=True,
    )

    mkdocs_config = mkdocs_template.render(
        all_applicants=all_applicants,
        applicants_by_term=applicants_by_term,
        majors=[x["ID"] for x in sorted_majors],
        programs=[x["ID"] for x in sorted_programs],
    )
    with open(output_dir / "mkdocs.yml", "w") as f:
        f.write(mkdocs_config)

    shutil.copy(file_path / "templates" / "index.md", mkdocs_docs_dir / "index.md")
