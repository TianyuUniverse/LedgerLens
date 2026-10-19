"""Assemble reviewed Artifact Tool slide renders. Editable content is in PPTX."""
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
ROOT=Path(__file__).resolve().parents[1]
name,stage=sys.argv[1:3]
output=ROOT/'output'/f'{name}.pdf'
c=canvas.Canvas(str(output),pagesize=(1280,720))
c.setTitle(name.replace('_',' '));c.setAuthor('CSSE2026 draft with OpenAI Codex assistance')
for image in sorted(Path(stage).glob('slide-*.png')):
    c.drawImage(str(image),0,0,width=1280,height=720);c.showPage()
c.save()
print(output)
