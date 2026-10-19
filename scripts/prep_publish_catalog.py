"""Publish only successfully exported and reimported local assets."""
from pathlib import Path
import json, struct, hashlib
ROOT=Path(__file__).resolve().parents[1]
names={'esqueleto':'Esqueleto humano','Anatomic_Muscle_study':'Estudo muscular','Vitruvian_Man_3D':'Homem Vitruviano',
'doctor_horror_hospital':'Médico · tema de terror','bone_seraph_skeletal_angel':'Serafim · fantasia',
'plague_doctor___bone_mask__warding_cane':'Médico da peste · máscara óssea',
'plague_doctor_alchemist___glass_beak_mask':'Alquimista · fantasia',
'thai_student_v9':'Estudante · pose casual','school_girl_v21':'Estudante 01',
'japanese_school_girl_v25':'Estudante 02','woman_seated_v15':'Leitora sentada',
'woman_standing_v38__eko':'Mulher · esportiva','woman_standing_v33':'Mulher · urbana',
'woman_standing_v16':'Mulher · elegante','facultad_de_enfermeria_unal_colombia':'Faculdade de Enfermagem · Colômbia',
'gm_hospitals_stand_design':'Hospital · estande','hospital_01':'Hospital 01','hospital_02':'Hospital 02',
'hospital_03':'Hospital 03 · uso não comercial','kit_hospital':'Equipamentos hospitalares'}
records=[]
for p in sorted((ROOT/'reports/supplied').glob('*.json')):
    r=json.loads(p.read_text(encoding='utf-8'))
    if r['status']!='validated':continue
    f=ROOT/'frontend/public'/r['url'].lstrip('/')
    assert hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
    with f.open('rb') as stream:
        header=stream.read(20); doc=json.loads(stream.read(struct.unpack_from('<I',header,12)[0]))
    if r['animated']:
        assert len(doc.get('animations',[]))>=len(r['animations'])
        r['exportedAnimations']=[a.get('name') for a in doc.get('animations',[])]
    r['originalRig']=bool(doc.get('skins'))
    r['heavyAsset']=r['bytes']>30*1024*1024
    r['name']=names.get(r['id'][4:],r['credits'].get('title',r['id'][4:]))
    r['licenseStatus']='noncommercial' if 'NC' in r['credits'].get('license','') else 'attribution' if r['credits'].get('license') else 'unknown'
    records.append(r)
(ROOT/'frontend/src/config/suppliedAssets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Créditos dos modelos fornecidos pelo criador','',
'Arquivos originais preservados na pasta indicada pelo usuário. Versões derivadas locais: redução de malhas estáticas, união de objetos e texturas até 1024 px. A atribuição abaixo reproduz os metadados dos GLBs; não representa verificação independente da autoria.','',
'Hospital 03: CC BY-NC-SA 4.0, apenas uso não comercial e derivação sob a mesma licença. Alguns modelos não incluem licença nos metadados; veja a situação individual abaixo. A autorização de redistribuição desses modelos permanece a confirmar.','']
for r in records:
    c=r['credits']; lines += [f"## {r['name']}",f"- Arquivo: `{r['url']}`",f"- Autor: {c.get('author','Não informado no arquivo')}",f"- Origem: {c.get('source',r['sourceRelative'])}",f"- Licença: {c.get('license','Não informada no arquivo')}",f"- Alterações: {r['modifications']}",'']
(ROOT/'THIRD_PARTY_ASSETS.md').write_text('\n'.join(lines),encoding='utf-8')
print('Published',len(records),'validated assets')

