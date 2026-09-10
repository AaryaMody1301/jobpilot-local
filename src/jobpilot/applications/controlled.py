from __future__ import annotations

from pathlib import Path

from jobpilot.applications.adapter import FormField, FormInspection


_BLOCKER_MARKERS = {
    "captcha": ("captcha", "recaptcha", "hcaptcha"),
    "assessment": ("assessment", "coding test", "take-home"),
    "login_or_verification": ("sign in", "log in", "verification code", "one-time password", "otp"),
    "payment": ("payment", "credit card", "debit card", "pay now"),
}


def inspect_controlled_form(page, fixture: Path) -> FormInspection:
    """Read-only form recognition. This function never clicks or fills controls."""
    page.goto(fixture.resolve().as_uri())
    body_text = page.locator("body").inner_text().lower()
    blockers: list[str] = []
    for blocker, markers in _BLOCKER_MARKERS.items():
        if any(marker in body_text for marker in markers):
            blockers.append(blocker)

    fields: list[FormField] = []
    controls = page.locator("input, textarea, select")
    for index in range(controls.count()):
        control = controls.nth(index)
        field_type = control.get_attribute("type") or control.evaluate("el => el.tagName.toLowerCase()")
        if field_type in {"submit", "button", "hidden", "reset", "image"}:
            continue
        name = control.get_attribute("name") or control.get_attribute("id") or f"field_{index}"
        required = control.get_attribute("required") is not None or control.get_attribute("aria-required") == "true"
        label = ""
        control_id = control.get_attribute("id")
        if control_id:
            label_locator = page.locator(f'label[for="{control_id}"]')
            if label_locator.count():
                label = label_locator.first.inner_text().strip()
        if not label:
            label = control.get_attribute("aria-label") or name
        fields.append(FormField(name=name, field_type=field_type, required=required, label=label))

    submit_controls = page.locator('button[type="submit"], input[type="submit"]').count()
    return FormInspection(supported=not blockers and submit_controls == 1, fields=tuple(fields), blockers=tuple(blockers), submit_controls=submit_controls)
