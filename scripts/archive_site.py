from lxml import etree
import requests
import argparse

WAYBACK_URL = "https://web.archive.org/save/"
RETRIES = 5

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive a site")
    parser.add_argument("site", type=str)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    r = requests.get(args.site)
    sitemap_root = etree.fromstring(r.content)

    sites = [sitemap.getchildren()[0].text for sitemap in sitemap_root]
    sites = sites[args.start : args.end]

    print(
        f"Archiving {len(sites)} sites of {args.site} (from {args.start} to {args.end})"
    )

    for site in sites:
        for i in range(RETRIES):
            try:
                r = requests.get(WAYBACK_URL + site)
                r.raise_for_status()
                print(f"Archived {site}")
                break
            except BaseException as e:
                print(f"Failed to archive {site}, retrying (attempt {i+1}/{RETRIES})")
