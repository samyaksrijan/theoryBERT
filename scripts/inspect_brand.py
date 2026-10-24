"""Visual acceptance of the Poppins write-on intro and shared wordmark."""
from pathlib import Path
import json
from playwright.sync_api import expect, sync_playwright


def main():
    output = Path('artifacts/brand-ui')
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='no-preference')
        page = context.new_page()
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8501/')
        expect(page.locator('.startup-screen')).to_be_visible()
        expect(page.get_by_role('heading',level=1)).not_to_be_visible()
        page.screenshot(path=str(output/'intro-writing-start.png'))
        page.wait_for_timeout(650)
        page.screenshot(path=str(output/'intro-writing-mid.png'))
        page.wait_for_timeout(900)
        page.screenshot(path=str(output/'intro-written.png'))
        expect(page.locator('.startup-screen')).to_have_count(0,timeout=5000)
        expect(page.get_by_role('heading',level=1)).to_be_visible()
        expect(page.get_by_text('Runs locally',exact=True)).to_be_visible()
        assert page.locator('body').evaluate('(e)=>getComputedStyle(e).overflow') != 'hidden'
        page.screenshot(path=str(output/'landing-logo-desktop.png'),full_page=True)
        page.get_by_role('link',name='Open workspace',exact=True).click()
        expect(page.get_by_role('heading',level=1)).to_contain_text('DFA')
        expect(page.locator('.startup-screen')).to_have_count(0)
        page.get_by_role('link',name='TheoryBERT home',exact=True).click()
        expect(page.get_by_role('heading',level=1)).to_be_visible()
        expect(page.locator('.startup-screen')).to_have_count(0)
        page.reload()
        expect(page.locator('.startup-screen')).to_be_visible()
        page.wait_for_timeout(700)
        page.get_by_role('button',name='Skip intro',exact=False).click()
        expect(page.locator('.startup-screen')).to_have_count(0)
        expect(page.get_by_role('heading',level=1)).to_be_focused()
        page.reload()
        expect(page.locator('.startup-screen')).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('.startup-screen')).to_have_count(0)
        page.set_viewport_size({'width':390,'height':844})
        page.reload()
        expect(page.locator('.startup-screen')).to_be_visible()
        page.wait_for_timeout(1450)
        page.screenshot(path=str(output/'intro-mobile.png'))
        expect(page.locator('.startup-screen')).to_have_count(0,timeout=5000)
        expect(page.get_by_role('heading',level=1)).to_be_visible()
        page.screenshot(path=str(output/'landing-logo-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth') <= 390
        reduced = browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        reduced_page = reduced.new_page()
        reduced_page.on('pageerror',lambda error:errors.append(str(error)))
        reduced_page.goto('http://127.0.0.1:8501/')
        expect(reduced_page.get_by_role('heading',level=1)).to_be_visible()
        expect(reduced_page.locator('.startup-screen')).to_have_count(0)
        reduced_page.goto('http://127.0.0.1:8501/dfa')
        expect(reduced_page.get_by_role('heading',level=1)).to_be_visible()
        expect(reduced_page.locator('.startup-screen')).to_have_count(0)
        assert not errors, errors
        (output/'report.json').write_text(json.dumps({'status':'passed','page_errors':errors,'checks':['normal startup sequence','skip','Escape','no replay on navigation','direct studio access','reduced motion','desktop/mobile logo layout']},indent=2))
        browser.close()
    print('Brand checks passed: animated startup, automatic reveal, Skip/Escape, navigation, reduced motion, desktop and mobile.')


if __name__ == '__main__':
    main()
