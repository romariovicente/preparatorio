from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/validate_thai_standing_seams_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAIR_V9_20261023.blend',
 'PREP_OUT':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAIR_V9_PROBES_20261023.blend',
 'PREP_FOLDER':ROOT/'reports/thai_hair_v9_20261023',
 'PREP_SOURCE_REPORT':ROOT/'reports/CHARACTER_THAI_HAIR_V9_20261023.json',
 'PREP_QA_SCENE':'VALIDATE_THAI_HAIR_BIND_V9_20261023',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_HAIR_V9_REIMPORT_20261023.json'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
