from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


class InvalidTargetingSettings(ValueError):
    pass


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise InvalidTargetingSettings(f"{field} must contain at least one value")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InvalidTargetingSettings(f"{field} must contain non-empty strings")
        cleaned.append(item.strip())
    return tuple(dict.fromkeys(cleaned))


@dataclass(frozen=True, slots=True)
class TargetingSettings:
    roles: tuple[str, ...] = ("data analyst", "data engineer", "analytics engineer")
    target_experience_min_years: int = 2
    target_experience_max_years: int = 5
    india_office_cities: tuple[str, ...] = ("Surat",)
    remote_origin_city: str = "Surat"
    remote_origin_country: str = "India"
    remote_must_allow_origin: bool = True
    relocation_outside_india: bool = True
    require_overseas_sponsorship: bool = True
    salary_minimum: int | None = None
    notice_period_days: int = 30
    employment_types: tuple[str, ...] = ("permanent_full_time",)
    excluded_employers: tuple[str, ...] = ("Brentwood Industries",)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("roles", "india_office_cities", "employment_types", "excluded_employers"):
            value[key] = list(value[key])
        return value

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "TargetingSettings":
        allowed = {
            "roles",
            "target_experience_min_years",
            "target_experience_max_years",
            "india_office_cities",
            "remote_origin_city",
            "remote_origin_country",
            "remote_must_allow_origin",
            "relocation_outside_india",
            "require_overseas_sponsorship",
            "salary_minimum",
            "notice_period_days",
            "employment_types",
            "excluded_employers",
        }
        unexpected = set(raw) - allowed
        if unexpected:
            raise InvalidTargetingSettings(f"unexpected settings: {sorted(unexpected)}")

        default = cls()
        roles = _string_tuple(raw.get("roles", default.roles), "roles")
        cities = _string_tuple(raw.get("india_office_cities", default.india_office_cities), "india_office_cities")
        employment = _string_tuple(raw.get("employment_types", default.employment_types), "employment_types")
        excluded = _string_tuple(raw.get("excluded_employers", default.excluded_employers), "excluded_employers")

        minimum = raw.get("target_experience_min_years", default.target_experience_min_years)
        maximum = raw.get("target_experience_max_years", default.target_experience_max_years)
        notice = raw.get("notice_period_days", default.notice_period_days)
        salary = raw.get("salary_minimum", default.salary_minimum)
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
            raise InvalidTargetingSettings("target_experience_min_years must be a non-negative integer")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < minimum:
            raise InvalidTargetingSettings("target_experience_max_years must be an integer >= minimum")
        if not isinstance(notice, int) or isinstance(notice, bool) or notice < 0:
            raise InvalidTargetingSettings("notice_period_days must be a non-negative integer")
        if salary is not None and (not isinstance(salary, int) or isinstance(salary, bool) or salary < 0):
            raise InvalidTargetingSettings("salary_minimum must be null or a non-negative integer")

        city = raw.get("remote_origin_city", default.remote_origin_city)
        country = raw.get("remote_origin_country", default.remote_origin_country)
        if not isinstance(city, str) or not city.strip():
            raise InvalidTargetingSettings("remote_origin_city must be a non-empty string")
        if not isinstance(country, str) or not country.strip():
            raise InvalidTargetingSettings("remote_origin_country must be a non-empty string")

        remote_must_allow_origin = raw.get("remote_must_allow_origin", default.remote_must_allow_origin)
        relocation = raw.get("relocation_outside_india", default.relocation_outside_india)
        sponsorship = raw.get("require_overseas_sponsorship", default.require_overseas_sponsorship)
        if not isinstance(remote_must_allow_origin, bool):
            raise InvalidTargetingSettings("remote_must_allow_origin must be a boolean")
        if not isinstance(relocation, bool) or not isinstance(sponsorship, bool):
            raise InvalidTargetingSettings("relocation and sponsorship settings must be booleans")

        return cls(
            roles=roles,
            target_experience_min_years=minimum,
            target_experience_max_years=maximum,
            india_office_cities=cities,
            remote_origin_city=city.strip(),
            remote_origin_country=country.strip(),
            remote_must_allow_origin=remote_must_allow_origin,
            relocation_outside_india=relocation,
            require_overseas_sponsorship=sponsorship,
            salary_minimum=salary,
            notice_period_days=notice,
            employment_types=employment,
            excluded_employers=excluded,
        )
