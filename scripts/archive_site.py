from lxml import etree
import requests
import argparse
import time

WAYBACK_URL = "https://web.archive.org/save/"
RETRIES = 5
TIME_LIMIT = 6 * 60 * 59  # 6 hours

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive a site")
    parser.add_argument("site", type=str)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    start_time = time.time()

    r = requests.get(args.site)
    sitemap_root = etree.fromstring(r.content)

    sites = [sitemap.getchildren()[0].text for sitemap in sitemap_root]
    sites = sites[args.start : args.end]

    print(
        f"Archiving {len(sites)} sites of {args.site} (from {args.start} to {args.end})"
    )

    while len(sites) > 0:
        if time.time() - start_time > TIME_LIMIT:
            print(f"Time limit reached, skipping remaining {len(sites)} sites")
            break
        site = sites.pop(0)
        for i in range(RETRIES + 1):
            try:
                r = requests.get(WAYBACK_URL + site)
                r.raise_for_status()
                print(f"Archived {site}")
                break
            except KeyboardInterrupt:
                exit(0)
            except BaseException as e:
                print(f"Failed to archive {site}, retrying (attempt {i+1}/{RETRIES})")
        else:
            sites.append(site)
            print(f"Failed to archive {site} after {RETRIES} attempts")
