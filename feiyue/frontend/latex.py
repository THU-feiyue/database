from . import Frontend
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import shutil
from datetime import timezone, datetime, timedelta
import re


class LatexFrontend(Frontend):
    """
    Frontend for generating LaTeX files.

    Files to be generated:
        - main.tex
        - all_areas.tex
        - applicant/
            - <applicant_id>.tex
        - major/
            - <major_id>.tex
        - program/
            - <program_id>.tex
    """

    def __init__(self, output_dir: Path, template_dir: Path, resource_dir: Path):
        super().__init__(output_dir, template_dir, resource_dir)
        self.docs_dir = output_dir / "latex"

    def pre_build(self):
        def latex_escape(x) -> str:
            s = str(x)
            s = s.replace("\\", "\\textbackslash{}")
            s = s.replace("{", "\\{")
            s = s.replace("}", "\\}")
            s = s.replace("$", "\\$")
            s = s.replace("&", "\\&")
            s = s.replace("#", "\\#")
            s = s.replace("^", "\\textasciicircum{}")
            s = s.replace("_", "\\_")
            s = s.replace("~", "\\textasciitilde{}")
            s = s.replace("%", "\\%")

            return s

        list_re = re.compile(r"^( +)(\*|-|\+)", flags=re.MULTILINE)

        def multiply_list_spaces(s: str) -> str:
            """
            Multiply the number of spaces of list items by 2.

            SeaTable's editor uses 2 spaces for indentation, but `markdown` package
            in LaTeX only supports 4. (https://github.com/Witiko/markdown/issues/55)
            """
            return list_re.sub(lambda x: " " * (len(x.group(1)) * 2) + x.group(2), s)

        env = Environment(loader=FileSystemLoader(self.template_dir))
        env.filters["escape"] = latex_escape
        env.filters["fix_list"] = multiply_list_spaces
        self.applicant_template = env.get_template("applicant.jinja")
        self.major_template = env.get_template("major.jinja")
        self.program_template = env.get_template("program.jinja")
        self.area_template = env.get_template("all_areas.jinja")
        self.main_template = env.get_template("main.jinja")

    def build(self, all_applicants, all_datapoints, all_programs, all_majors):
        self._preprocess(all_applicants, all_datapoints, all_programs, all_majors)

        self.docs_dir.mkdir(exist_ok=True, parents=True)

        self._build_applicant_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_major_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_program_pages(
            all_applicants, all_datapoints, all_programs, all_majors
        )

        self._build_area_page(all_applicants, all_datapoints, all_programs, all_majors)

        self._build_main_page(all_applicants, all_datapoints, all_programs, all_majors)

    def _build_applicant_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        for applicant in all_applicants.values():
            applicant_tex = self.applicant_template.render(
                applicant=applicant,
                majors=all_majors,
                programs=all_programs,
                datapoints=all_datapoints,
            )

            output_path = self.docs_dir / "applicant" / f"{applicant['ID']}.tex"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(applicant_tex)

    def _build_major_pages(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        for major in all_majors.values():
            major_tex = self.major_template.render(
                major=major,
                applicants=all_applicants,
                datapoints=all_datapoints,
                programs=all_programs,
            )

            output_path = self.docs_dir / "major" / f"{major['ID']}.tex"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(major_tex)

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

            program_tex = self.program_template.render(
                program=program,
                majors=all_majors,
                applicants=all_applicants,
                datapoints=all_datapoints,
                program_datapoints=program_datapoints,
            )

            output_path = self.docs_dir / "program" / f"{program['ID']}.tex"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "w") as f:
                f.write(program_tex)

    def _build_area_page(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        area_tex = self.area_template.render(
            all_areas=self.all_areas,
            applicants=all_applicants,
            majors=all_majors,
            programs=all_programs,
            datapoints=all_datapoints,
        )
        with open(self.docs_dir / "all_areas.tex", "w") as f:
            f.write(area_tex)

    def _build_main_page(
        self, all_applicants, all_datapoints, all_programs, all_majors
    ):
        sorted_majors = sorted(
            list(all_majors.values()),
            key=lambda x: (x["院系"], x["ID"]),
        )

        sorted_programs = sorted(
            list(all_programs.values()),
            key=lambda x: (len(x["数据点"]), x["ID"]),
            reverse=True,
        )

        main_latex = self.main_template.render(
            applicants_by_term=self.applicants_by_term,
            applicants=all_applicants,
            programs=sorted_programs,
            majors=sorted_majors,
            build_date=datetime.now(tz=timezone(timedelta(hours=+8))).strftime(
                "%Y年%-m月%-d日"
            ),
        )
        with open(self.docs_dir / "main.tex", "w") as f:
            f.write(main_latex)

    def copy_images(self, image_dir: Path):
        shutil.copytree(image_dir, self.docs_dir / "images", dirs_exist_ok=True)
