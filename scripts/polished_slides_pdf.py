"""Export the reviewed polished slide renders to a presentation PDF."""
import sys
from pathlib import Path
from pypdf import PdfReader
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[1]
revision=sys.argv[1] if len(sys.argv)>1 else ''
name='202464870547-陈天宇-202464871352-朱俊丞-202464871290-张瀚文'
stage=ROOT/('tmp/decks/ledgerlens-polished'+revision)
target=ROOT/'output/精美版'/(name+'.pdf')
images=sorted(stage.glob('slide-*.png'))
assert len(images)==10
titles=['LedgerLens','Table of Contents','User Needs & Pain Points','Project Positioning & Users','User Research','Product Workflow','System Architecture','Core Innovations','Validation & Risks','Plan & Outlook']
c=canvas.Canvas(str(target),pagesize=(1280,720))
c.setTitle('LedgerLens - Project Proposal')
c.setAuthor('Chen Tianyu, Zhu Juncheng, Zhang Hanwen')
for i,image in enumerate(images):
    key=f'slide-{i+1}'
    c.bookmarkPage(key)
    c.addOutlineEntry(titles[i],key,level=0)
    c.drawImage(str(image),0,0,width=1280,height=720)
    if i==1:
        for j in range(8):
            x=72 if j<4 else 690
            y=231+(j%4)*99
            c.linkRect('',f'slide-{j+3}',(x,720-y-88,x+522,720-y),relative=0,thickness=0)
    c.showPage()
c.save()
assert len(PdfReader(target).pages)==10
print(target)
