from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from jobpilot.applications.adapter import FormField, FormInspection, SubmissionConfirmation

_SUPPORTED_INPUTS = {"text", "email", "tel", "url", "number", "date", "file", "checkbox", "radio"}
_CONFIRMATION_JS = """() => /thank you for applying|application (?:was )?submitted|application received/i.test(document.body.innerText || '') || !!document.querySelector('[data-jobpilot-confirmation=\"success\"]')"""


def _loopback(host: str | None) -> bool:
    if not host:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _url(value: object) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    if not 1 <= len(text) <= 2000 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("application URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("application URL cannot contain credentials")
    return text


def _label(locator: Any) -> str:
    return " ".join(str(locator.evaluate("""el => {
        if (el.labels && el.labels.length) return Array.from(el.labels).map(x => x.innerText || x.textContent || '').join(' ');
        const parent = el.closest('label');
        return (parent && (parent.innerText || parent.textContent)) || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || el.id || '';
    }""") or "").split())[:300]


def _visible(locator: Any) -> bool:
    try:
        return locator.is_visible()
    except Exception:
        return False


class HostedApplicationAdapter:
    provider = ""
    hosts: tuple[str, ...] = ()

    def __init__(self, page: Any, *, allow_controlled_submit: bool = False) -> None:
        self.page = page
        self.allow_controlled_submit = allow_controlled_submit
        self._frame: Any = None
        self._fields: dict[str, Any] = {}
        self._field_types: dict[str, str] = {}
        self._required: set[str] = set()
        self._submit: Any = None

    def _validate_target(self, value: object) -> str:
        url = _url(value)
        host = urlparse(url).hostname or ""
        if self.allow_controlled_submit:
            if not _loopback(host):
                raise ValueError("controlled adapter submission permits loopback targets only")
        elif host.casefold() not in self.hosts:
            raise ValueError(f"{self.provider} adapter does not recognize host {host!r}")
        return url

    def _validate_landed_url(self) -> None:
        host = urlparse(str(self.page.url)).hostname or ""
        if self.allow_controlled_submit:
            if not _loopback(host):
                raise RuntimeError("controlled form redirected outside loopback before submit")
        elif host.casefold() not in self.hosts:
            raise RuntimeError(f"{self.provider} form redirected to unsupported host {host!r}")

    def inspect(self, url: str) -> FormInspection:
        target = self._validate_target(url)
        self.page.goto(target, wait_until="domcontentloaded", timeout=15_000)
        try:
            self.page.wait_for_load_state("networkidle", timeout=3_000)
        except Exception:
            pass
        self._validate_landed_url()

        frame = self._find_application_frame()
        if frame is None:
            self._reset()
            return FormInspection(False, (), ("application_form_not_found",), 0)

        self._frame = frame
        blockers = self._blockers(frame)
        self._fields.clear(); self._field_types.clear(); self._required.clear()
        fields: list[FormField] = []
        seen: set[str] = set()
        controls = frame.locator("input, textarea, select")
        for index in range(controls.count()):
            control = controls.nth(index)
            if not _visible(control):
                continue
            tag = str(control.evaluate("el => el.tagName.toLowerCase()"))
            input_type = str(control.get_attribute("type") or "text").casefold()
            if tag == "input" and input_type in {"hidden", "submit", "button", "reset", "image"}:
                continue
            kind = "select" if tag == "select" else "textarea" if tag == "textarea" else input_type
            name = str(control.get_attribute("name") or control.get_attribute("id") or "").strip() or f"field_{index}"
            if name in seen:
                continue
            seen.add(name)
            label = _label(control) or name
            required = (
                control.get_attribute("required") is not None
                or str(control.get_attribute("aria-required") or "").casefold() == "true"
                or bool(re.search(r"(?:\*|✱)\s*$", label))
            )
            supported = tag in {"select", "textarea"} or (tag == "input" and input_type in _SUPPORTED_INPUTS)
            if required and not supported:
                blockers.append(f"unsupported_required_field:{kind}")
            fields.append(FormField(name=name, field_type=kind, required=required, label=label))
            if supported:
                self._fields[name] = control
                self._field_types[name] = kind
                if required:
                    self._required.add(name)

        submits = self._submit_controls(frame)
        self._submit = submits[0] if len(submits) == 1 else None
        if len(submits) != 1:
            blockers.append("submit_control_count")
        if not fields:
            blockers.append("application_fields_not_found")
        return FormInspection(not blockers, tuple(fields), tuple(dict.fromkeys(blockers)), len(submits))

    def check_support(self, inspection: FormInspection) -> bool:
        return inspection.supported

    def fill(self, answers: dict[str, str]) -> None:
        self._require_controlled_write()
        missing = sorted(name for name in self._required if not str(answers.get(name, "")).strip())
        if missing:
            raise ValueError(f"missing required approved answers: {', '.join(missing)}")
        for name, answer in answers.items():
            locator = self._fields.get(name)
            if locator is not None:
                self._fill_control(name, locator, self._field_types[name], str(answer))

    def submit(self) -> None:
        self._require_controlled_write()
        if self._submit is None:
            raise RuntimeError("supported submit control is not available")
        self._submit.click(timeout=5_000)

    def confirm(self) -> SubmissionConfirmation:
        try:
            self.page.wait_for_function(_CONFIRMATION_JS, timeout=3_000)
        except Exception:
            return SubmissionConfirmation(False, None)
        text = " ".join(self.page.locator("body").inner_text().split())[:500]
        return SubmissionConfirmation(True, text or "explicit success marker")

    def _reset(self) -> None:
        self._frame = None; self._fields.clear(); self._field_types.clear(); self._required.clear(); self._submit = None

    def _find_application_frame(self) -> Any | None:
        for frame in self.page.frames:
            if self._submit_controls(frame) and frame.locator("input, textarea, select").count():
                return frame
        return None

    @staticmethod
    def _submit_controls(frame: Any) -> list[Any]:
        matches: list[Any] = []
        buttons = frame.locator('button, input[type="submit"]')
        for index in range(buttons.count()):
            button = buttons.nth(index)
            if not _visible(button):
                continue
            tag = str(button.evaluate("el => el.tagName.toLowerCase()"))
            text = " ".join(str(button.inner_text() if tag == "button" else button.get_attribute("value") or "").split()).casefold()
            if "submit" in text and ("application" in text or text == "submit"):
                matches.append(button)
        return matches

    @staticmethod
    def _blockers(frame: Any) -> list[str]:
        selectors = {
            "captcha": '[id*="captcha" i], [class*="captcha" i], iframe[src*="captcha" i], iframe[src*="recaptcha" i], iframe[src*="hcaptcha" i]',
            "login_or_verification": 'input[type="password"], input[autocomplete="one-time-code"]',
            "payment": 'input[autocomplete="cc-number"], input[name*="card" i], input[name*="payment" i]',
        }
        blockers = [name for name, selector in selectors.items() if frame.locator(selector).count()]
        if frame.get_by_role("button", name=re.compile(r".*(?:assessment|test).*", re.I)).count():
            blockers.append("assessment")
        return blockers

    def _require_controlled_write(self) -> None:
        if not self.allow_controlled_submit or not _loopback(urlparse(str(self.page.url)).hostname):
            raise RuntimeError("adapter writes are disabled for live employer pages")

    def _fill_control(self, name: str, locator: Any, kind: str, answer: str) -> None:
        if kind == "file":
            locator.set_input_files(answer)
        elif kind == "select":
            try:
                locator.select_option(value=answer)
            except Exception:
                locator.select_option(label=answer)
        elif kind == "checkbox":
            if answer.strip().casefold() in {"yes", "true", "1", "on"}:
                locator.check()
            elif answer.strip().casefold() in {"no", "false", "0", "off"}:
                locator.uncheck()
            else:
                raise ValueError(f"invalid checkbox answer for {name}")
        elif kind == "radio":
            assert self._frame is not None
            radios = self._frame.locator('input[type="radio"]')
            chosen = None
            for index in range(radios.count()):
                radio = radios.nth(index)
                if radio.get_attribute("name") == name and str(radio.get_attribute("value") or "") == answer:
                    chosen = radio; break
            if chosen is None:
                raise ValueError(f"radio answer does not match an available value for {name}")
            chosen.check()
        else:
            locator.fill(answer)
        if kind != "file" and not bool(locator.evaluate("el => el.checkValidity()")):
            raise ValueError(f"approved answer is invalid for {name}")


class GreenhouseAdapter(HostedApplicationAdapter):
    provider = "greenhouse"
    hosts = ("job-boards.greenhouse.io", "boards.greenhouse.io")


class LeverAdapter(HostedApplicationAdapter):
    provider = "lever"
    hosts = ("jobs.lever.co", "jobs.eu.lever.co")
