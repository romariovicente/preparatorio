"""Local garment-seam area repair in exactly the existing V3 review pose."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
candidate=ROOT/'work/qa_thai_seam_area_v12_20261026/candidate_weights_v12.npz'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='08a5b68b88c6f41982388d96351ef7e32af63a48f872eec1f44ecdd2a8b7751e'
qa=ROOT/'work/qa_thai_v12_review_20261026/candidate_08a5b68b88c6_audit.json'
assert qa.is_file(), 'Independent candidate audit must exist before applying the staged trial.'
review=json.loads(qa.read_text(encoding='utf-8'))
assert all(review['checks'].values()) and all(review['qualityGates'].values()), 'Independent gates must pass without exceptions.'
script=ROOT/'scripts/prep_thai_standing_pilot_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_AREA_V12_20261026.blend',
 'PREP_FOLDER':ROOT/'reports/thai_seam_area_v12_20261026',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_SEAM_AREA_V12_20261026.json',
 'PREP_WEIGHTS':ROOT/'work/qa_thai_seam_area_v12_20261026/candidate_weights_v12.npz',
 'PREP_BIND_OUTPUT':ROOT/'art/character_refit_20261023/CHR_Thai_Seam_Area_Bind_V12_20261026.glb',
 'PREP_BIND_LIBRARY':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_AREA_BIND_V12_20261026.blend',
 'PREP_SOURCE_DESCRIPTION':'PREP_CHARACTER_THAI_GARMENT_BIND_V11_20261023.blend',
 'PREP_ARM_SPLAY':.28,'PREP_FOREARM_FORWARD':.28,'PREP_EXTRA_CLOSEUPS':True}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
