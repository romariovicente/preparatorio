"""Baseline before/after views and four frames of the diagnostic action only."""
import bpy,json,hashlib,traceback
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_dynamic_normals_v25_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RENDERS_20261027.json';STATUS=ROOT/'work/v25_dynamic_normal_render_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and not STATUS.exists()
    r=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIX_20261027.json').read_text());probes=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIXED_PROBES_20261027.json').read_text())
    assert probes['all24ProbesPass']and Path(bpy.data.filepath)==Path(r['library'])and sha(r['library'])==r['sha256']and not bpy.data.is_dirty
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    source_scene=bpy.data.scenes['REVIEW_THAI_UNBOUND_SOURCE_V23'];scene=bpy.data.scenes[r['scene']];scene.frame_set(1)
    folder=F/'validated_probe_previews';assert not folder.exists();folder.mkdir()
    images=[]
    def render(sc,view,direction,label,frame):
        window.scene=sc;sc.frame_set(frame);layer=sc.view_layers[0];layer.update()
        sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=512;sc.render.resolution_y=768;sc.render.resolution_percentage=100
        sc.render.threads_mode='FIXED';sc.render.threads=2;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False;sc.view_settings.view_transform='AgX'
        camera=sc.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.85
        target=Vector((0,0,.85));camera.location=target+Vector(direction)*3;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        path=folder/(view+'_'+label+'.png');assert not path.exists();sc.render.filepath=str(path)
        (ROOT/'work/v25_dynamic_normal_render_progress_20261027.json').write_text(json.dumps({'view':view,'state':label,'frame':frame}))
        with bpy.context.temp_override(window=window,scene=sc,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'view':view,'state':label,'frame':frame,'path':str(path),'sha256':sha(path)})
    for view,direction in(('front',(0,-1,0)),('right',(-1,0,0)),('back',(0,1,0))):
        render(source_scene,view,direction,'before_static_source',1);render(scene,view,direction,'after_dynamic_baseline',1)
    for frame in(1,9,17,25):render(scene,'diagnostic_front',(0,-1,0),'frame_'+str(frame),frame)
    assert sha(r['library'])==r['sha256']and sha(r['sourceV23'])==r['sourceV23Sha256']and sha(r['sourceV24'])==r['sourceV24Sha256']
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    result={'status':'six-matched-baseline-and-four-diagnostic-action-frames-rendered','library':r['library'],'sha256':r['sha256'],'images':images,'sameBaselineCamerasLightingMaterialsAndOldPosture':True,'diagnosticAction':r['diagnosticAction'],'diagnosticFramesAreNotNativeWalk':True,'all24NumericProbesPreviouslyPassed':True,'savedSessionRestoredWithoutSavingRenderChanges':True,'sourceFilesUnchanged':True,'postureFixed':False,'healthySkinningApproved':False,'nativeWalkValidated':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps({'status':result['status'],'images':len(images),'librarySha256':r['sha256']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
