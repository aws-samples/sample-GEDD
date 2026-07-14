#!/usr/bin/env python3
"""Release smoke test for the public GEDD web app.

Checks the public CloudFront routes, product-critical page content, and, when
Playwright is installed, performs a real browser render pass.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROUTES = [
    "/",
    "/demos",
    "/gdpr-demo",
    "/mass-effect-localization-demo",
    "/coach",
    "/eval",
    "/coding",
    "/analysis",
    "/requirements",
    "/judge",
    "/report",
    "/improvement",
    "/health",
]
CONTENT_CHECKS = {
    "/": [
        "GEDD Coach",
        "Open Coach",
        "SME_error_analysis.md",
    ],
    "/demos": [
        "Demos for requirements.md and LLM Judge",
        "Load a 50-query annotation demo",
        "scenarios",
    ],
    "/gdpr-demo": [
        "AWS GDPR assistant to specs and judge",
        "GDPR Compliance Specialist Assistant",
        "requirements.md",
        "LLM Judge",
    ],
    "/mass-effect-localization-demo": [
        "Mass Effect localization assistant to specs and judge",
        "Mass Effect Localization Specialist",
        "requirements.md",
        "LLM Judge",
    ],
    "/coach": [
        "Curate evidence for Kiro specs",
        "Coach workbench",
        "Start with your domain expertise",
    ],
    "/coding": [
        "No baseline responses yet",
        "Open Coach",
        "requirements.md",
    ],
    "/requirements": [
        "requirements.md built from SME evidence",
        "No requirements evidence yet",
        "Open Coach",
    ],
    "/judge": ["Create the LLM Judge", "Open Annotations", "Coach"],
    "/report": ["Evidence handoff is not ready", "SME_error_analysis.md", "Build a judge first"],
    "/improvement": ["requirements.md quality uplift", "No measurement evidence yet", "Open Coach"],
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def fetch(url: str, timeout: float = 20.0) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "gedd-release-check/1.0"})
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        status = int(response.status)
        content_type = response.headers.get("content-type", "")
        body = response.read()
    return status, content_type, body


def fetch_no_redirect(url: str, timeout: float = 20.0) -> tuple[int, str, bytes, str]:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(url, headers={"User-Agent": "gedd-release-check/1.0"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(response.status)
            content_type = response.headers.get("content-type", "")
            body = response.read()
            location = response.headers.get("location", "")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        content_type = exc.headers.get("content-type", "")
        body = exc.read()
        location = exc.headers.get("location", "")
    return status, content_type, body, location


def check_routes(base_url: str, expect_auth: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    for route in ROUTES:
        url = f"{base_url}{route}"
        try:
            if expect_auth and route != "/health":
                status, content_type, body, location = fetch_no_redirect(url)
            else:
                status, content_type, body = fetch(url)
                location = ""
        except urllib.error.URLError as exc:
            results.append(CheckResult(f"route {route}", False, str(exc)))
            continue
        if expect_auth and route != "/health":
            ok = status in (302, 303, 307, 308) and "amazoncognito.com/login" in location
        else:
            ok = status == 200 and (route != "/health" or b'"status":"ok"' in body)
        results.append(
            CheckResult(
                f"route {route}",
                ok,
                f"{status} {content_type} {len(body)} bytes" + (f" -> {location}" if location else ""),
            )
        )
    return results


def check_content(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    for route, needles in CONTENT_CHECKS.items():
        try:
            status, _, body = fetch(f"{base_url}{route}")
        except urllib.error.URLError as exc:
            results.append(CheckResult(f"content {route}", False, str(exc)))
            continue
        text = body.decode("utf-8", errors="replace")
        missing = [needle for needle in needles if needle not in text]
        results.append(
            CheckResult(
                f"content {route}",
                status == 200 and not missing,
                "ok" if not missing else f"missing: {', '.join(missing)}",
            )
        )
    return results


async def check_browser(base_url: str, screenshot_dir: Path) -> list[CheckResult]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return [
            CheckResult(
                "browser",
                False,
                "Playwright is not installed; run `python -m pip install -e '.[dev]' && python -m playwright install chromium`.",
            )
        ]

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    results: list[CheckResult] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        for route, selector_text in [
            ("/", "Open Coach"),
            ("/demos", "Demos for requirements.md and LLM Judge"),
            ("/gdpr-demo", "AWS GDPR assistant to specs and judge"),
            ("/mass-effect-localization-demo", "Mass Effect localization assistant to specs and judge"),
            ("/coach", "Coach workbench"),
            ("/coding", "No baseline responses yet"),
            ("/requirements", "No requirements evidence yet"),
            ("/judge", "Create the LLM Judge"),
            ("/report", "Evidence handoff is not ready"),
            ("/improvement", "No measurement evidence yet"),
        ]:
            try:
                response = await page.goto(f"{base_url}{route}", wait_until="networkidle", timeout=30000)
                content = await page.content()
                await page.screenshot(path=screenshot_dir / f"{route.strip('/') or 'home'}.png", full_page=True)
                status = response.status if response else 0
                ok = status == 200 and selector_text in content
                results.append(CheckResult(f"browser {route}", ok, f"{status}; contains {selector_text!r}={selector_text in content}"))
            except Exception as exc:
                results.append(CheckResult(f"browser {route}", False, str(exc)))
        await browser.close()
    return results


def print_results(results: list[CheckResult]) -> None:
    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"{marker} {result.name}: {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run release checks against a deployed GEDD app.")
    parser.add_argument("--base-url", default="https://d2esgpsbblnxif.cloudfront.net")
    parser.add_argument("--browser", action="store_true", help="Run Playwright browser checks.")
    parser.add_argument("--expect-auth", action="store_true", help="Expect protected app routes to redirect to login.")
    parser.add_argument("--screenshot-dir", default="/tmp/gedd-release-screenshots")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = check_routes(base_url, expect_auth=args.expect_auth)
    if not args.expect_auth:
        results += check_content(base_url)
    if args.browser:
        results.extend(asyncio.run(check_browser(base_url, Path(args.screenshot_dir))))
    print_results(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
