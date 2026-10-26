"""Actual GLB reimport of the local seam-area draft, including head15 probe."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'scripts/validate_thai_standing_seams_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_AREA_V12_20261026.blend',
 'PREP_OUT':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_AREA_V12_PROBES_20261026.blend',
 'PREP_FOLDER':ROOT/'reports/thai_seam_area_v12_20261026',
 'PREP_SOURCE_REPORT':ROOT/'reports/CHARACTER_THAI_SEAM_AREA_V12_20261026.json',
 'PREP_QA_SCENE':'VALIDATE_THAI_SEAM_AREA_BIND_V12_20261026',
 'PREP_EXTRA_HEAD_TURN':True,
 'PREP_SCOPE':'local-white-garment-seam-area-repair-not-full-character-or-Walk',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_SEAM_AREA_V12_REIMPORT_20261026.json'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
