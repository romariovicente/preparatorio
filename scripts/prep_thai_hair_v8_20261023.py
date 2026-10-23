"""Test conservative rigid hair while preserving ambiguous neck/collar seams."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/prep_thai_standing_pilot_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAIR_V8_20261023.blend',
 'PREP_FOLDER':ROOT/'reports/thai_hair_v8_20261023',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_HAIR_V8_20261023.json',
 'PREP_WEIGHTS':ROOT/'work/qa_thai_hair_waist_20261023/hair_weights_v8_conservative.npz',
 'PREP_BIND_OUTPUT':ROOT/'art/character_refit_20261023/CHR_Thai_Hair_Bind_V8_20261023.glb',
 'PREP_BIND_LIBRARY':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAIR_BIND_V8_20261023.blend',
 'PREP_SOURCE_DESCRIPTION':'PREP_CHARACTER_THAI_SEAM_V7_20261023.blend',
 'PREP_ARM_SPLAY':.28,'PREP_FOREARM_FORWARD':.28,'PREP_EXTRA_CLOSEUPS':True}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
