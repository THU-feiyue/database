import argparse
import os
from pathlib import Path
import sys
import collections

sys.path.append(Path(os.path.dirname(os.path.realpath(__file__))).parent.as_posix())
import feiyue.backend.api as api
import feiyue.backend as backend


def get_duplicate_programs(programs: dict) -> dict[tuple[str, str], list]:
    program_by_name = {}
    for program in programs.values():
        if not program.get("学校") or not program.get("项目"):
            continue
        program_by_name.setdefault(
            (program["学校"].lower(), program["项目"].lower()), []
        ).append(program)

    return {
        name: programs
        for name, programs in program_by_name.items()
        if len(programs) > 1
    }


def get_incomplete_programs(programs: dict) -> list[str]:
    incomplete_programs = []
    for program in programs.values():
        if not program.get("学校") or not program.get("项目"):
            incomplete_programs.append(program["ID"])

    return incomplete_programs


def get_duplicate_datapoints_of_applicants(
    applicants: dict, datapoints: dict, programs: dict
) -> dict[str, list]:
    ret = {}
    for applicant in applicants.values():
        duplicate_programs = []
        if not applicant.get("数据点", []):
            continue
        duplicate_programs = [
            program
            for program, count in collections.Counter(
                [programs[datapoints[dp]["项目"][0]]["ID"] for dp in applicant["数据点"]]
            ).items()
            if count > 1
        ]
        if duplicate_programs:
            ret[applicant["ID"]] = duplicate_programs

    return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--api-base", type=str, default="https://cloud.seatable.io")
    parser.add_argument("--output", type=str, default="output/issues.log")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    def log(*_args, **_kwargs):
        with open(args.output, "a") as f:
            print(*_args, **_kwargs, file=f)
        print(*_args, **_kwargs, file=sys.stderr)

    api.api_base = args.api_base
    api.init_base_token(args.api_key)

    all_applicants, all_datapoints, all_programs, all_majors = backend.get_all_rows(
        args.api_key
    )

    duplicate_programs = get_duplicate_programs(all_programs)

    if len(duplicate_programs) == 0:
        print("No duplicate programs found.", file=sys.stderr)
    else:
        log("**Duplicate programs**\n")
        for (school, program_name), programs in duplicate_programs.items():
            log(f" - {program_name}@{school}: {[p['ID'] for p in programs]}")
        log("")

    incomplete_programs = get_incomplete_programs(all_programs)

    if len(incomplete_programs) == 0:
        print("No incomplete programs found.", file=sys.stderr)
    else:
        log("**Incomplete programs**")
        for program_id in incomplete_programs:
            log(f" - {program_id}")
        log("")

    duplicate_datapoints = get_duplicate_datapoints_of_applicants(
        all_applicants, all_datapoints, all_programs
    )

    if len(duplicate_datapoints) == 0:
        print("No duplicate datapoints found.", file=sys.stderr)
    else:
        log("**Duplicate datapoints**")
        for applicant_id, programs in duplicate_datapoints.items():
            log(f" - {applicant_id}: {programs}")
        log("")
