from __future__ import annotations

from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from jobpilot.settings import TargetingSettings
from jobpilot.storage.database import Database, utc_now_text

PROVIDERS = {"greenhouse", "lever", "ashby"}
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
YEARS_RE = re.compile(r"\b(\d{1,2})(?:\s*(?:-|to)\s*(\d{1,2}))?\+?\s+years?\b", re.I)
STOPWORDS = {
    "about", "after", "also", "and", "are", "but", "for", "from", "have", "into", "job", "more",
    "our", "role", "team", "that", "the", "their", "this", "with", "work", "will", "you", "your",
    "data", "experience", "required", "preferred", "skills", "using", "years",
}
REQUIRED_MARKERS = ("required", "requirements", "must have", "minimum", "at least", "proficient", "experience with")
PREFERRED_MARKERS = ("preferred", "nice to have", "bonus", "ideally")
NO_SPONSORSHIP = ("no sponsorship", "cannot sponsor", "can t sponsor", "unable to sponsor", "not sponsor", "without sponsorship")
YES_SPONSORSHIP = ("visa sponsorship", "sponsorship available", "will sponsor", "can sponsor")
REMOTE_RESTRICTED = ("united states only", "u s only", "us only", "must be based in the us", "must reside in the us")
LEGAL_SUFFIXES = {"inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "pvt", "private"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _plain(value: object) -> str:
    parser = _TextExtractor()
    parser.feed(unescape(str(value or "")))
    return "\n".join(parser.parts)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).casefold()).strip()


def _employer_key(value: object) -> str:
    parts = [part for part in _key(value).split() if part not in LEGAL_SUFFIXES]
    return " ".join(parts)


def _url(value: object) -> str:
    text = _clean(value)
    if len(text) > 2000:
        raise ValueError("job URL exceeds 2000 characters")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("job URL must be an absolute credential-free HTTP(S) URL")
    return text


def _board_token(value: object) -> str:
    token = _clean(value)
    if not TOKEN_RE.fullmatch(token):
        raise ValueError("board identifier must contain only letters, numbers, '_' or '-'")
    return token


def board_url(provider: str, token: str) -> str:
    token = _board_token(token)
    if provider == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if provider == "lever":
        return f"https://api.lever.co/v0/postings/{token}?mode=json"
    if provider == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
    raise ValueError(f"unsupported job provider: {provider}")


def _json_get(url: str, *, timeout: float = 20.0) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "JobPilotLocal/0.1"})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"job board returned HTTP {response.status}")
        body = response.read(8 * 1024 * 1024 + 1)
    if len(body) > 8 * 1024 * 1024:
        raise RuntimeError("job board response exceeded 8 MiB")
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("job board returned invalid JSON") from exc


def _employment(value: object, description: str = "") -> str:
    text = _key(value) or _key(description[:3000])
    if any(term in text for term in ("full time", "fulltime", "permanent")):
        return "permanent_full_time"
    if "part time" in text or "parttime" in text:
        return "part_time"
    if "contract" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "temporary" in text or "temp " in f"{text} ":
        return "temporary"
    return ""


def _workplace(value: object, location: str, description: str = "") -> str:
    text = _key(value)
    if "remote" in text:
        return "remote"
    if "hybrid" in text:
        return "hybrid"
    if "site" in text or "office" in text:
        return "onsite"
    combined = _key(f"{location} {description[:1000]}")
    if "remote" in combined:
        return "remote"
    if "hybrid" in combined:
        return "hybrid"
    return "onsite" if location else ""


def _job(provider: str, board_token: str, employer: str, source_id: object, *, title: object, location: object,
         description: object, workplace: object = "", employment: object = "", source_url: object,
         apply_url: object = "", published_at: object = "") -> dict[str, Any]:
    title_text = _clean(title)
    employer_text = _clean(employer)
    location_text = _clean(location) or "Unknown"
    description_text = _plain(description)
    if not title_text or not employer_text or not description_text:
        raise ValueError("job requires employer, title, and description")
    if len(title_text) > 300 or len(employer_text) > 200 or len(location_text) > 300:
        raise ValueError("job employer/title/location exceeds the supported size")
    source_url_text = _url(source_url)
    source_id_text = _clean(source_id) or sha256(source_url_text.encode()).hexdigest()[:24]
    return {
        "provider": provider,
        "board_token": board_token,
        "source_job_id": source_id_text,
        "employer": employer_text,
        "title": title_text,
        "location": location_text,
        "workplace_type": _workplace(workplace, location_text, description_text),
        "employment_type": _employment(employment, description_text),
        "source_url": source_url_text,
        "apply_url": _url(apply_url) if _clean(apply_url) else None,
        "description": description_text[:100_000],
        "published_at": _clean(published_at) or None,
    }


