from __future__ import annotations

import json

from jobpilot.jobs import fetch_board


STARTER_BOARDS = (
    ("greenhouse", "GitLab", "gitlab"),
    ("lever", "Nium", "nium"),
    ("ashby", "Ashby", "ashby"),
)


def main() -> int:
    counts: dict[str, int] = {}
    for provider, employer, token in STARTER_BOARDS:
        jobs = fetch_board(provider, employer, token)
        if not jobs:
            raise RuntimeError(f"{provider} starter board returned no current jobs")
        counts[provider] = len(jobs)
        for job in jobs:
            if job["provider"] != provider or not job["source_url"].startswith("https://"):
                raise RuntimeError(f"{provider} returned an invalid normalized job")
    print(json.dumps({"phase5_public_discovery": True, "job_counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
