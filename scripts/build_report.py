"""Build the technical report using the bundled PDF runtime, not an app dependency."""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
for name,font in [('Body','arial.ttf'),('Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/font)))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportBody',fontName='Body',fontSize=9.3,leading=13.4,spaceAfter=8,textColor=colors.HexColor('#263e42')))
styles.add(ParagraphStyle(name='ReportH1',fontName='Bold',fontSize=21,leading=26,spaceAfter=16,textColor=colors.HexColor('#153e38')))
styles.add(ParagraphStyle(name='ReportH2',fontName='Bold',fontSize=15,leading=19,spaceAfter=10,textColor=colors.HexColor('#153e38')))
styles.add(ParagraphStyle(name='ReportH3',fontName='Bold',fontSize=11.2,leading=16,spaceBefore=9,spaceAfter=7,textColor=colors.HexColor('#167569')))
styles.add(ParagraphStyle(name='Cell',fontName='Body',fontSize=8.2,leading=11.2,textColor=colors.HexColor('#263e42')))
styles.add(ParagraphStyle(name='CellHead',fontName='Bold',fontSize=8.3,leading=11.2,textColor=colors.white))

def para(text,style='ReportBody'):
    text=escape(text)
    text=re.sub(r'(https://[^\s]+)',r'<link href="\1" color="#167569">\1</link>',text)
    return Paragraph(text,styles[style])

def table(rows,widths=None):
    n=len(rows[0]);widths=widths or ([90,220,205] if n==3 else [140,375])
    cells=[[para(v,'CellHead' if r==0 else 'Cell') for v in row] for r,row in enumerate(rows)]
    obj=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    obj.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#167569')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#edf3ea'),colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dbe5dd'))]))
    return obj

def diagram(kind):
    d=Drawing(515,145 if kind=='domain' else 170)
    def box(x,y,w,h,title,lines):
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor('#edf3ea'),strokeColor=colors.HexColor('#adc4b4'),strokeWidth=.7))
        d.add(String(x+10,y+h-19,title,fontName='Bold',fontSize=10,fillColor=colors.HexColor('#153e38')))
        for i,line in enumerate(lines):d.add(String(x+10,y+h-37-i*13,line,fontName='Body',fontSize=8,fillColor=colors.HexColor('#263e42')))
    if kind=='domain':
        box(0,50,158,90,'Transaction',['date, amount_fen, kind','category, fingerprint','0..* records per workspace'])
        box(177,50,158,90,'SavingsScenario',['target, current, months, cuts','computed source IDs','one saved current plan'])
        box(354,50,158,90,'Budget',['category, limit_fen','latest-month source IDs','0..* category limits'])
        d.add(String(0,15,'AuditEvent records changes and outcomes across the workspace.',fontName='Body',fontSize=9))
    else:
        box(0,76,145,80,'Browser interface',['charts, records, review','scenario forms, questions'])
        box(180,76,145,80,'Python service',['validation, calculations','HTTP routes, model seam'])
        box(370,76,145,80,'SQLite',['transactions, budgets','settings, audit'])
        box(180,0,205,58,'Optional model provider',['description in / JSON proposal out'])
        for x1,x2 in [(145,180),(325,370)]:
            d.add(Line(x1,112,x2,112,strokeColor=colors.HexColor('#167569')))
            d.add(Line(x2-4,115,x2,112,strokeColor=colors.HexColor('#167569')))
            d.add(Line(x2-4,109,x2,112,strokeColor=colors.HexColor('#167569')))
        d.add(Line(251,76,251,58,strokeColor=colors.HexColor('#167569')))
    return d

# Preserve the earlier report's baseline scope when rebuilding historical materials.
evidence=json.loads((ROOT/'output/evidence/baseline-20261009/verification.json').read_text(encoding='utf-8'))
body=(ROOT/'docs/TECHNICAL_REPORT.md').read_text(encoding='utf-8')
story=[]
for block_index,block in enumerate(body.split('---PAGE---')):
    if block_index:story.append(PageBreak())
    lines=block.strip().splitlines();i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                parts=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',v) for v in parts):rows.append(parts)
                i+=1
            widths=[48,255,212] if rows[0][0]=='ID' else None
            if len(rows[0])==3 and rows[0][0] in ('Operation','Choice','Risk / abnormal input'):widths=[116,193,206]
            story.extend([table(rows,widths),Spacer(1,10)]);continue
        if line=='[[SCREENSHOT]]':
            story.extend([Spacer(1,10),Image(str(ROOT/'output/evidence/dashboard-clean.png'),width=515,height=357.64),Spacer(1,8)])
        elif line=='[[DOMAIN]]':story.extend([diagram('domain'),Spacer(1,8)])
        elif line=='[[ARCHITECTURE]]':story.extend([diagram('architecture'),Spacer(1,8)])
        elif line=='[[RESULTS]]':
            rows=[['Measured check','Result','Scope'],['Domain and HTTP tests',f"{evidence['test_count']} passed, 0 failures",'Temporary SQLite databases'],['Rules classification',f"{evidence['baseline_evaluation']['correct']} / 20 labels",'Synthetic, rules-informed set'],['Grounded Q&A',f"{evidence['grounded_qa']['passed']} / 9 cases",'6 supported and 3 refused'],['Browser workflow','Passed','Real UI actions in Edge'],['Model boundary','Fallback / no write','Injected providers only']]
            story.extend([table(rows,[160,140,215]),Spacer(1,10)])
        elif line=='[[EVALUATION]]':
            story.extend([table([['Component','Evaluation and outcome'],['Rules baseline','18/20 correct category labels. Two unknown merchants require correction.'],['Grounded Q&A','9/9 authored expected-result and refusal cases pass.'],['Model boundary','Malformed schema, invalid confidence and failures fall back. Proposals do not write records.'],['Live language model','Not configured or evaluated. No accuracy, cost or latency claim.']]),Spacer(1,10)])
        elif line.startswith('### '):story.append(para(line[4:],'ReportH3'))
        elif line.startswith('## '):story.append(para(line[3:],'ReportH2'))
        elif line.startswith('# '):story.append(para(line[2:],'ReportH1'))
        else:
            paragraph=[line];i+=1
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','[[')):
                paragraph.append(lines[i].strip());i+=1
            story.append(para(' '.join(paragraph)));continue
        i+=1

def page(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#dbe5dd'));canvas.line(40,35,555,35)
    canvas.setFont('Body',8);canvas.setFillColor(colors.HexColor('#687d82'))
    canvas.drawString(40,23,'LedgerLens / CSSE2026 / Initial AI-assisted package for team review')
    canvas.drawRightString(555,23,str(doc.page))

doc=SimpleDocTemplate(str(OUT/'LedgerLens_Technical_Report.pdf'),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=37,bottomMargin=47,title='LedgerLens Technical Report',author='CSSE2026 project draft with OpenAI Codex assistance')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(OUT/'LedgerLens_Technical_Report.pdf')
