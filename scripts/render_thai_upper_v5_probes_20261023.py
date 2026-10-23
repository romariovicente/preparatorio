from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/render_thai_upper_probes_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_V5_20261023.blend',
 'PREP_BIND_REPORT':ROOT/'reports/CHARACTER_THAI_UPPER_BIND_V5_20261023.json',
 'PREP_FOLDER':ROOT/'reports/thai_upper_refit_v5_20261023',
 'PREP_OUT':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_V5_PROBES_20261023.blend',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_UPPER_V5_VISUAL_PROBES_20261023.json'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
