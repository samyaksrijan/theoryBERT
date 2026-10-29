"""Browser checks for genuine learned and user-supplied DFA workflows."""

import json
import re
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

OUT = Path("artifacts/learned-ui")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    errors, shots = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501/dfa")
        expect(page.get_by_label("Prediction source", exact=True)).to_have_value("learned")
        build = page.get_by_role("button", name="Build & verify", exact=True)
        expect(build).to_be_enabled(timeout=15000)
        build.click()
        expect(page.get_by_text("Verified language", exact=True)).to_be_visible(timeout=60000)
        expect(page.locator(".source-line")).to_contain_text("google-bert/bert-base-uncased")

        def shot(name):
            page.get_by_role("heading", level=1).click()
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(OUT / name), full_page=True, animations="disabled")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert not errors, errors
            shots.append(name)

        shot("bert-verified-desktop.png")
        page.get_by_label("Language description", exact=False).fill("Please recognize binary strings ending with 10.")
        page.get_by_label("Test string", exact=False).fill("110")
        build.click()
        expect(page.locator(".source-line")).to_contain_text("google-bert/bert-base-uncased", timeout=60000)
        expect(page.locator(".graph-svg")).to_have_attribute("aria-label", re.compile("Structurally checked"))
        expect(page.get_by_role("button", name="Export animation", exact=True)).to_be_disabled()
        expect(page.get_by_role("slider", name="Execution step")).to_be_visible()
        shot("bert-custom-preview-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        shot("bert-custom-preview-mobile.png")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_label("Prediction source", exact=True).select_option("manual")
        machine = {"states": ["start", "accept", "island"], "alphabet": ["0", "1"], "transitions": {"start": {"0": "start", "1": "accept"}, "accept": {"0": "start", "1": "accept"}, "island": {"0": "island", "1": "island"}}, "start_state": "start", "accept_states": ["accept"]}
        page.get_by_label("Your DFA JSON", exact=True).fill(json.dumps(machine))
        page.get_by_label("Test string", exact=False).fill("101")
        build.click()
        expect(page.locator(".source-line")).to_contain_text("User-supplied DFA", timeout=15000)
        expect(page.locator(".graph-svg")).to_contain_text("island")
        slider = page.get_by_role("slider", name="Execution step")
        slider.focus()
        slider.press("End")
        expect(page.get_by_text("ACCEPT", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Export animation", exact=True)).to_be_disabled()
        shot("manual-dfa-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        shot("manual-dfa-mobile.png")
        browser.close()
    report = {"passed": True, "page_errors": errors, "screenshots": shots, "checks": ["real BERT default and source", "BERT verified example", "unverified model preview and playback", "video proof gate", "manual DFA names and unreachable states preserved", "desktop and mobile overflow"]}
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
