"""Finalize disk manifests after the independent Blender read-back passed."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
delivery = json.loads((ROOT/"reports/BLENDER_ENTREGA_20261015.json").read_text(encoding="utf-8"))
assert delivery["savedFileReadBack"]["validated"] and delivery["savedFileReadBack"]["storedObjectChannelsMatchLive"]
master = ROOT/"art/blender/PREPARATORIO_PROJETO_20261015.blend"
before = master.stat()
assert before.st_size == delivery["savedFileReadBack"]["fileBytes"]
def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8*1024*1024):
            value.update(chunk)
    return value.hexdigest()
master_hash = digest(master)
after = master.stat()
assert (before.st_size,before.st_mtime_ns) == (after.st_size,after.st_mtime_ns), "Master changed during hashing."
assets = []
for relative in ("frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb",
                 "frontend/public/assets/new-delivery/VEH_Bus_BRT_Interactive_20261009.glb"):
    path = ROOT/relative
    assets.append({"path":relative,"bytes":path.stat().st_size,"sha256":digest(path),"generatedEarlier":True})
manifest = {"verifiedAtLocal":datetime.now().astimezone().isoformat(timespec="seconds"),
            "master":{"path":str(master),"bytes":after.st_size,"sha256":master_hash,"unchangedDuringHashing":True},
            "preservedRuntimeGlbs":assets}
(ROOT/"reports/FILE_MANIFEST_20261015.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
plan_path = ROOT/"reports/PLANO_MACRO_20261014.json"
plan = json.loads(plan_path.read_text(encoding="utf-8"))
if "initialAuditState" not in plan:
    plan["initialAuditState"] = {"status":plan["status"],"sourceConfigSha256":plan["sourceConfigSha256"],
                                "centerlineTotalMeters":plan["roadMeasures"]["centerlineTotalMeters"],"openIssues":plan["openIssues"]}
plan["status"] = "saved-and-visually-reviewed; inactive planning prototype"
plan["updatedAtLocal"] = manifest["verifiedAtLocal"]
plan["sourceConfigSha256"] = digest(ROOT/"frontend/src/config/macroWorldPlan.json")
plan["roadMeasures"]["centerlineTotalMeters"] = 38125
plan["roadMeasures"]["peripheralRingMeters"] = 14800
plan["openIssues"] = [issue for issue in plan["openIssues"] if issue["id"] not in ("coastal-road-crossing","render-and-save")]
plan["resolvedIssues"] = [{"id":"coastal-road-crossing","status":"resolved in inactive prototype","evidence":"reports/BLENDER_COAST_20261015.json"},
                          {"id":"render-and-save","status":"saved, reviewed and independently read back","evidence":"reports/BLENDER_ENTREGA_20261015.json"}]
plan["verification"]["scope"] = "Configuration tests, live object preservation, render review and saved persistent object channels; no gameplay macro trip, traffic, performance or regulatory certification."
plan["blockoutExecution"]["status"] = "saved-and-visually-reviewed-inactive-prototype"
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
report_path = ROOT/"reports/ENTREGA_20261015.md"
text = report_path.read_text(encoding="utf-8")
text += "\n## Leitura independente concluída\n\nO master salvo abriu em outra instância do Blender, sem executar scripts embutidos. Foram confirmados 44 cenas, 12.917 objetos e os dois rigs de 55 ossos. Os canais persistentes de transformação, inversas de parentesco, vínculos, ações e visibilidade global dos 12.517 objetos anteriores coincidiram exatamente com a sessão aberta. O cache avaliado de `matrix_world` difere entre as sessões; esse hash não foi apresentado como prova de igualdade da releitura. A comparação não certifica conteúdo interno de todos os datablocks nem ocultação específica de cada view layer.\n\nMaster: **"+str(after.st_size)+" bytes**; SHA-256: `"+master_hash+"`. O arquivo permaneceu estável durante o cálculo. Ver `FILE_MANIFEST_20261015.json`.\n"
report_path.write_text(text,encoding="utf-8")
print(json.dumps({"manifest":"reports/FILE_MANIFEST_20261015.json","masterBytes":after.st_size,"masterSha256":master_hash}))
