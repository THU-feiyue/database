import argparse
import json
import os
import shutil
import glob
from datetime import timezone, datetime, timedelta
import statistics
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import feiyue.backend as backend

file_path = Path(os.path.dirname(os.path.realpath(__file__)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, required=True)
    parser.add_argument(
        "--api-base", type=str, default="https://cloud.seatable.io/dtable-server/api/v1"
    )
    parser.add_argument("--output-dir", type=str, default="output")
    parser.add_argument("--link-resources", action="store_true")
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()

    api_key = args.api_key
    backend.api.api_base = args.api_base

    cache_loaded = False
    cache_dir = file_path / ".cache"

    if args.cached:

        def load_cache(file_name: Path):
            with open(cache_dir / file_name, "r") as f:
                return json.load(f)

        # check if is cached already
        if os.path.isdir(file_path / ".cache"):
            print("Loading rows from cache...")
            try:
                all_applicants = load_cache("applicants.json")
                all_datapoints = load_cache("datapoints.json")
                all_programs = load_cache("programs.json")
                all_majors = load_cache("majors.json")
                cache_loaded = True
            except:
                shutil.rmtree(file_path / ".cache")

    if not cache_loaded:
        print("Getting all rows...")
        all_applicants, all_datapoints, all_programs, all_majors = backend.get_all_rows(
            api_key
        )
        if args.cached:
            cache_dir.mkdir(exist_ok=True)
            with open(cache_dir / "applicants.json", "w") as f:
                json.dump(all_applicants, f)
            with open(cache_dir / "datapoints.json", "w") as f:
                json.dump(all_datapoints, f)
            with open(cache_dir / "programs.json", "w") as f:
                json.dump(all_programs, f)
            with open(cache_dir / "majors.json", "w") as f:
                json.dump(all_majors, f)

    print(
        "Done, got",
        len(all_applicants),
        "applicants,",
        len(all_datapoints),
        "datapoints,",
        len(all_programs),
        "programs,",
        len(all_majors),
        "majors",
    )

    # filter out invalid datapoints
    backend.filter_out_invalid(all_applicants, all_datapoints, all_programs, all_majors)

    # get the terms that each applicant applied for & update nickname
    backend.set_term(all_applicants, all_datapoints, key="__term")
    backend.update_nickname(all_applicants)

    applicants_by_term = backend.get_applicants_by_term(all_datapoints, all_applicants)

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
            "%Y年%m月%d日 %H:%M"
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

    # copy or link resources
    with open(file_path / "resources" / "manifest.json", "r") as f:
        manifest: dict = json.load(f)

    for src, dest in manifest["mappings"].items():
        if args.link_resources:
            if os.path.exists(output_dir / dest):
                os.remove(output_dir / dest)
            os.symlink(file_path / "resources" / src, output_dir / dest)
        elif os.path.isfile(file_path / "resources" / src):
            shutil.copy(file_path / "resources" / src, output_dir / dest)
        elif os.path.isdir(file_path / "resources" / src):
            shutil.copytree(
                file_path / "resources" / src,
                output_dir / dest,
                dirs_exist_ok=True,
            )
        else:
            raise Exception(f"Resource {src} not exist")
