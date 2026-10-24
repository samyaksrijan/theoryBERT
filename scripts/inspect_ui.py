"""Repeatable browser QA. Start Streamlit locally before running this script."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path("artifacts/ui")
out.mkdir(parents=True, exist_ok=True)
screenshots = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1440, "height": 1100}, device_scale_factor=1
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:8501")
    page.get_by_text("Make the theory visible.").wait_for(timeout=30000)

    def shot(name):
        page.locator('[data-testid="stMain"]').evaluate("(el) => el.scrollTop=0")
        viewport = page.viewport_size
        height = page.locator('[data-testid="stMain"]').evaluate(
            "(el)=>el.scrollHeight"
        )
        page.set_viewport_size(
            {
                "width": viewport["width"],
                "height": max(viewport["height"], min(height + 70, 6000)),
            }
        )
        page.screenshot(path=str(out / (name + ".png")), full_page=True)
        screenshots.append(name + ".png")
        page.set_viewport_size(viewport)
        assert not page.locator('[data-testid="stException"]').count(), page.locator(
            "body"
        ).inner_text()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "Horizontal overflow in " + name
        assert page.locator('[data-testid="stMain"]').evaluate(
            "el => el.scrollWidth <= el.clientWidth"
        ), "Workspace overflow in " + name

    def source(value):
        page.get_by_label("Prediction source", exact=True).click()
        page.get_by_role("option", name=value, exact=True).click()

    def verify():
        page.get_by_role("button", name="Verify & prepare", exact=True).click()

    shot("desktop-empty")
    for width in (320, 768):
        page.set_viewport_size({"width": width, "height": 1000})
        shot(f"responsive-{width}-empty")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-empty")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_role("button", name="Ends in 01", exact=True).click()
    expect(page.get_by_label("Language description", exact=True)).to_have_value(
        "Binary strings that end in 01."
    )
    verify()
    page.get_by_text("✓ Verified DFA; test string accepted.", exact=True).wait_for(
        timeout=20000
    )
    shot("desktop-verified")
    slider = page.get_by_role("group", name="Execution step", exact=True).get_by_role(
        "slider"
    )
    slider.focus()
    slider.press("End")
    page.get_by_text("Read 1: q1 → q2.", exact=False).wait_for()
    shot("desktop-final-step")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-verified")
    page.locator('[data-testid="stImage"]').first.screenshot(
        path=str(out / "narrow-dfa-detail.png")
    )
    screenshots.append("narrow-dfa-detail.png")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_role("button", name="Render animation", exact=True).click()
    try:
        page.get_by_text(
            "Rendering · building your verified animation", exact=True
        ).wait_for(timeout=5000)
        page.screenshot(path=str(out / "desktop-rendering.png"), full_page=True)
        screenshots.append("desktop-rendering.png")
    except Exception:
        pass
    page.locator("video").wait_for(timeout=90000)
    shot("desktop-video")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-video")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_label("Test string", exact=True).fill("00")
    page.get_by_label("Test string", exact=True).press("Tab")
    page.get_by_text("Inputs changed · verify again", exact=True).wait_for()
    assert page.locator("video").count() == 0
    shot("desktop-stale")
    verify()
    page.get_by_text("✓ Verified DFA; test string rejected.", exact=True).wait_for()
    shot("desktop-rejected-string")
    source("Incorrect candidate fixture")
    verify()
    page.get_by_text("× Candidate rejected by verifier.", exact=True).wait_for()
    shot("desktop-failed")
    assert page.get_by_role("button", name="Render animation", exact=True).is_disabled()
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-failed")
    page.set_viewport_size({"width": 1440, "height": 1100})
    source("TheoryBERT checkpoint")
    page.get_by_text("No checkpoint found.", exact=False).wait_for()
    shot("desktop-missing-checkpoint")
    assert page.get_by_role("button", name="Predict & verify", exact=True).is_disabled()
    source("Rule-based baseline")
    page.get_by_label("Language description", exact=True).fill(
        "Binary strings that contain 01."
    )
    page.get_by_label("Language description", exact=True).press("Tab")
    page.get_by_role("button", name="Predict & verify", exact=True).click()
    page.get_by_text(
        "! Structure valid; semantic equivalence unverified.", exact=True
    ).wait_for()
    shot("desktop-missing-reference")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-missing-reference")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_text("CFG / Parse tree", exact=True).click()
    page.get_by_role("button", name="Arithmetic", exact=True).click()
    expect(page.get_by_label("Input tokens", exact=True)).to_have_value("id + id * id")
    page.get_by_role("button", name="Parse & verify", exact=True).click()
    page.get_by_text("✓ Verified parse tree", exact=True).wait_for(timeout=30000)
    shot("desktop-cfg")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-cfg")
    page.locator('[data-testid="stImage"]').first.screenshot(
        path=str(out / "narrow-cfg-detail.png")
    )
    screenshots.append("narrow-cfg-detail.png")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_role("button", name="Render animation", exact=True).click()
    page.locator("video").wait_for(timeout=90000)
    shot("desktop-cfg-video")
    page.get_by_role("button", name="Ambiguous expression", exact=True).click()
    expect(page.get_by_label("Input tokens", exact=True)).to_have_value("id + id + id")
    page.get_by_role("button", name="Parse & verify", exact=True).click()
    page.get_by_text("2 trees found.", exact=False).wait_for(timeout=30000)
    shot("desktop-ambiguous")
    page.get_by_label("Input tokens", exact=True).fill("id +")
    page.get_by_label("Input tokens", exact=True).press("Tab")
    page.get_by_role("button", name="Parse & verify", exact=True).click()
    page.get_by_text("Verification could not complete", exact=True).wait_for(
        timeout=20000
    )
    shot("desktop-cfg-error")
    (out / "browser-report.json").write_text(
        json.dumps(
            {
                "page_errors": errors,
                "screenshots": sorted(screenshots),
                "widths": [320, 390, 768, 1440],
                "status": "passed",
            },
            indent=2,
        )
    )
    assert not errors, errors
    print("Browser checks passed; screenshots captured:", len(screenshots))
    browser.close()
