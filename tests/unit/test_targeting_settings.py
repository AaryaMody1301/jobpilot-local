import pytest

from jobpilot.settings.targeting import InvalidTargetingSettings, TargetingSettings


def test_default_targeting_matches_agreed_phase1_preferences() -> None:
    settings = TargetingSettings()
    assert settings.roles == ("data analyst", "data engineer", "analytics engineer")
    assert settings.target_experience_min_years == 2
    assert settings.target_experience_max_years == 5
    assert settings.india_office_cities == ("Surat",)
    assert settings.remote_origin_city == "Surat"
    assert settings.remote_origin_country == "India"
    assert settings.remote_must_allow_origin is True
    assert settings.salary_minimum is None
    assert settings.require_overseas_sponsorship is True
    assert settings.notice_period_days == 30
    assert settings.employment_types == ("permanent_full_time",)
    assert settings.excluded_employers == ("Brentwood Industries",)


def test_round_trip_normalizes_editable_values() -> None:
    raw = TargetingSettings().to_dict()
    raw["roles"] = [" data analyst ", "data analyst", "data engineer"]
    raw["notice_period_days"] = 45
    parsed = TargetingSettings.from_mapping(raw)
    assert parsed.roles == ("data analyst", "data engineer")
    assert parsed.notice_period_days == 45


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("roles", []),
        ("target_experience_min_years", -1),
        ("target_experience_max_years", 1),
        ("notice_period_days", -1),
        ("remote_origin_city", ""),
        ("remote_must_allow_origin", "yes"),
        ("salary_minimum", -1),
        ("require_overseas_sponsorship", "yes"),
    ],
)
def test_invalid_targeting_is_rejected(field: str, value: object) -> None:
    raw = TargetingSettings().to_dict()
    raw[field] = value
    with pytest.raises(InvalidTargetingSettings):
        TargetingSettings.from_mapping(raw)
