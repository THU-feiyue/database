import json
import os
import shutil
from pathlib import Path
import statistics

from ..backend import term_value


class Frontend:
    def __init__(self, output_dir, template_dir, resource_dir):
        self.output_dir = output_dir
        self.template_dir = template_dir
        self.resource_dir = resource_dir

    def pre_build(self):
        pass

    def build(self, applicants, datapoints, programs, majors):
        pass

    def copy_resources(self, link):
        with open(self.resource_dir / "manifest.json", "r") as f:
            manifest: dict = json.load(f)

        for src, dest in manifest["mappings"].items():
            if link:
                if os.path.islink(self.output_dir / dest):
                    os.remove(self.output_dir / dest)
                os.symlink(self.resource_dir / src, self.output_dir / dest)
            elif os.path.isfile(self.resource_dir / src):
                shutil.copy(self.resource_dir / src, self.output_dir / dest)
            elif os.path.isdir(self.resource_dir / src):
                shutil.copytree(
                    self.resource_dir / src,
                    self.output_dir / dest,
                    dirs_exist_ok=True,
                )
            else:
                raise Exception(f"Resource {src} not exist")

    def copy_images(self, image_dir: Path):
        raise NotImplementedError

    def _preprocess(self, all_applicants, all_datapoints, all_programs, all_majors):
        self._set_applicants_by_term(all_datapoints, all_applicants)
        self.all_areas = self._get_areas(all_applicants)
        # get top programs & terms & GPA median & total programs for each major
        # get final destination for each applicant
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
                for term, applicants in self.applicants_by_term
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

                    if "最终去向" in datapoint and datapoint["最终去向"]:
                        applicant["__destination"] = datapoint["项目"][0]

                if applicant.get("GPA") is not None:
                    gpas.append(applicant["GPA"])

            major["__programs"] = sorted(
                list(major["__programs"].items()), key=lambda x: x[1], reverse=True
            )
            major["__gpa_median"] = (
                round(statistics.median(gpas), 2) if len(gpas) > 0 else None
            )

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
                for term, applicants in self.applicants_by_term
            ]

    def _set_applicants_by_term(self, datapoints: dict, applicants: dict) -> dict:
        self.applicants_by_term = {}

        for datapoint in datapoints.values():
            if datapoint["学年"] is None:
                continue
            self.applicants_by_term.setdefault(
                (datapoint["学年"], datapoint["学期"]), set()
            ).add((datapoint["申请人"][0]))

        self.applicants_by_term = sorted(
            [
                (term, sorted(term_applicants, key=lambda x: applicants[x]["专业"]))
                for term, term_applicants in self.applicants_by_term.items()
            ],
            key=lambda x: term_value(*x[0]),
            reverse=True,
        )

    def _get_areas(self, all_applicants: dict) -> dict:
        all_areas: dict[str, list] = {}
        for term, applicants in self.applicants_by_term:
            for applicant in applicants:
                applicant = all_applicants[applicant]
                areas = applicant["申请方向"]
                for area in areas:
                    all_areas.setdefault(area, []).append((term, applicant["_id"]))

        all_areas = dict(sorted(all_areas.items(), key=lambda x: x[0]))
        return all_areas
