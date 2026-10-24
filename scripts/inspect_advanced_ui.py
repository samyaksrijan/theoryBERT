"""Additional browser QA for checkpoint, reference, state and rendering boundaries."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path("artifacts/ui")
out.mkdir(parents=True, exist_ok=True)
screenshots = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:8501")
    page.get_by_text("Make the theory visible.").wait_for(timeout=30000)

    def shot(name):
        page.locator('[data-testid="stMain"]').evaluate("(el)=>el.scrollTop=0")
        viewport = page.viewport_size
        height = page.locator('[data-testid="stMain"]').evaluate(
            "(el)=>el.scrollHeight"
        )
        page.set_viewport_size(
            {
                "width": viewport["width"],
                "height": min(6000, max(viewport["height"], height + 30)),
            }
        )
        page.screenshot(path=str(out / (name + ".png")), full_page=True)
        screenshots.append(name + ".png")
        page.set_viewport_size(viewport)
        assert not page.locator('[data-testid="stException"]').count()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        assert page.locator('[data-testid="stMain"]').evaluate(
            "el => el.scrollWidth <= el.clientWidth"
        )

    def source(name):
        page.get_by_label("Prediction source", exact=True).click()
        page.get_by_role("option", name=name, exact=True).click()
        expect(page.get_by_label("Prediction source", exact=True)).to_have_value(name)

    def edit(label, value):
        page.get_by_label(label, exact=True).fill(value)
        page.get_by_label(label, exact=True).press("Tab")
        expect(page.get_by_label(label, exact=True)).to_have_value(value)

    page.get_by_role("button", name="Ends in 01", exact=True).click()
    expect(page.get_by_label("Test string", exact=True)).to_have_value("1101")
    source("TheoryBERT checkpoint")
    page.get_by_text("No checkpoint found.", exact=False).wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-missing-checkpoint")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_text(
        "Advanced settings · checkpoints, reference & rendering", exact=True
    ).click()
    edit("Local checkpoint directory", "artifacts/smoke/best")
    expect(
        page.get_by_role("button", name="Predict & verify", exact=True)
    ).to_be_enabled()
    page.get_by_role("button", name="Predict & verify", exact=True).click()
    page.get_by_text("× Candidate rejected by verifier.", exact=True).wait_for(
        timeout=60000
    )
    page.get_by_text("tiny-random-bert", exact=False).first.wait_for()
    shot("desktop-smoke-inference")
    assert page.get_by_role("button", name="Render animation", exact=True).is_disabled()
    source("Rule-based baseline")
    edit("Language description", "Binary strings that end in 01.")
    edit("Or paste reference DFA JSON", '{"states": []}')
    page.get_by_text("Invalid DFA fields:", exact=False).wait_for()
    expect(
        page.get_by_role("button", name="Predict & verify", exact=True)
    ).to_be_disabled()
    shot("desktop-invalid-reference")
    edit("Or paste reference DFA JSON", "")
    expect(page.get_by_text("Invalid DFA fields:", exact=False)).to_have_count(0)
    page.locator("input[type=file]").set_input_files(
        "data/examples/reference-suffix-01.json"
    )
    # The cleared editor rerun must finish before the uploader starts its rerun.
    page.get_by_text("Reference loaded.", exact=False).wait_for(timeout=30000)
    page.get_by_role("button", name="Predict & verify", exact=True).click()
    page.get_by_text("✓ Verified DFA; test string accepted.", exact=True).wait_for()
    shot("desktop-uploaded-reference")
    # Make a fresh uncached rendering request so progress is exercised, not merely a cache hit.
    edit("Test string", "1100110011001100110001")
    page.get_by_role("button", name="Predict & verify", exact=True).click()
    page.get_by_text("✓ Verified DFA; test string accepted.", exact=True).wait_for()
    from theorybert.data.generators import benchmark_examples
    from theorybert.pipeline import run_candidates
    from theorybert.rendering.renderer import payload_for, render_key

    e = benchmark_examples()[0]
    seal = run_candidates([e["dfa"]], e["dfa"], "QA").verified
    key = render_key(payload_for(seal, list("1100110011001100110001")))
    (Path("artifacts/videos") / (key + ".mp4")).unlink(missing_ok=True)
    page.get_by_role("button", name="Render animation", exact=True).click()
    page.get_by_text(
        "Rendering · building your verified animation", exact=True
    ).wait_for(timeout=10000)
    page.screenshot(path=str(out / "desktop-rendering-progress.png"), full_page=True)
    screenshots.append("desktop-rendering-progress.png")
    assert page.get_by_text(
        "3 · Rendering the checked execution trace", exact=False
    ).count()
    page.locator("video").wait_for(timeout=90000)
    expect(page.locator("video")).to_have_js_property("readyState", 4, timeout=30000)
    shot("desktop-long-video")
    # Switching away and back preserves both input and results.
    page.get_by_text("CFG / Parse tree", exact=True).click()
    page.get_by_role("button", name="Balanced a / b", exact=True).click()
    expect(page.get_by_label("Input tokens", exact=True)).to_have_value("a a b b")
    page.get_by_role("button", name="Parse & verify", exact=True).click()
    page.get_by_text("✓ Verified parse tree", exact=True).wait_for()
    page.get_by_text("TOC / DFA", exact=True).click()
    expect(page.get_by_label("Test string", exact=True)).to_have_value(
        "1100110011001100110001"
    )
    page.locator("video").wait_for(timeout=10000)
    # Changing only rendering quality keeps verification and exposes a fresh preview.
    quality_input = page.get_by_label("Video quality", exact=True)
    quality_input.focus()
    quality_input.press("ArrowDown")
    quality_input.press("ArrowDown")
    quality_input.press("Enter")
    expect(quality_input).to_have_value("High · 1080p / 60 fps")
    page.get_by_text("✓ Verified DFA; test string accepted.", exact=True).wait_for()
    expect(page.locator("video")).to_have_count(0)
    expect(
        page.get_by_role("button", name="Render animation", exact=True)
    ).to_be_enabled()
    shot("desktop-quality-change")
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-advanced")
    # A selected ambiguous tree survives widget cleanup after switching modes.
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.get_by_text("CFG / Parse tree", exact=True).click()
    page.get_by_role("button", name="Ambiguous expression", exact=True).click()
    expect(page.get_by_label("Input tokens", exact=True)).to_have_value("id + id + id")
    page.get_by_role("button", name="Parse & verify", exact=True).click()
    choice = page.get_by_label("Verified parse tree", exact=True)
    choice.click()
    page.get_by_role("option", name="Tree 2 of 2", exact=True).click()
    expect(choice).to_have_value("Tree 2 of 2")
    page.get_by_text("TOC / DFA", exact=True).click()
    page.get_by_text("CFG / Parse tree", exact=True).click()
    expect(choice).to_have_value("Tree 2 of 2")
    page.get_by_text("Inspect a branch", exact=True).click()
    branch = page.get_by_label("Subtree root", exact=True)
    root_label = branch.input_value()
    branch.focus()
    branch.press("ArrowDown")
    branch.press("ArrowDown")
    branch.press("Enter")
    expect(branch).not_to_have_value(root_label)
    page.set_viewport_size({"width": 390, "height": 844})
    shot("narrow-focused-branch")
    # Larger verified machines remain inspectable while animation is unavailable.
    page.close()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:8501")
    page.get_by_text("Make the theory visible.", exact=True).wait_for()
    source("Rule-based baseline")
    from theorybert.data.generators import pattern_dfa

    reference = pattern_dfa("01010101")
    edit("Language description", "Binary strings that end in 01010101.")
    edit("Test string", "01010101")
    page.get_by_text(
        "Advanced settings · checkpoints, reference & rendering", exact=True
    ).click()
    edit("Or paste reference DFA JSON", json.dumps(reference.to_dict()))
    page.get_by_text("Reference loaded.", exact=False).wait_for()
    page.get_by_role("button", name="Predict & verify", exact=True).click()
    page.get_by_text("9 states → 9 minimal.", exact=False).wait_for()
    page.get_by_text("Visualisation supports at most 8 states.", exact=False).wait_for()
    expect(
        page.get_by_role("button", name="Render animation", exact=True)
    ).to_be_disabled()
    shot("desktop-large-dfa")
    assert not errors, errors
    (out / "advanced-browser-report.json").write_text(
        json.dumps(
            {"page_errors": errors, "status": "passed", "screenshots": screenshots},
            indent=2,
        )
    )
    browser.close()
    print("Advanced browser assertions passed")
