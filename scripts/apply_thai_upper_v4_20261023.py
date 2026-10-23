from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'scripts/apply_thai_upper_bind_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_V4_20261023.blend',
 'PREP_FOLDER':ROOT/'reports/thai_upper_refit_v4_20261023',
 'PREP_OUT':ROOT/'art/character_refit_20261023/CHR_Thai_Upper_Bind_V4_20261023.glb',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_UPPER_BIND_V4_20261023.json',
 'PREP_USE_VALIDATED_BMESH':True}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
