"""Check visible BERT diagnostics and challenge evidence with the real app."""
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

OUT = Path('artifacts/challenge-ui')
OUT.mkdir(parents=True, exist_ok=True)


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1050}, reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8501/grammar')
        expect(page.get_by_label('Grammar source',exact=True)).to_have_value('learned',timeout=15000)
        page.get_by_role('button',name='Arithmetic compiler',exact=True).click()
        page.get_by_label('Input tokens',exact=True).fill('a+*b')
        page.get_by_role('button',name='Parse & verify',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('No derivation',timeout=30000)
        expect(page.locator('#grammar-editor')).to_have_value(__import__('re').compile('E.*->'))
        expect(page.get_by_text('These are BERT’s actual productions from the failed request. No replacement grammar or tree was supplied.',exact=True)).to_be_visible()
        expect(page.locator('.graph-svg')).to_have_count(0)
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(OUT/'actual-bert-failure-productions.png'),full_page=True)
        page.get_by_label('Input tokens',exact=True).fill('(a+3)*b')
        page.get_by_role('button',name='Parse & verify',exact=True).click()
        expect(page.get_by_text('Verified derivation',exact=True)).to_be_visible(timeout=30000)
        page.get_by_role('tab',name='Compiler analysis',exact=True).click()
        expect(page.locator('.ast-diagram')).to_be_visible()
        expect(page.locator('.arithmetic-output')).to_contain_text('%t1')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(OUT/'valid-code-after-correction.png'),full_page=True)
        page.goto('http://127.0.0.1:8501/research')
        expect(page.get_by_text(__import__('re').compile('Fresh wording challenge:'))).to_be_visible(timeout=15000)
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(OUT/'fresh-challenge-research.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(OUT/'fresh-challenge-mobile.png'),full_page=True)
        browser.close()
    assert not errors, errors
    report={'passed':True,'page_errors':errors,'checks':['Actual BERT productions retained after invalid input','No substitute tree after failure','Corrected source produces a checked AST and IR','Research distinguishes fresh challenge from generated benchmark','Mobile overflow']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
