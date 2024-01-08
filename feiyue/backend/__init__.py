import re
from pathlib import Path
from . import api


_image_url_pattern = re.compile(
    r"https://.+?/workspace/[0-9]+?/asset/.+?(/images/auto-upload/.+?.png)"
)


def get_all_rows(api_key: str) -> tuple[dict, dict, dict, dict]:
    api.init_base_token(api_key)
    all_majors = api.get_all_rows("本科专业")
    all_applicants = api.get_all_rows("申请人")
    all_programs = api.get_all_rows("项目")
    all_datapoints = api.get_all_rows("数据点")

    return all_applicants, all_datapoints, all_programs, all_majors


def term_value(year: int, term: str) -> float:
    if year is None:
        return 0

    year = int(year)
    terms = ["Spring", "Summer", "Fall", "Winter"]
    year += (terms.index(term) + 1) / 10

    return year


def filter_out_invalid(
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


def set_term(applicants: dict, datapoints: dict, key: str):
    for applicant in applicants.values():
        # get max term
        applicant[key] = max(
            [(datapoints[dp]["学年"], datapoints[dp]["学期"]) for dp in applicant["数据点"]],
            key=lambda x: term_value(x[0], x[1]),
        )


def update_nickname(applicants: dict):
    for applicant in applicants.values():
        if "姓名/昵称" not in applicant:
            new_nickname = "申请人" + str(int(applicant["ID"].split("-")[1]))
            applicant["姓名/昵称"] = new_nickname


def update_image_url(applicants: dict):
    for applicant in applicants.values():
        summary = applicant.get("申请总结", None)
        if summary is None:
            continue
        # replace with retrived url
        summary = re.sub(
            _image_url_pattern, lambda m: api.get_image_direct_url(m.group(1)), summary
        )
        applicant["申请总结"] = summary
