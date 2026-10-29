"""Render all final pages and check text, links, page bounds and page counts."""
import json,re
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tmp/pdfs'
OUT.mkdir(parents=True,exist_ok=True)
checks=[]
for name,count,prefix in [('TheoryBERT_IEEE_8_Pages.pdf',8,'ieee'),('TheoryBERT_Comprehensive_Technical_Report.pdf',34,'report')]:
 path=ROOT/'output/pdf'/name
 doc=pymupdf.open(path)
 assert len(doc)==count,(name,len(doc))
 text='\n'.join(p.get_text() for p in doc)
 assert '\u2014' not in text
 assert not any(token in text for token in ['turn10view','turn9search','TODO','PLACEHOLDER'])
 pages=[]
 for i,page in enumerate(doc):
  outside=[]
  for block in page.get_text('blocks'):
   if block[0]<35 or block[1]<20 or block[2]>page.rect.width-35 or block[3]>page.rect.height-20:outside.append(block[:4])
  assert not outside,(name,i+1,outside)
  pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
  pix.save(OUT/f'{prefix}-{i+1:02}.png')
  pages.append({'page':i+1,'words':len(page.get_text().split()),'links':len(page.get_links())})
 checks.append({'file':str(path.relative_to(ROOT)),'pages':len(doc),'bytes':path.stat().st_size,'words':len(text.split()),'em_dashes':0,'page_checks':pages})
(ROOT/'artifacts/report-qa.json').write_text(json.dumps(checks,indent=2))
print(json.dumps([{k:v for k,v in x.items() if k!='page_checks'} for x in checks],indent=2))
