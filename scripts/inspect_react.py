"""Isolated browser acceptance checks for the local React product."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    output = Path("artifacts/react-ui")
    output.mkdir(parents=True, exist_ok=True)
    screenshots, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        def visit(path):
            page.goto(args.base_url + path)
            expect(page.get_by_role("heading", level=1)).to_be_visible()
            page.evaluate("document.fonts.ready")
            expect(page.get_by_text("Runs locally", exact=True)).to_be_visible()

        def shot(name):
            page.wait_for_timeout(350)
            if not page.get_by_role("dialog").count():
                page.get_by_role("heading", level=1).click()
            page.evaluate("window.scrollTo(0, 0)")
            expected_width = page.viewport_size["width"]
            page.screenshot(
                path=str(output / f"{name}.png"), full_page=True, animations="disabled"
            )
            screenshots.append(name + ".png")
            overflow = page.evaluate("""() => ({
                width: innerWidth, body: document.documentElement.scrollWidth,
                offenders: [...document.querySelectorAll('main *')].filter(e => {
                  const r=e.getBoundingClientRect(); return r.width && r.right > innerWidth + 2;
                }).slice(0,8).map(e=>({tag:e.tagName, cls:e.className?.baseVal ?? e.className, width:e.getBoundingClientRect().width}))
            })""")
            assert overflow["body"] <= expected_width + 1, (
                name,
                expected_width,
                overflow,
            )
            assert not errors, errors

        def verify_dfa():
            page.get_by_role("button", name="Build & verify", exact=True).click()
            expect(page.get_by_text("Verified language", exact=True)).to_be_visible(
                timeout=60000
            )

        def parse_cfg():
            page.get_by_role("button", name="Parse & verify", exact=True).click()
            expect(page.get_by_text("Verified derivation", exact=True)).to_be_visible(
                timeout=30000
            )

        try:
            visit("/")
            expect(page.locator(".landing-example")).to_have_count(6)
            shot("overview-desktop")
            page.get_by_role("button", name="Pause showcase animation", exact=True).click()
            expect(page.get_by_role("button", name="Play showcase animation", exact=True)).to_be_visible()
            page.get_by_role("button", name="GRAMMARS", exact=True).first.click()
            expect(page.get_by_role("heading", level=1)).to_contain_text("parse trees.")
            page.get_by_role("button", name="Start exploring", exact=True).click()
            expect(page.get_by_label("Input tokens", exact=True)).to_have_value("id + id * id")
            visit("/")
            page.get_by_label("Search worked examples", exact=True).fill("Arithmetic")
            expect(page.locator(".landing-example")).to_have_count(1)
            page.get_by_role("group", name="Example category").get_by_role("button", name="Finite automata", exact=True).click()
            expect(page.get_by_text("No examples match that search.", exact=True)).to_be_visible()
            page.get_by_role("button", name="Show all examples", exact=False).click()
            expect(page.locator(".landing-example")).to_have_count(6)
            page.get_by_label("Sort examples", exact=True).select_option("name")
            expect(page.locator(".landing-example h3").first).to_have_text("Ambiguous expression")
            page.locator(".landing-popular").get_by_role("button", name="Arithmetic", exact=True).click()
            expect(page.locator(".landing-example")).to_have_count(1)
            page.get_by_role("button", name="Explore Arithmetic", exact=True).click()
            expect(page.get_by_label("Input tokens", exact=True)).to_have_value("id + id * id")
            visit("/dfa")
            shot("dfa-ready-desktop")
            verify_dfa()
            page.get_by_role("button", name="Step forward", exact=True).click()
            expect(page.get_by_role("slider", name="Execution step")).to_have_value("1")
            page.get_by_role("slider", name="Execution step").focus()
            page.get_by_role("slider", name="Execution step").press("End")
            expect(page.get_by_text("ACCEPT", exact=True)).to_be_visible()
            shot("dfa-verified-desktop")
            page.get_by_role("button", name="Zoom in", exact=True).click()
            expect(page.get_by_text("125%", exact=True)).to_be_visible()
            page.get_by_role("button", name="Reset diagram view", exact=True).click()
            page.get_by_role("button", name="Expand diagram", exact=True).click()
            expect(page.get_by_role("dialog", name="Expanded diagram")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog", name="Expanded diagram")).to_have_count(0)
            page.get_by_role("tab", name="Transition table", exact=True).click()
            expect(page.get_by_role("table")).to_be_visible()
            page.get_by_role("tab", name="Transition table", exact=True).press(
                "ArrowRight"
            )
            expect(
                page.get_by_role("tab", name="Execution trace", exact=True)
            ).to_have_attribute("aria-selected", "true")
            page.get_by_role("button", name="Export animation", exact=True).click()
            expect(
                page.get_by_role("dialog", name="Your theory, in motion.")
            ).to_be_visible(timeout=90000)
            expect(page.locator("video")).to_have_js_property(
                "readyState", 4, timeout=30000
            )
            assert (
                page.get_by_role("link", name="Download MP4", exact=True)
                .get_attribute("href")
                .startswith("/api/videos/")
            )
            shot("video-export-desktop")
            page.get_by_role("button", name="Close dialog", exact=True).click()
            page.get_by_label("Test string", exact=False).fill("00")
            expect(
                page.get_by_text("A fresh input needs a fresh check.", exact=True)
            ).to_be_visible()
            expect(page.locator("video")).to_have_count(0)
            verify_dfa()
            page.get_by_role("slider", name="Execution step").focus()
            page.get_by_role("slider", name="Execution step").press("End")
            expect(page.get_by_text("REJECT", exact=True)).to_be_visible()
            shot("dfa-reject-desktop")
            page.get_by_label("Prediction source", exact=True).select_option(
                "incorrect"
            )
            page.get_by_role("button", name="Build & verify", exact=True).click()
            expect(page.get_by_text("Candidate rejected", exact=True)).to_be_visible()
            expect(
                page.get_by_role("button", name="Export animation", exact=True)
            ).to_be_disabled()
            expect(page.locator(".counterexample code")).to_have_text("ε")
            shot("dfa-counterexample-desktop")
            page.get_by_label("Prediction source", exact=True).select_option("learned")
            expect(
                page.get_by_role("button", name="Build & verify", exact=True)
            ).to_be_disabled()
            expect(
                page.get_by_text(
                    "Choose a checkpoint in workspace settings.", exact=True
                )
            ).to_be_visible()
            shot("dfa-missing-checkpoint")
            page.get_by_label("Prediction source", exact=True).select_option("rule")
            page.get_by_label("Language description", exact=False).fill(
                "Binary strings that contain 01."
            )
            page.get_by_role("button", name="Build & verify", exact=True).click()
            expect(page.get_by_text("Reference needed", exact=True)).to_be_visible()
            shot("dfa-missing-reference")
            page.get_by_role("button", name="Configure", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.get_by_role("button", name="Presentation", exact=False).click()
            page.get_by_role("button", name="Done", exact=True).click()
            expect(page.get_by_text("Reference needed", exact=True)).to_be_visible()
            page.get_by_role("button", name="Configure", exact=True).click()
            page.get_by_role("button", name="Quick preview", exact=False).click()
            page.get_by_role("button", name="Done", exact=True).click()

            visit("/grammar")
            parse_cfg()
            page.get_by_role("slider", name="Execution step").focus()
            page.get_by_role("slider", name="Execution step").press("End")
            shot("grammar-verified-desktop")
            page.get_by_role("button", name="Ambiguous", exact=True).click()
            parse_cfg()
            expect(page.get_by_label("Verified parse tree", exact=True)).to_have_count(
                1
            )
            page.get_by_label("Verified parse tree", exact=True).select_option("1")
            page.get_by_role("slider", name="Execution step").focus()
            page.get_by_role("slider", name="Execution step").press("End")
            shot("grammar-ambiguous-desktop")
            page.get_by_role("link", name="DFA Studio STUDIO", exact=True).click()
            expect(page.get_by_text("Reference needed", exact=True)).to_be_visible()
            page.get_by_role("link", name="Grammar Lab", exact=True).click()
            expect(page.get_by_label("Verified parse tree", exact=True)).to_have_value(
                "1"
            )
            page.get_by_role("button", name="Balanced aⁿbⁿ", exact=True).click()
            page.get_by_label("Input tokens", exact=True).fill("")
            parse_cfg()
            shot("grammar-empty-input")

            visit("/examples")
            expect(page.locator(".example-card")).to_have_count(6)
            page.get_by_label("Search examples", exact=True).fill("Arithmetic")
            expect(page.locator(".example-card")).to_have_count(1)
            page.get_by_role("button", name="Open in Lab", exact=True).click()
            expect(page.get_by_label("Input tokens", exact=True)).to_have_value(
                "id + id * id"
            )
            parse_cfg()
            page.get_by_role("slider", name="Execution step").focus()
            page.get_by_role("slider", name="Execution step").press("End")
            page.set_viewport_size({"width": 390, "height": 844})
            shot("grammar-verified-mobile")
            page.get_by_role("button", name="Open navigation", exact=True).click()
            expect(
                page.get_by_role("link", name="Example Library", exact=True)
            ).to_be_visible()
            page.get_by_role("link", name="Example Library", exact=True).click()
            expect(page.get_by_label("Search examples", exact=True)).to_be_visible()
            shot("examples-mobile")
            visit("/research")
            expect(page.get_by_text("20%", exact=True).first).to_be_visible()
            shot("research-mobile")
            visit("/dfa")
            page.get_by_role("button", name="Ends in 01", exact=True).click()
            page.get_by_label("Prediction source", exact=True).select_option("demo")
            verify_dfa()
            shot("dfa-verified-mobile")
            page.get_by_role("button", name="Configure", exact=True).click()
            shot("settings-mobile")
            page.get_by_role("button", name="Done", exact=True).click()
            visit("/")
            shot("overview-mobile")
            page.get_by_role("button", name="Open menu", exact=True).click()
            expect(page.get_by_role("navigation", name="Mobile landing navigation")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("navigation", name="Mobile landing navigation")).to_have_count(0)
            page.set_viewport_size({"width": 320, "height": 844})
            shot("overview-small-mobile")
            page.set_viewport_size({"width": 768, "height": 1000})
            visit("/dfa")
            shot("dfa-tablet")
            page.set_viewport_size({"width": 1440, "height": 1000})
            visit("/research")
            shot("research-desktop")
            visit("/examples")
            shot("examples-desktop")
            (output / "browser-report.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "page_errors": errors,
                        "screenshots": screenshots,
                    },
                    indent=2,
                )
            )
            print(
                f"React browser checks passed; {len(screenshots)} screenshots captured; no page errors."
            )
        except Exception:
            page.screenshot(path=str(output / "failure.png"), full_page=True)
            (output / "failure.txt").write_text(page.locator("body").inner_text())
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