def parse_board_payload(provider: str, employer: str, token: str, payload: object) -> list[dict[str, Any]]:
    token = _board_token(token)
    jobs: list[dict[str, Any]] = []
    if provider == "greenhouse":
        if not isinstance(payload, Mapping) or not isinstance(payload.get("jobs"), list):
            raise RuntimeError("Greenhouse payload is missing jobs[]")
        for item in payload["jobs"]:
            if not isinstance(item, Mapping) or not item.get("id") or not item.get("title"):
                continue
            jobs.append(_job(
                provider, token, employer, item["id"], title=item["title"],
                location=(item.get("location") or {}).get("name", ""), description=item.get("content", ""),
                source_url=item.get("absolute_url", ""), published_at=item.get("updated_at", ""),
            ))
    elif provider == "lever":
        if not isinstance(payload, list):
            raise RuntimeError("Lever payload must be a job list")
        for item in payload:
            if not isinstance(item, Mapping) or not item.get("id") or not item.get("text"):
                continue
            categories = item.get("categories") or {}
            jobs.append(_job(
                provider, token, employer, item["id"], title=item["text"], location=categories.get("location", ""),
                description=item.get("descriptionPlain") or item.get("description", ""),
                workplace=item.get("workplaceType", ""), employment=categories.get("commitment", ""),
                source_url=item.get("hostedUrl", ""), apply_url=item.get("applyUrl", ""),
            ))
    elif provider == "ashby":
        if not isinstance(payload, Mapping) or not isinstance(payload.get("jobs"), list):
            raise RuntimeError("Ashby payload is missing jobs[]")
        for item in payload["jobs"]:
            if not isinstance(item, Mapping) or item.get("isListed") is False or not item.get("title"):
                continue
            jobs.append(_job(
                provider, token, employer, item.get("id") or item.get("jobUrl", ""), title=item["title"],
                location=item.get("location", ""), description=item.get("descriptionPlain") or item.get("descriptionHtml", ""),
                workplace=item.get("workplaceType", ""), employment=item.get("employmentType", ""),
                source_url=item.get("jobUrl", ""), apply_url=item.get("applyUrl", ""), published_at=item.get("publishedAt", ""),
            ))
    else:
        raise ValueError(f"unsupported job provider: {provider}")
    return jobs


def fetch_board(provider: str, employer: str, token: str) -> list[dict[str, Any]]:
    if provider not in PROVIDERS:
        raise ValueError(f"unsupported job provider: {provider}")
    return parse_board_payload(provider, _clean(employer), token, _json_get(board_url(provider, token)))


def normalize_manual_job(raw: Mapping[str, Any]) -> dict[str, Any]:
    source_url = _url(raw.get("source_url"))
    return _job(
        "manual", "", raw.get("employer", ""), sha256(source_url.encode()).hexdigest()[:24],
        title=raw.get("title", ""), location=raw.get("location", ""), description=raw.get("description", ""),
        workplace=raw.get("workplace_type", ""), employment=raw.get("employment_type", ""), source_url=source_url,
        apply_url=raw.get("apply_url", ""),
    )


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9+#.]{2,}", value.casefold()) if token not in STOPWORDS}


def _requirements(description: str) -> tuple[list[str], list[str]]:
    required: list[str] = []
    preferred: list[str] = []
    for part in re.split(r"[\r\n]+|(?<=[.!?])\s+", description):
        text = _clean(part)
        if not 8 <= len(text) <= 500:
            continue
        low = text.casefold()
        target = preferred if any(marker in low for marker in PREFERRED_MARKERS) else required if any(marker in low for marker in REQUIRED_MARKERS) else None
        if target is not None and text not in target:
            target.append(text)
    return required[:12], preferred[:8]


