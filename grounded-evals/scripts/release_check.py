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


ROUTES = ["/", "/demos", "/coach", "/eval", "/coding", "/analysis", "/judge", "/report", "/health"]
CONTENT_CHECKS = {
    "/": [
        "Annotation is the product",
        "Build the review interface",
        "Purpose-built annotation",
        "AdTech",
        "What the domain expert discovers",
    ],
    "/demos": ["RxBot", "MigrateBot", "EnergyBot", "BudgetAir"],
    "/coding": ["Annotation Workbench", "domain language", "severity", "confidence", "memo", "judge"],
    "/judge": ["rubric", "Generate"],
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def fetch(url: str, timeout: float = 20.0) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "gedd-release-check/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(response.status)
        content_type = response.headers.get("content-type", "")
        body = response.read()
    return status, content_type, body


def check_routes(base_url: str, expect_auth: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    for route in ROUTES:
        url = f"{base_url}{route}"
        try:
            status, content_type, body = fetch(url)
        except urllib.error.URLError as exc:
            results.append(CheckResult(f"route {route}", False, str(exc)))
            continue
        if expect_auth and route != "/health":
            ok = status == 200 and b"Sign in" in body
        else:
            ok = status == 200 and (route != "/health" or b'"status":"ok"' in body)
        results.append(
            CheckResult(
                f"route {route}",
                ok,
                f"{status} {content_type} {len(body)} bytes",
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
            ("/", "Annotation is the product"),
            ("/demos", "Domain Specialists"),
            ("/coding", "Annotation Workbench"),
            ("/judge", "Generate"),
            ("/report", "Handoff"),
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
