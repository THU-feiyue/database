import json
import os
import shutil
from pathlib import Path


class Frontend:
    def __init__(self, output_dir, template_dir, resource_dir):
        self.output_dir = output_dir
        self.template_dir = template_dir
        self.resource_dir = resource_dir

    def pre_build(self, applicants, datapoints, programs, majors):
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
