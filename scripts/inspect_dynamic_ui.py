"""Real browser acceptance checks for input-dependent machine/tree/compiler output."""
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

OUT = Path('artifacts/dynamic-ui')
OUT.mkdir(parents=True, exist_ok=True)


def main():
    errors, screenshots = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1050}, reduced_motion='reduce')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://127.0.0.1:8501/dfa')
        source = page.get_by_label('Prediction source', exact=True)
        expect(source).to_be_enabled(timeout=15000)
        source.select_option('learned')
        description = page.get_by_label('Language description', exact=False)
        value = page.get_by_label('Test string', exact=False)
        build = page.get_by_role('button', name='Build & verify', exact=True)
        description.fill('Binary strings that end with 01')
        value.fill('1101')
        build.click()
        expect(page.locator('.machine-metrics')).to_contain_text('3 states', timeout=15000)
        expect(page.locator('.execution-path summary')).to_contain_text('ACCEPT')
        shape = page.locator('.graph-svg').inner_html()
        value.fill('00')
        expect(page.locator('.execution-path summary')).to_contain_text('REJECT', timeout=15000)
        expect(page.locator('.machine-metrics')).to_contain_text('3 states')
        description.fill('Binary strings that end with 0101')
        value.fill('110101')
        build.click()
        expect(page.locator('.machine-metrics')).to_contain_text('5 states', timeout=15000)
        assert shape != page.locator('.graph-svg').inner_html()
        expect(page.locator('.source-line')).to_contain_text('google-bert/bert-base-uncased')
        page.screenshot(path=str(OUT/'dfa-five-states.png'), full_page=True)
        screenshots.append('dfa-five-states.png')
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth+1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(OUT/'dfa-mobile.png'), full_page=True)
        screenshots.append('dfa-mobile.png')
        page.set_viewport_size({'width':1440,'height':1050})
        page.goto('http://127.0.0.1:8501/grammar')
        page.get_by_role('button',name='Balanced aⁿbⁿ',exact=True).click()
        expect(page.get_by_label('Grammar source',exact=True)).to_have_value('learned')
        text = page.get_by_label('Input tokens',exact=True)
        text.fill('ab')
        page.get_by_role('button',name='Parse & verify',exact=True).click()
        expect(page.get_by_text('Verified derivation',exact=True)).to_be_visible(timeout=15000)
        expect(page.locator('.source-line')).to_contain_text('BERT language encoder')
        nodes = page.locator('.graph-svg [data-node]').count()
        text.fill('aabb')
        expect(page.get_by_text('Verified derivation',exact=True)).to_be_visible(timeout=15000)
        expect(page.locator('.graph-svg [data-node]')).to_have_count(7, timeout=15000)
        assert page.locator('.graph-svg [data-node]').count() > nodes
        page.screenshot(path=str(OUT/'grammar-aabb.png'), full_page=True)
        screenshots.append('grammar-aabb.png')
        page.get_by_role('button',name='Arithmetic compiler',exact=True).click()
        page.get_by_role('button',name='Parse & verify',exact=True).click()
        expect(page.get_by_text('Verified derivation',exact=True)).to_be_visible(timeout=15000)
        page.get_by_role('tab',name='Compiler analysis',exact=True).click()
        expect(page.get_by_text('IR preserves the syntax tree',exact=True)).to_be_visible()
        expect(page.locator('.ast-diagram')).to_be_visible()
        expect(page.locator('.arithmetic-output')).to_contain_text('%t3')
        page.screenshot(path=str(OUT/'compiler-ast-ir.png'), full_page=True)
        screenshots.append('compiler-ast-ir.png')
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth+1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(OUT/'compiler-mobile.png'), full_page=True)
        screenshots.append('compiler-mobile.png')
        browser.close()
    assert not errors, errors
    report = {'passed':True,'page_errors':errors,'screenshots':screenshots,'checks':['Real BERT DFA predictions change state counts and edges with description','test string auto-simulates on the same machine','grammar input auto-rebuilds derivation','BERT-generated compiler grammar, AST and checked IR','desktop/mobile overflow']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
