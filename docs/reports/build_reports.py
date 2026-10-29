"""Rebuild the two research PDFs from prose, local manifests and measured results."""
from pathlib import Path
import json
import html
import re
import sys
import os

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Flowable, KeepTogether, BaseDocTemplate, PageTemplate, Frame

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
OUT=ROOT/'output/pdf'
FONT=Path('/System/Library/Fonts/Supplemental')
for name,file in [('TimesProject','Times New Roman.ttf'),('TimesProject-Bold','Times New Roman Bold.ttf'),('TimesProject-Italic','Times New Roman Italic.ttf'),('TimesProject-BoldItalic','Times New Roman Bold Italic.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('TimesProject',normal='TimesProject',bold='TimesProject-Bold',italic='TimesProject-Italic',boldItalic='TimesProject-BoldItalic')

BODY=ParagraphStyle('IEEE',fontName='TimesProject',fontSize=10,leading=11.5,alignment=TA_JUSTIFY,spaceAfter=5,splitLongWords=True)
HEAD=ParagraphStyle('Head',parent=BODY,fontName='TimesProject-Bold',alignment=TA_CENTER,spaceBefore=6,spaceAfter=6)
SUB=ParagraphStyle('Sub',parent=BODY,fontName='TimesProject-Italic',alignment=TA_LEFT,spaceBefore=4,spaceAfter=4)
REF=ParagraphStyle('Ref',parent=BODY,fontSize=8,leading=9,alignment=TA_LEFT,spaceAfter=4)
CAP=ParagraphStyle('Cap',parent=BODY,fontSize=8.5,leading=10,alignment=TA_CENTER,spaceAfter=6)
LONG=ParagraphStyle('Report',parent=BODY,fontSize=11,leading=14,spaceAfter=8)
LH=ParagraphStyle('ReportHead',parent=LONG,fontName='TimesProject-Bold',fontSize=17,leading=20,alignment=TA_LEFT,spaceAfter=15)
LS=ParagraphStyle('ReportSub',parent=LONG,fontName='TimesProject-Bold',fontSize=11.5,leading=14,spaceBefore=6,spaceAfter=6,alignment=TA_LEFT)
SMALL=ParagraphStyle('Small',parent=LONG,fontSize=9,leading=11,alignment=TA_LEFT)
NAVY=colors.HexColor('#122c48')


def clean(text):
    # ASCII punctuation, including hyphens, throughout authored text.
    for char in ('\u2014','\u2013','\u2011','\u2212'):text=text.replace(char,'-')
    return text.replace('\u2019',"'").replace('\u2018',"'").replace('\u201c','"').replace('\u201d','"')


def para(text,style=BODY):return Paragraph(clean(text),style)


def table(headers,rows,width,ieee=True,widths=None):
    st=ParagraphStyle('cell',parent=REF if ieee else SMALL,fontSize=8 if ieee else 9,leading=9.5 if ieee else 11,spaceAfter=0)
    values=[[para(str(v),st) for v in row] for row in [headers]+rows]
    t=Table(values,colWidths=widths or [width/len(headers)]*len(headers),hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.7,colors.black),('LINEBELOW',(0,0),(-1,0),.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),.7,colors.black),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    if ieee:t.splitByRow=0
    if not ieee:
        t.spaceAfter=6
        if headers==['Page','Topic']:
            t.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    return t


class Architecture(Flowable):
    """Component/deployment view, not a sequence or flow chart."""
    def __init__(self,width=252,height=265,large=False):
        Flowable.__init__(self);self.width=width;self.height=height;self.large=large
    def draw(self):
        c=self.canv;w=self.width;h=self.height
        c.setStrokeColor(colors.black);c.setLineWidth(.55)
        def box(x,y,bw,bh,title,lines):
            c.setFillColor(colors.HexColor('#f2f5f8') if self.large else colors.white)
            c.roundRect(x,y,bw,bh,3,fill=1,stroke=1)
            p=para('<b>'+title+'</b><br/>'+'<br/>'.join(lines),ParagraphStyle('arch',parent=REF,fontSize=9 if self.large else 8,leading=11 if self.large else 9.5,alignment=TA_CENTER))
            _,ph=p.wrap(bw-10,bh-6);p.drawOn(c,x+5,y+bh-5-ph)
        gap=10
        # Horizontal subsystem bands and an artifact repository form a component
        # architecture. Interface labels, not execution arrows, link the bands.
        box(0,h-45,w,42,'Presentation component',['React studio | DFA, CFG, compiler workspaces','SVG canvas, playback and evidence panels'])
        box(0,h-106,w,43,'Application component',['Starlette jobs, bounded workers, result cache','JSON contracts and verification status'])
        box(0,h-177,(w-gap)/2,51,'Neural component',['Shared BERT encoder','DFA / plan / CFG heads'])
        box((w+gap)/2,h-177,(w-gap)/2,51,'Formal component',['DFA / Earley / AST / IR','Evidence and trace checks'])
        box(0,h-242,w,43,'Artifacts and rendering components',['Manifests, fingerprints, checkpoints, sealed evidence','SVG geometry and optional Manim video cache'])
        for y,label in [(h-55,'HTTP / job JSON'),(h-116,'typed semantic contracts'),(h-188,'checked objects / model artifacts')]:
            c.setDash(2,2);c.line(w*.18,y+3,w*.82,y+3);c.setDash()
            c.setFillColor(colors.white);c.rect(w*.18,y-3,w*.64,9,stroke=0,fill=1)
            c.setFont('TimesProject',7 if not self.large else 8);c.setFillColor(colors.black);c.drawCentredString(w/2,y-1,label)


def draw_blocks(c,blocks,x,top,width,height,style=BODY):
    remaining=height;y=top
    for item in blocks:
        if isinstance(item,str):flow=para(item,style)
        else:
            kind=item[0]
            if kind=='h':flow=para(item[1],HEAD if style is BODY else LH)
            elif kind=='s':flow=para(item[1],SUB if style is BODY else LS)
            elif kind=='cap':flow=para(item[1],CAP)
            elif kind=='small':flow=para(item[1],REF if style is BODY else SMALL)
            elif kind=='space':flow=Spacer(1,item[1])
            elif kind=='lead':flow=para(item[1],ParagraphStyle('Lead',parent=LONG,fontSize=17,leading=21,alignment=TA_LEFT))
            elif kind=='arch':flow=Architecture(width,265 if style is BODY else 245,style is not BODY)
            elif kind=='table':flow=table(item[1],item[2],width,style is BODY,item[3] if len(item)>3 else None)
            else:raise ValueError(item)
        space=flow.getSpaceBefore()
        fw,fh=flow.wrap(width,remaining)
        used=space+fh+flow.getSpaceAfter()
        if used>remaining+.01:
            message=f'Page {c.getPageNumber()} column x={x}: overflow {used-remaining:.1f}pt on {str(item)[:120]}'
            if os.environ.get('REPORT_LAYOUT_AUDIT'):print(message)
            else:raise ValueError(message)
        y-=space+fh;flow.drawOn(c,x,y);y-=flow.getSpaceAfter();remaining-=used
    return remaining


def build():
    from final_solution import ieee_pages,long_pages
    OUT.mkdir(parents=True,exist_ok=True)
    paper=OUT/'TheoryBERT_IEEE_8_Pages.pdf'
    def title_page(c,doc):
        title=para('TheoryBERT: Translating and Understanding<br/>Formal Languages with BERT',ParagraphStyle('Title',fontName='TimesProject',fontSize=23,leading=26,alignment=TA_CENTER))
        _,th=title.wrap(522,70);title.drawOn(c,45,738-th)
    def make_frames(height):
        return [Frame(45+col*270,72,252,height,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id=f'column{col}') for col in range(2)]
    doc=BaseDocTemplate(str(paper),pagesize=(612,792),title='TheoryBERT: Translating and Understanding Formal Languages with BERT',author='TheoryBERT Project',pageCompression=1)
    doc.addPageTemplates([PageTemplate(id='first',frames=make_frames(592),onPage=title_page,autoNextPageTemplate='body'),PageTemplate(id='body',frames=make_frames(666))])
    story=[]
    skip=0
    raw=[item for columns in ieee_pages() for column in columns for item in column]
    # IEEE table captions precede their tables and remain attached.
    arranged=[];at=0
    while at<len(raw):
        if isinstance(raw[at],tuple) and raw[at][0]=='table' and at+1<len(raw) and isinstance(raw[at+1],tuple) and raw[at+1][0]=='cap' and raw[at+1][1].startswith('TABLE'):
            arranged.extend([raw[at+1],raw[at]]);at+=2
        else:arranged.append(raw[at]);at+=1
    raw=arranged
    for i,item in enumerate(raw):
        if skip:
            skip-=1
            continue
        if isinstance(item,str):flow=para(item)
        else:
            kind=item[0]
            if kind=='h':flow=para(item[1],HEAD);flow.keepWithNext=True
            elif kind=='s':
                flow=para(item[1],SUB)
                flow.keepWithNext=True
                if i+2<len(raw) and isinstance(raw[i+1],tuple) and raw[i+1][0]=='cap' and raw[i+1][1].startswith('TABLE') and raw[i+2][0]=='table':
                    following=raw[i+2]
                    flow=KeepTogether([flow,para(raw[i+1][1],CAP),table(following[1],following[2],252,True)])
                    skip=2
            elif kind=='cap':
                flow=para(item[1],CAP)
                if item[1].startswith('TABLE'):
                    following=raw[i+1]
                    flow=KeepTogether([flow,table(following[1],following[2],252,True)])
                    skip=1
            elif kind=='small':flow=para(item[1],REF)
            elif kind=='arch':flow=Architecture(252,265)
            elif kind=='table':flow=table(item[1],item[2],252,True)
            elif kind=='space':flow=Spacer(1,item[1])
            else:raise ValueError(item)
        story.append(flow)
    doc.build(story)
    report=OUT/'TheoryBERT_Comprehensive_Technical_Report.pdf'
    c=canvas.Canvas(str(report),pagesize=(595.276,841.89),pageCompression=1)
    c.setTitle('TheoryBERT Comprehensive Technical Project Report')
    c.setAuthor('TheoryBERT Project')
    for index,(title,blocks) in enumerate(long_pages()):
        c.setStrokeColor(NAVY);c.setLineWidth(.5);c.line(52,795,543,795)
        c.setFillColor(NAVY);c.setFont('TimesProject',9);c.drawString(52,805,'THEORYBERT  |  TECHNICAL PROJECT REPORT')
        c.setFillColor(colors.black)
        spare=draw_blocks(c,[('h',title)]+blocks,52,777,491,700,LONG)
        c.setStrokeColor(colors.HexColor('#b7c0ca'));c.line(52,45,543,45)
        c.setFont('TimesProject',9);c.setFillColor(NAVY)
        c.drawString(52,30,'Final technical solution - 29 October 2026')
        c.drawRightString(543,30,str(index+1))
        print(f'Report page {index+1}: {spare:.1f} pt spare')
        c.showPage()
    c.save()
    return [paper,report]

if __name__=='__main__':
    for path in build():print(path)
