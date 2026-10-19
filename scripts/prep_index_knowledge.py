"""Index the supplied local study book without altering it."""
from pathlib import Path
import json,shutil,hashlib,re
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
inventory=json.loads((ROOT/'reports/supplied_assets_inventory.json').read_text(encoding='utf-8'))
source_root=Path(inventory[0]['path']).parents[1]
source=next((source_root/'Livros de Conhecimentos de Enfermagem').glob('*.pdf'))
reader=PdfReader(source);assert len(reader.pages)==150
dest=ROOT/'frontend/public/assets/knowledge/guia_enfermagem.pdf';dest.parent.mkdir(parents=True,exist_ok=True)
digest=hashlib.sha256(source.read_bytes()).hexdigest()
if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
else:shutil.copy2(source,dest)
lessons=[]
for page_index,category in [(1,'Matemática'),(2,'Bases do curso')]:
    lines=[line.strip() for line in reader.pages[page_index].extract_text().splitlines()]
    for i,line in enumerate(lines):
        if line.isdigit() and i and 7<=int(line)<=66:
            title=re.sub(r'^\d+\.\s*','',lines[i-1])
            lessons.append({'id':'page-'+line,'title':title,'page':int(line),'category':category})
quizzes=[
('Qual registro apresenta número e unidade?',['100','100 mL','cem'],1,'A unidade informa a grandeza. O número sozinho é ambíguo.'),
('Quanto é 1,25 + 0,50?',['1,30','1,75','6,25'],1,'Alinhe as casas decimais: 1,25 + 0,50 = 1,75.'),
('Quanto é 1,2 × 4?',['4,8','1,6','12,4'],0,'São quatro parcelas iguais: 1,2 + 1,2 + 1,2 + 1,2.'),
('Quanto é 1,25 ÷ 0,25?',['0,5','5','50'],1,'Confira pela multiplicação: 5 × 0,25 = 1,25.'),
('A fração 3/4 corresponde a:',['25%','34%','75%'],2,'3 dividido por 4 é 0,75; em porcentagem, 75%.'),
('Em 2 + 3 × 4, qual operação vem primeiro?',['Adição','Multiplicação','Qualquer uma'],1,'Sem parênteses, a multiplicação antecede a adição.'),
('Quantos mL há em 1 L?',['10','100','1000'],2,'O prefixo mili representa a milésima parte: 1000 mL = 1 L.'),
('Uma hora e meia corresponde a:',['150 minutos','90 minutos','60 minutos'],1,'Uma hora tem 60 minutos. Meia hora acrescenta 30 minutos.')]
for lesson,quiz in zip(lessons,quizzes):
    question,options,answer,explanation=quiz
    lesson['quiz']={'question':question,'options':options,'answer':answer,'explanation':explanation}
lessons.extend([{'id':'page-70','title':'Patógenos, mecanismos e casos','page':70,'category':'Leitura ilustrada'},{'id':'page-95','title':'Anatomia, vias e procedimentos ilustrados','page':95,'category':'Leitura ilustrada'}])
data={'title':'Guia Técnico de Enfermagem','url':'/assets/knowledge/guia_enfermagem.pdf','pages':150,'sha256':digest,'driveUrl':'https://drive.google.com/file/d/1a_TqJ0M44kXhwFPvkwXiXGcW_kMEyt-F/view','notice':'Material de estudo fornecido pelo criador, elaborado com assistência de IA. A apresentação informa que não recebeu validação clínica independente. Exercícios de matemática são fictícios; conteúdos clínicos requerem orientação docente e protocolos atualizados.','lessons':lessons}
(ROOT/'frontend/src/config/studyBook.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/knowledge_index.json').write_text(json.dumps({'source':str(source),'pages':150,'sha256':digest,'indexedLessons':len(lessons),'quizzes':len(quizzes),'reviewedPages':[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],'driveRootItems':66,'driveSubfolderGuideVerified':True,'fullClinicalValidation':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Indexed',len(lessons),'guided readings,',len(quizzes),'math quizzes')
