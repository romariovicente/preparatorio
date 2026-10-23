from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/prep_thai_standing_pilot_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_STANDING_V2_20261023.blend',
 'PREP_FOLDER':ROOT/'reports/thai_standing_v2_20261023',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_STANDING_V2_20261023.json',
 'PREP_WEIGHTS':ROOT/'work/qa_thai_standing_seams_20261023/seam_weight_candidate.npz',
 'PREP_BIND_OUTPUT':ROOT/'art/character_refit_20261023/CHR_Thai_Seam_Bind_V6_20261023.glb',
 'PREP_BIND_LIBRARY':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_V6_20261023.blend',
 'PREP_ARM_SPLAY':.28,'PREP_FOREARM_FORWARD':.28}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
