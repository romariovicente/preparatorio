from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];script=ROOT/'scripts/forecast_thai_upper_pose_20261023.py'
ns={'__file__':str(script),'__name__':'__main__','PREP_FOLDER':ROOT/'reports/thai_upper_refit_v4_20261023'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
