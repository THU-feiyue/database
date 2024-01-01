from . import Frontend
from ..backend import term_value
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import statistics
from datetime import timezone, datetime, timedelta


class MkDocsFrontend(Frontend):
    def __init__(self, output_dir, template_dir, resource_dir):
        super().__init__(output_dir, template_dir, resource_dir)
        self.mkdocs_docs_dir = output_dir / "docs"

    def pre_build(self):
        env = Environment(loader=FileSystemLoader(self.template_dir), autoescape=True)
        self.applicant_template = env.get_template("applicant.jinja")
        self.major_template = env.get_template("major.jinja")
        self.program_template = env.get_template("program.jinja")
        self.mkdocs_template = env.get_template("mkdocs_config.jinja")
        self.index_template = env.get_template("index.jinja")
        self.applicant_index_template = env.get_template("applicant_index.jinja")
        self.major_index_template = env.get_template("major_index.jinja")
        self.program_index_template = env.get_template("program_index.jinja")

    def build(self, all_applicants, all_datapoints, all_programs, all_majors):
        self._preprocess(all_applicants, all_datapoints, all_programs, all_majors)

        output_dir = Path(self.output_dir)
        output_dir.mkdir(exist_ok=True)
        mkdocs_docs_dir = output_dir / "docs"
        mkdocs_docs_dir.mkdir(exist_ok=True)

        print("Generating applicant pages...", end=" ")
        self._build_applicant_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )
        print("done")

        print("Generating major pages...", end=" ")
        self._build_major_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )
        print("done")

        print("Generating program pages...", end=" ")
        self._build_program_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )
        print("done")

        print("Generating index pages...", end=" ")
        self._build_index_pages(
            all_applicants,
            all_datapoints,
            all_programs,
            all_majors,
        )
        print("done")

    def _preprocess(self, all_applicants, all_datapoints, all_programs, all_majors):
        self._set_applicants_by_term(all_datapoints, all_applicants)
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

                    if "最终去向" in datapoint:
                        applicant["__destination"] = datapoint["项目"][0]

                if "GPA" in applicant:
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

    def _build_applicant_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        for applicant in all_applicants.values():
            applicant_md = self.applicant_template.render(
                metadata={},
                applicant=applicant,
                majors=all_majors,
                programs=all_programs,
                datapoints=all_datapoints,
            )

            output_path = self.mkdocs_docs_dir / "applicant" / f"{applicant['ID']}.md"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(applicant_md)

    def _build_major_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        for major in all_majors.values():
            major_md = self.major_template.render(
                metadata={},
                major=major,
                applicants=all_applicants,
                programs=all_programs,
                datapoints=all_datapoints,
            )

            output_path = self.mkdocs_docs_dir / "major" / f"{major['ID']}.md"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(major_md)

    def _build_program_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
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

            program_md = self.program_template.render(
                metadata={},
                program=program,
                majors=all_majors,
                applicants=all_applicants,
                program_datapoints=program_datapoints,
            )

            output_path = self.mkdocs_docs_dir / "program" / f"{program['ID']}.md"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(program_md)

    def _build_index_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
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

        mkdocs_config = self.mkdocs_template.render(
            all_applicants=all_applicants,
            applicants_by_term=self.applicants_by_term,
            majors=sorted_majors,
            programs=sorted_programs,
            build_time=datetime.now(tz=timezone(timedelta(hours=+8))).strftime(
                "%Y年%m月%d日 %H:%M"
            ),
        )
        with open(self.output_dir / "mkdocs.yml", "w") as f:
            f.write(mkdocs_config)

        index_md = self.index_template.render(
            applicant_num=len(all_applicants),
            major_num=len(all_majors),
            program_num=len(all_programs),
        )
        with open(self.mkdocs_docs_dir / "index.md", "w") as f:
            f.write(index_md)

        applicant_index_md = self.applicant_index_template.render(
            applicants_by_term=self.applicants_by_term,
            applicants=all_applicants,
            majors=all_majors,
            programs=all_programs,
            datapoints=all_datapoints,
        )
        with open(self.mkdocs_docs_dir / "applicant" / "index.md", "w") as f:
            f.write(applicant_index_md)

        major_index_md = self.major_index_template.render(
            majors=sorted_majors,
        )
        with open(self.mkdocs_docs_dir / "major" / "index.md", "w") as f:
            f.write(major_index_md)

        program_index_md = self.program_index_template.render(
            programs=sorted_programs,
        )
        with open(self.mkdocs_docs_dir / "program" / "index.md", "w") as f:
            f.write(program_index_md)

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
                (term, applicants)
                for term, applicants in self.applicants_by_term.items()
            ],
            key=lambda x: term_value(*x[0]),
            reverse=True,
        )

        for i, term_tuple in enumerate(self.applicants_by_term):
            self.applicants_by_term[i] = (
                term_tuple[0],
                sorted(
                    list(term_tuple[1]),
                    key=lambda x: (applicants[x]["ID"]),
                    reverse=False,
                ),
            )
