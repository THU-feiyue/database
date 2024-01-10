from . import Frontend
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import timezone, datetime, timedelta
import shutil


class MkDocsFrontend(Frontend):
    """
    Frontend for generating MkDocs files.

    File to be generated:
        - docs/
            - index.md
            - area.md
            - applicant/
                - index.md
                - <applicant_id>.md
            - major/
                - index.md
                - <major_id>.md
            - program/
                - index.md
                - <program_id>.md
        - mkdocs.yml
    """

    def __init__(self, output_dir, template_dir, resource_dir):
        super().__init__(output_dir, template_dir, resource_dir)
        self.mkdocs_docs_dir = output_dir / "docs"

    def pre_build(self):
        env = Environment(loader=FileSystemLoader(self.template_dir))
        self.applicant_template = env.get_template("applicant.jinja")
        self.major_template = env.get_template("major.jinja")
        self.program_template = env.get_template("program.jinja")
        self.mkdocs_template = env.get_template("mkdocs_config.jinja")
        self.index_template = env.get_template("index.jinja")
        self.applicant_index_template = env.get_template("applicant_index.jinja")
        self.major_index_template = env.get_template("major_index.jinja")
        self.program_index_template = env.get_template("program_index.jinja")
        self.area_index_template = env.get_template("area_index.jinja")

    def build(self, all_applicants, all_datapoints, all_programs, all_majors):
        self._preprocess(all_applicants, all_datapoints, all_programs, all_majors)

        output_dir = Path(self.output_dir)
        output_dir.mkdir(exist_ok=True)
        mkdocs_docs_dir = output_dir / "docs"
        mkdocs_docs_dir.mkdir(exist_ok=True)

        self._build_applicant_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_major_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_program_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_index_pages(
            all_applicants,
            all_datapoints,
            all_programs,
            all_majors,
        )

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
            all_majors=all_majors,
            all_programs=all_programs,
            applicants_by_term=self.applicants_by_term,
            majors=sorted_majors,
            programs=sorted_programs,
            build_time=datetime.now(tz=timezone(timedelta(hours=+8))).strftime(
                "%Y年%-m月%-d日 %H:%M"
            ),
        )
        with open(self.output_dir / "mkdocs.yml", "w") as f:
            f.write(mkdocs_config)

        index_md = self.index_template.render(
            applicant_num=len(all_applicants),
            major_num=len(all_majors),
            program_num=len(all_programs),
            area_num=len(self.all_areas),
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

        # area index page
        area_index_md = self.area_index_template.render(
            all_areas=self.all_areas,
            applicants=all_applicants,
            majors=all_majors,
            programs=all_programs,
            datapoints=all_datapoints,
        )
        with open(self.mkdocs_docs_dir / "area.md", "w") as f:
            f.write(area_index_md)

    def copy_images(self, image_dir: Path):
        shutil.copytree(image_dir, self.mkdocs_docs_dir / "images", dirs_exist_ok=True)
