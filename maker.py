import argparse
import requests
import os
import shutil
import glob
from datetime import timezone, datetime, timedelta
import statistics
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

api_base = None
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


def _filter_out_invalid(
    applicants: dict, datapoints: dict, programs: dict, majors: dict
):
    has_invalid = True

    # dependency: applicant <-> datapoint <-> program
    #             applicant <-> major
    def _applicant_valid(applicant: dict) -> bool:
        global has_invalid
        valid = (
            "数据点" in applicant
            and len(applicant["数据点"]) > 0
            and "专业" in applicant
            and len(applicant["专业"]) > 0
        )
        if not valid:
            return False
        for datapoint in applicant["数据点"]:
            if datapoint not in datapoints:
                has_invalid = True
                applicant["数据点"].remove(datapoint)
        if applicant["专业"][0] not in majors:
            return False
        return True

    def _program_valid(program: dict) -> bool:
        global has_invalid
        valid = (
            "项目" in program
            and len(program["项目"]) > 0
            and "学校" in program
            and len(program["学校"]) > 0
            and "数据点" in program
            and len(program["数据点"]) > 0
        )
        if not valid:
            return False
        for datapoint in program["数据点"]:
            if datapoint not in datapoints:
                has_invalid = True
                program["数据点"].remove(datapoint)
        return True

    def _datapoint_valid(datapoint: dict) -> bool:
        global has_invalid
        valid = (
            "项目" in datapoint
            and len(datapoint["项目"]) > 0
            and "学年" in datapoint
            and "学期" in datapoint
            and len(datapoint["学期"]) > 0
            and "申请人" in datapoint
            and len(datapoint["申请人"]) > 0
        )
        if not valid:
            return False
        for applicant in datapoint["申请人"]:
            if applicant not in applicants:
                has_invalid = True
                datapoint["申请人"].remove(applicant)
        if datapoint["项目"][0] not in programs:
            return False
        return True

    def _major_valid(major: dict) -> bool:
        global has_invalid
        valid = (
            "院系" in major
            and len(major["院系"]) > 0
            and "专业" in major
            and len(major["专业"]) > 0
            and "申请人" in major
            and len(major["申请人"]) > 0
        )
        if not valid:
            return False
        for applicant in major["申请人"]:
            if applicant not in applicants:
                has_invalid = True
                major["申请人"].remove(applicant)
        return True

    while has_invalid:
        has_invalid = False
        applicant_invalid = []
        program_invalid = []
        datapoint_invalid = []
        major_invalid = []

        # applicant
        for applicant in applicants.values():
            if not _applicant_valid(applicant):
                applicant_invalid.append(applicant["_id"])
                has_invalid = True
        for invalid_applicant in applicant_invalid:
            applicants.pop(invalid_applicant)

        for datapoint in datapoints.values():
            if not _datapoint_valid(datapoint):
                datapoint_invalid.append(datapoint["_id"])
                has_invalid = True
        for invalid_datapoint in datapoint_invalid:
            datapoints.pop(invalid_datapoint)

        for major in majors.values():
            if not _major_valid(major):
                major_invalid.append(major["_id"])
                has_invalid = True
        for invalid_major in major_invalid:
            majors.pop(invalid_major)

        # program
        for program in programs.values():
            if not _program_valid(program):
                program_invalid.append(program["_id"])
                has_invalid = True
        for invalid_program in program_invalid:
            programs.pop(invalid_program)


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

    # filter out invalid datapoints
    _filter_out_invalid(all_applicants, all_datapoints, all_programs, all_majors)

    # get the terms that each applicant applied for & update nickname
    for applicant in all_applicants.values():
        if "姓名/昵称" not in applicant:
            new_nickname = "申请人" + str(int(applicant["ID"].split("-")[1]))
            applicant["姓名/昵称"] = new_nickname

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
            (datapoint["申请人"][0])
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
    index_template = env.get_template("index.jinja")
    applicant_index_template = env.get_template("applicant_index.jinja")

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
        # do this work outside of jinja2 -- it's too complicated
        program_datapoints = all_datapoints.copy()
        program_datapoints = [
            datapoint
            for datapoint in all_datapoints.values()
            if datapoint["项目"][0] == program["_id"]
        ]
        for datapoint in program_datapoints:
            datapoint["申请人"] = datapoint["申请人"][0]

        program_md = program_template.render(
            metadata={},
            program=program,
            majors=all_majors,
            applicants=all_applicants,
            program_datapoints=program_datapoints,
        )

        output_path = mkdocs_docs_dir / "program" / f"{program['ID']}.md"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            f.write(program_md)
    print("done")

    # ====================

    sorted_majors = sorted(
        list(all_majors.values()),
        key=lambda x: len(x["申请人"]),
        reverse=True,
    )

    sorted_programs = sorted(
        list(all_programs.values()),
        key=lambda x: len(x["数据点"]),
        reverse=True,
    )

    mkdocs_config = mkdocs_template.render(
        all_applicants=all_applicants,
        applicants_by_term=applicants_by_term,
        majors=[x["ID"] for x in sorted_majors],
        programs=[x["ID"] for x in sorted_programs],
        build_time=datetime.now(tz=timezone(timedelta(hours=+8))).strftime(
            "%Y年%m月%d日 %H:%M (UTC+8)"
        ),
    )
    with open(output_dir / "mkdocs.yml", "w") as f:
        f.write(mkdocs_config)

    index_md = index_template.render(
        applicant_num=len(all_applicants),
        major_num=len(all_majors),
        program_num=len(all_programs),
    )
    with open(mkdocs_docs_dir / "index.md", "w") as f:
        f.write(index_md)

    applicant_index_md = applicant_index_template.render(
        applicants_by_term=applicants_by_term,
        applicants=all_applicants,
        majors=all_majors,
        programs=all_programs,
        datapoints=all_datapoints,
    )
    with open(mkdocs_docs_dir / "applicant" / "index.md", "w") as f:
        f.write(applicant_index_md)

    # create pseudo index pages for redirect
    with open(mkdocs_docs_dir / "major" / "index.md", "w") as f:
        pass
    with open(mkdocs_docs_dir / "program" / "index.md", "w") as f:
        pass

    for file in glob.glob(str(file_path / "resources" / "*")):
        if os.path.isfile(file):
            shutil.copy(file, output_dir)
        elif os.path.isdir(file):
            shutil.copytree(
                file, output_dir / os.path.basename(file), dirs_exist_ok=True
            )