def _requirement_supported(requirement: str, fact_token_sets: list[set[str]]) -> bool:
    req = _tokens(requirement)
    if not req:
        return False
    threshold = 1 if len(req) <= 2 else max(2, (len(req) + 1) // 2)
    return any(len(req & fact) >= threshold for fact in fact_token_sets)


def _explicit_min_years(description: str) -> int | None:
    found: list[int] = []
    low = description.casefold()
    for match in YEARS_RE.finditer(low):
        context = low[max(0, match.start() - 60):match.end() + 60]
        if any(marker in context for marker in PREFERRED_MARKERS):
            continue
        if any(marker in context for marker in ("experience", "required", "minimum", "at least")):
            found.append(int(match.group(1)))
    return max(found) if found else None


def assess_job(job: Mapping[str, Any], targeting: TargetingSettings, approved_facts: list[Mapping[str, Any]]) -> dict[str, Any]:
    hard: list[str] = []
    review: list[str] = []
    title_key = _key(job.get("title"))
    description = str(job.get("description") or "")
    location_key = _key(job.get("location"))
    workplace = _key(job.get("workplace_type"))
    employment = _key(job.get("employment_type"))

    if any(_employer_key(job.get("employer")) == _employer_key(name) for name in targeting.excluded_employers):
        hard.append("employer is excluded by targeting settings")

    role_matches = [role for role in targeting.roles if _key(role) in title_key]
    if not role_matches:
        hard.append("title does not match a configured target role")

    if employment and employment != "permanent full time":
        hard.append(f"employment type is {job.get('employment_type')}, not permanent full-time")
    elif not employment:
        review.append("employment type is not explicit")

    minimum_years = _explicit_min_years(description)
    if minimum_years is not None and minimum_years > targeting.target_experience_max_years:
        hard.append(f"explicit minimum experience is {minimum_years} years, above configured target")

    combined = f"{location_key} {_key(description[:5000])}"
    if workplace == "remote":
        if targeting.remote_must_allow_origin:
            origin_ok = _key(targeting.remote_origin_city) in combined or _key(targeting.remote_origin_country) in combined
            if any(term in combined for term in REMOTE_RESTRICTED):
                hard.append("remote role explicitly restricts work to the United States")
            elif not origin_ok:
                review.append("remote role does not explicitly permit the configured India origin")
    elif not location_key or location_key == "unknown":
        review.append("work location is unknown")
    elif "india" in location_key or any(_key(city) in location_key for city in targeting.india_office_cities):
        if not any(_key(city) in location_key for city in targeting.india_office_cities):
            hard.append("India office/hybrid location is outside configured cities")
    else:
        if not targeting.relocation_outside_india:
            hard.append("outside-India office/hybrid role requires relocation but relocation is disabled")
        elif targeting.require_overseas_sponsorship:
            if any(term in combined for term in NO_SPONSORSHIP):
                hard.append("role explicitly says visa sponsorship is unavailable")
            elif not any(term in combined for term in YES_SPONSORSHIP):
                review.append("overseas sponsorship requirement is not explicit")

    required, preferred = _requirements(description)
    fact_token_sets = [_tokens(str(fact.get("value_text") or fact.get("value") or "")) for fact in approved_facts]
    matched_required = [item for item in required if _requirement_supported(item, fact_token_sets)]
    matched_preferred = [item for item in preferred if _requirement_supported(item, fact_token_sets)]
    job_tokens = _tokens(description)
    fact_tokens = set().union(*fact_token_sets) if fact_token_sets else set()
    supported_terms = sorted(job_tokens & fact_tokens)[:20]

    role_score = 40 if role_matches else 0
    if required:
        evidence_score = round(35 * len(matched_required) / len(required))
    else:
        evidence_score = min(35, len(supported_terms) * 5)
    preferred_score = round(10 * len(matched_preferred) / len(preferred)) if preferred else 0
    clarity_score = 15 if not hard and not review else 5 if not hard else 0
    status = "ineligible" if hard else "review" if review else "eligible"
    return {
        **dict(job),
        "eligibility": status,
        "hard_reasons": hard,
        "review_reasons": review,
        "required_requirements": required,
        "preferred_requirements": preferred,
        "matched_required": matched_required,
        "matched_preferred": matched_preferred,
        "supported_terms": supported_terms,
        "score": role_score + evidence_score + preferred_score + clarity_score,
        "score_reasons": {
            "role": role_score,
            "required_evidence": evidence_score,
            "preferred_evidence": preferred_score,
            "eligibility_clarity": clarity_score,
        },
    }


def dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_content: set[str] = set()
    result: list[dict[str, Any]] = []
    for job in jobs:
        identity = f"{job.get('provider')}|{job.get('board_token')}|{job.get('source_job_id')}"
        content = sha256("|".join(_key(job.get(key)) for key in ("employer", "title", "location", "description")).encode()).hexdigest()
        if identity in seen_ids or content in seen_content:
            continue
        seen_ids.add(identity)
        seen_content.add(content)
        result.append(job)
    return result


class JobStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def boards(self) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute("SELECT * FROM job_boards ORDER BY user_added, employer, provider").fetchall()
        return [dict(row) for row in rows]

    def add_board(self, provider: str, employer: str, token: str, *, verification_source: str, user_added: bool = True) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise ValueError(f"unsupported job provider: {provider}")
        token = _board_token(token)
        employer = _clean(employer)
        if not employer:
            raise ValueError("employer name is required")
        if len(employer) > 200:
            raise ValueError("employer name exceeds 200 characters")
        board_id = f"{provider}:{token.casefold()}"
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO job_boards(id, provider, employer, board_token, enabled, user_added, verification_source, verified_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(provider, board_token) DO UPDATE SET
                    employer=excluded.employer, enabled=1, verification_source=excluded.verification_source,
                    verified_at=excluded.verified_at
                """,
                (board_id, provider, employer, token, int(user_added), verification_source, now),
            )
        return next(row for row in self.boards() if row["id"] == board_id)

    def set_board_enabled(self, board_id: str, enabled: bool) -> None:
        with self.database.transaction() as connection:
            if connection.execute("UPDATE job_boards SET enabled=? WHERE id=?", (int(enabled), board_id)).rowcount != 1:
                raise KeyError(board_id)

    def mark_checked(self, board_id: str, error: str | None = None) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE job_boards SET last_checked_at=?, last_error=? WHERE id=?",
                (utc_now_text(), error, board_id),
            )

    def _upsert_on(self, connection: Any, job: Mapping[str, Any], board_id: str | None, now: str) -> None:
        identity = f"{job['provider']}|{job.get('board_token', '')}|{job['source_job_id']}"
        job_id = sha256(identity.encode()).hexdigest()
        content_sha = sha256("|".join(_key(job.get(key)) for key in ("employer", "title", "location", "description")).encode()).hexdigest()
        connection.execute(
            """
            INSERT INTO discovered_jobs(
                id, provider, board_id, board_token, source_job_id, employer, title, location,
                workplace_type, employment_type, source_url, apply_url, description, published_at,
                active, first_seen_at, last_seen_at, content_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                employer=excluded.employer, title=excluded.title, location=excluded.location,
                workplace_type=excluded.workplace_type, employment_type=excluded.employment_type,
                source_url=excluded.source_url, apply_url=excluded.apply_url, description=excluded.description,
                published_at=excluded.published_at, active=1, last_seen_at=excluded.last_seen_at,
                content_sha256=excluded.content_sha256
            """,
            (
                job_id, job["provider"], board_id, job.get("board_token", ""), job["source_job_id"],
                job["employer"], job["title"], job["location"], job.get("workplace_type"),
                job.get("employment_type"), job["source_url"], job.get("apply_url"), job["description"],
                job.get("published_at"), now, now, content_sha,
            ),
        )

    def upsert(self, job: Mapping[str, Any], board_id: str | None = None) -> None:
        with self.database.transaction() as connection:
            self._upsert_on(connection, job, board_id, utc_now_text())

    def replace_board_jobs(self, board_id: str, jobs: list[Mapping[str, Any]]) -> None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            connection.execute("UPDATE discovered_jobs SET active=0 WHERE board_id=?", (board_id,))
            for job in jobs:
                self._upsert_on(connection, job, board_id, now)

    def jobs(self, limit: int = 500) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT * FROM discovered_jobs WHERE active=1 ORDER BY last_seen_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
