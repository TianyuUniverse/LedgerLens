"""Create a printable English speaking handout from the current Markdown script."""
import json
import re
from html import escape
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/PROPOSAL_SPEAKING_NOTES_EN.md'
OUTPUT = ROOT / 'output/pdf/PROPOSAL_SPEAKING_NOTES_EN.pdf'
CHECKS = ROOT / 'tmp/pdfs/proposal-speaking-notes'
text = SOURCE.read_text(encoding='utf-8')
slides = re.findall(
    r'## Slide (\d+) - (.*?)\n\nSuggested time: (.*?)\n\n(.*?)(?=\n## |\Z)',
    text, re.S,
)
assert len(slides) == 10, 'Expected ten slide paragraphs.'
qa_text = text.split('## Short English Q&A\n', 1)[1].split('\n## Practice notes', 1)[0]
qa = re.findall(r'\*\*(.*?)\*\*\n\n(.*?)(?=\n\n\*\*|\Z)', qa_text, re.S)
assert len(qa) == 14, 'Expected the current fourteen Q&A entries.'
intro = text.split('\n## Timing guide', 1)[0].split('\n\n')[1:]
timing = text.split('## Timing guide\n', 1)[1].split('\n## Slide 1 ', 1)[0]
rows = [line.strip().strip('|').split('|') for line in timing.splitlines() if line.startswith('|')]
rows = [[cell.strip() for cell in row] for row in rows]
rows = [rows[0]] + rows[2:]
practice = text.split('## Practice notes\n', 1)[1].split('\n## Architecture reference', 1)[0]
reminders = [line[2:] for line in practice.splitlines() if line.startswith('- ')]
reference = text.split('## Architecture reference\n', 1)[1].strip()

for name, filename in [('Arial', 'arial.ttf'), ('Arial-Bold', 'arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / filename)))
GREEN = colors.HexColor('#167569')
INK = colors.HexColor('#183d38')
BODY = colors.HexColor('#32494c')
MUTED = colors.HexColor('#6b8183')
LIGHT = colors.HexColor('#e9f0e3')

def style(name, size, leading, **kw):
    return ParagraphStyle(name, fontName='Arial', fontSize=size, leading=leading,
                          textColor=BODY, **kw)

title = ParagraphStyle(
    'Title', fontName='Arial-Bold', fontSize=22, leading=27, textColor=INK, spaceAfter=7)
subtitle = ParagraphStyle(
    'Subtitle', fontName='Arial', fontSize=11, leading=15, textColor=MUTED, spaceAfter=12)
guide = style('Guide', 9.5, 12.6, spaceAfter=5)
guide_heading = ParagraphStyle('GuideHeading', fontName='Arial-Bold', fontSize=12,
                               leading=16, textColor=GREEN, spaceBefore=9, spaceAfter=5)
table_text = style('TableText', 9, 11.7)
table_header = ParagraphStyle('TableHeader', fontName='Arial-Bold', fontSize=9,
                             leading=11.7, textColor=colors.white)
section = ParagraphStyle('Section', fontName='Arial-Bold', fontSize=20,
                         leading=25, textColor=INK, spaceAfter=13)
slide_heading = ParagraphStyle('SlideHeading', fontName='Arial-Bold', fontSize=13.5,
                               leading=17, textColor=GREEN, spaceAfter=3)
time_style = ParagraphStyle('Time', fontName='Arial', fontSize=10,
                            leading=13, textColor=MUTED, spaceAfter=6)
speech = style('Speech', 13, 18.5, spaceAfter=13)
question = ParagraphStyle('Question', fontName='Arial-Bold', fontSize=12,
                          leading=16, textColor=GREEN, spaceAfter=4)
answer = style('Answer', 12, 17, spaceAfter=12)

def markup(value):
    value = escape(value.strip())
    value = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', value)
    value = re.sub(r'\[(.*?)\]\((https?://[^)]+)\)',
                   lambda m: f'<a href="{m.group(2)}" color="#167569">{m.group(1)}</a>', value)
    return value

def para(value, paragraph_style):
    return Paragraph(markup(value), paragraph_style)

story = [para('LedgerLens', title), para('English Speaking Notes - Practice Guide', subtitle)]
for part in intro:
    if part.strip():
        story.append(para(part, guide))
story.append(para('Timing guide', guide_heading))
table_rows = [[para(cell, table_header if r == 0 else table_text) for cell in row]
              for r, row in enumerate(rows)]
table = Table(table_rows, colWidths=[40, 283, 116, 68], hAlign='LEFT', repeatRows=1)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), GREEN),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, colors.white]),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ('LINEBELOW', (0, -1), (-1, -1), 0.4, colors.HexColor('#c5d6c7')),
]))
story.append(table)
story.append(para('Practice notes', guide_heading))
for reminder in reminders:
    story.append(Paragraph('- ' + markup(reminder), guide))
story.append(para('Architecture reference', guide_heading))
story.append(para(reference, guide))

for start, end in [(0, 5), (5, 10)]:
    story.append(PageBreak())
    story.append(para(f'Main Script - Slides {start+1}-{end}', section))
    for number, heading, duration, words in slides[start:end]:
        story.append(KeepTogether([
            para(f'Slide {number} - {heading}', slide_heading),
            para(f'Suggested time: {duration}', time_style),
            para(words, speech),
        ]))

for start, end in [(0, 7), (7, 14)]:
    story.append(PageBreak())
    story.append(para(f'English Q&A - Questions {start+1}-{end}', section))
    for index, (prompt, response) in enumerate(qa[start:end], start+1):
        story.append(KeepTogether([
            para(f'{index}. {prompt}', question),
            para(response, answer),
        ]))

def decorate(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#c5d6c7'))
    canvas.setLineWidth(0.5)
    canvas.line(44, 37, A4[0]-44, 37)
    canvas.setFont('Arial', 9)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 23, 'LedgerLens - English Proposal Speaking Notes')
    canvas.drawRightString(A4[0]-44, 23, f'Page {doc.page} of 5')
    canvas.restoreState()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=44, rightMargin=44,
                             topMargin=40, bottomMargin=49,
                             title='LedgerLens - Simple English Proposal Speaking Notes',
                             author='LedgerLens Team', subject='Five-minute script and English Q&A')
document.build(story, onFirstPage=decorate, onLaterPages=decorate)

reader = PdfReader(OUTPUT)
assert len(reader.pages) == 5, f'Expected five pages, got {len(reader.pages)}. Review layout.'
normalize = lambda value: re.sub(r'\s+', ' ', value).strip()
main_text = normalize(' '.join(reader.pages[i].extract_text() for i in [1, 2]))
qa_pdf = normalize(' '.join(reader.pages[i].extract_text() for i in [3, 4]))
for _, _, _, words in slides:
    assert normalize(words) in main_text, 'A main paragraph is missing or changed.'
for prompt, response in qa:
    assert normalize(prompt) in qa_pdf and normalize(response) in qa_pdf, 'Q&A changed.'
word_count = sum(len(re.findall(r"\b[\w]+(?:['-][\w]+)*\b", part[3])) for part in slides)
assert word_count == 575
assert not re.search(r'school|roommate|electricity|air conditioning|computer|six thousand|two hundred', main_text, re.I)
CHECKS.mkdir(parents=True, exist_ok=True)
result = {'pdf': str(OUTPUT), 'pages': 5, 'main_script_words': word_count,
          'slide_sections': len(slides), 'qa_entries': len(qa),
          'script_text_matches_markdown': True, 'examples_in_qa_only': True}
(CHECKS/'content_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
