"""Create separate demonstration lettering; never alter supplied artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parents[1]
folder=root/'art/generated/uniform_names_20261014'
folder.mkdir(parents=True,exist_ok=True)
font_file=Path(r'C:\Windows\Fonts\georgiai.ttf')
if not font_file.exists():
    font_file=Path(r'C:\Windows\Fonts\ariali.ttf')
for key,name in [('romario','Romario Vicente Amaro'),('ana','Ana Clara')]:
    image=Image.new('RGBA',(1024,384),(0,0,0,0))
    draw=ImageDraw.Draw(image)
    color=(170,118,41,255)
    draw.text((512,116),'Técnico de Enfermagem',font=ImageFont.truetype(str(font_file),58),fill=color,anchor='mm')
    size=76
    while draw.textlength(name,font=ImageFont.truetype(str(font_file),size))>940 and size>24:
        size-=2
    draw.text((512,248),name,font=ImageFont.truetype(str(font_file),size),fill=color,anchor='mm')
    target=folder/f'demo_{key}.png'
    if target.exists():
        raise FileExistsError(target)
    image.save(target)
    print(target)
