from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/validate_thai_standing_seams_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_TRANSITION_V10_20261023.blend',
 'PREP_OUT':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_TRANSITION_V10_PROBES_20261023.blend',
 'PREP_FOLDER':ROOT/'reports/thai_transition_v10_20261023',
 'PREP_SOURCE_REPORT':ROOT/'reports/CHARACTER_THAI_TRANSITION_V10_20261023.json',
 'PREP_QA_SCENE':'VALIDATE_THAI_TRANSITION_BIND_V10_20261023',
 'PREP_EXTRA_HEAD_TURN':True,
 'PREP_SCOPE':'continuous-neck-collar-local-increment-not-neutral-or-runtime',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_TRANSITION_V10_REIMPORT_20261023.json'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
