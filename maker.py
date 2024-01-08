import argparse
import json
import os
import shutil
from pathlib import Path

import feiyue.backend as backend
from feiyue.frontend.mkdocs import MkDocsFrontend
from feiyue.frontend.latex import LatexFrontend

file_path = Path(os.path.dirname(os.path.realpath(__file__)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--api-base", type=str, default="https://cloud.seatable.io")
    parser.add_argument("--output-dir", type=str, default="output")
    parser.add_argument(
        "--link-resources",
        action="store_true",
        help="create symlinks instead of copying resources",
    )
    parser.add_argument(
        "--cached",
        action="store_true",
        help="use data cached on device without querying the API",
    )
    parser.add_argument("--frontend", type=str, required=True, help="mkdocs or latex")
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
        if os.path.isdir(cache_dir):
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
        if api_key is None:
            raise Exception("API key is not provided")
        print("Getting all rows...")
        all_applicants, all_datapoints, all_programs, all_majors = backend.get_all_rows(
            api_key
        )

        # replace direct image urls
        print("Updating image urls...")
        backend.update_image_url(all_applicants)

        # create cache
        cache_dir.mkdir(exist_ok=True)
        with open(cache_dir / "applicants.json", "w") as f:
            json.dump(all_applicants, f, ensure_ascii=False)
        with open(cache_dir / "datapoints.json", "w") as f:
            json.dump(all_datapoints, f, ensure_ascii=False)
        with open(cache_dir / "programs.json", "w") as f:
            json.dump(all_programs, f, ensure_ascii=False)
        with open(cache_dir / "majors.json", "w") as f:
            json.dump(all_majors, f, ensure_ascii=False)

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

    # build
    if args.frontend == "mkdocs":
        frontend = MkDocsFrontend(
            file_path / args.output_dir,
            file_path / "templates" / "mkdocs",
            file_path / "resources" / "mkdocs",
        )
    elif args.frontend == "latex":
        frontend = LatexFrontend(
            file_path / args.output_dir,
            file_path / "templates" / "latex",
            file_path / "resources" / "latex",
        )
    else:
        raise Exception(f"Invalid frontend {args.frontend}")

    frontend.pre_build()
    frontend.build(all_applicants, all_datapoints, all_programs, all_majors)
    frontend.copy_resources(args.link_resources)
