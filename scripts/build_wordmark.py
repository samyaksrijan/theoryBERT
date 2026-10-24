"""Outline the licensed Poppins wordmark for sharp, font-independent animation.

This is an optional asset-authoring helper. The generated SVG and path data are
checked in; running TheoryBERT does not require fontTools.
"""
import json
from pathlib import Path
import shutil
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
FONTS = FRONTEND / "node_modules/@fontsource/poppins"


def load(weight):
    font = TTFont(FONTS / f"files/poppins-latin-{weight}-normal.woff2")
    return font, font.getGlyphSet(), font.getBestCmap()


def advance(font, cmap, word, scale):
    return sum(font['hmtx'][cmap[ord(char)]][0] * scale for char in word)


def main():
    bold, bold_glyphs, bold_cmap = load(700)
    medium, medium_glyphs, medium_cmap = load(600)
    top_scale, lower_scale = .1, .027
    width = advance(bold, bold_cmap, 'BERT', top_scale)
    tracking = (width - advance(medium, medium_cmap, 'THEORY', lower_scale)) / 5
    letters = []
    for text, font, glyphs, cmap, scale, baseline, spacing, start, stagger in [
        ('BERT', bold, bold_glyphs, bold_cmap, top_scale, 74, 0, 0, .12),
        ('THEORY', medium, medium_glyphs, medium_cmap, lower_scale, 113, tracking, .48, .07),
    ]:
        x = 0
        for i, char in enumerate(text):
            name = cmap[ord(char)]
            pen = SVGPathPen(glyphs)
            glyphs[name].draw(TransformPen(pen, Transform(scale, 0, 0, -scale, x, baseline)))
            letters.append({'letter': char, 'd': pen.getCommands(), 'delay': round(start + i*stagger, 2)})
            x += font['hmtx'][name][0] * scale + spacing
    data = {'viewBox': f'-3 0 {width+19:.2f} 119', 'letters': letters, 'dot': {'x': round(width+5,2), 'y': 66, 'width':8, 'height':8}}
    target = FRONTEND / 'src/components/wordmark-paths.json'
    target.write_text(json.dumps(data, separators=(',',':'))+'\n')
    paths = ''.join(f'<path d="{letter["d"]}"/>' for letter in letters)
    dot = data['dot']
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{data["viewBox"]}" role="img" aria-label="TheoryBERT"><g fill="#0d0c22">{paths}</g><rect x="{dot["x"]}" y="{dot["y"]}" width="8" height="8" fill="#e84b89"/></svg>\n'
    (FRONTEND / 'public/theorybert-logo.svg').write_text(svg)
    icon = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#0d0c22"/><path d="{letters[0]["d"]}" transform="translate(8 4) scale(.73)" fill="white"/><rect x="51" y="51" width="6" height="6" fill="#e84b89"/></svg>\n'
    (FRONTEND / 'public/favicon.svg').write_text(icon)
    shutil.copyfile(FONTS/'LICENSE', FRONTEND/'public/fonts/Poppins-LICENSE.txt')
    print('Built stacked Poppins wordmark and SVG outline animation data.')


if __name__ == '__main__':
    main()
