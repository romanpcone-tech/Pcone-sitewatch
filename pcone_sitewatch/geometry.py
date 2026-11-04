"""MOBILE_OVERFLOW. Without a browser the rule is skipped, never reported clean."""

from __future__ import annotations

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding


def browser_available() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


def skipped_finding(url: str, canon: dict) -> Finding:
    return Finding(
        rule_id="MOBILE_OVERFLOW",
        severity="info",
        url=url,
        target="390",
        action="skipped",
        evidence="no headless browser; MOBILE_OVERFLOW skipped, not clean",
    )


def is_clean(findings: list[Finding]) -> bool:
    """A skipped geometry check is not a clean result."""
    if any(item.rule_id == "MOBILE_OVERFLOW" and item.action == "skipped" for item in findings):
        return False
    return not any(item.action != "skipped" for item in findings)


def check(urls: list[str], canon: dict, available: bool | None = None) -> list[Finding]:
    present = browser_available() if available is None else available
    home = urls[0] if urls else canon.get("site", {}).get("base", "")
    if not present:
        return [skipped_finding(home, canon)]
    try:
        return _run_browser(urls, canon)
    except Exception as exc:
        finding = skipped_finding(home, canon)
        finding.evidence = f"browser failed ({type(exc).__name__}); MOBILE_OVERFLOW skipped, not clean"
        return [finding]


def _run_browser(urls: list[str], canon: dict) -> list[Finding]:
    from playwright.sync_api import sync_playwright

    found: list[Finding] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for url in urls:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                metrics = page.evaluate(
                    """() => {
                      const header = document.querySelector('#hdr, header');
                      const doc = document.documentElement;
                      return {
                        headerOverflow: !!(header && header.scrollWidth > header.clientWidth + 1),
                        pageOverflow: doc.scrollWidth > window.innerWidth + 1
                      };
                    }"""
                )
                page.close()
                if metrics.get("headerOverflow") or metrics.get("pageOverflow"):
                    found.append(
                        Finding(
                            rule_id="MOBILE_OVERFLOW",
                            severity=severity(canon, "header/menu overflow at 390px width"),
                            url=url,
                            target="390",
                            action="report_only",
                            evidence="horizontal overflow at 390px",
                        )
                    )
        finally:
            browser.close()
    return found
