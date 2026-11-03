"""Append a separate copy of the validated white uniform/native Remy rig.

The user explicitly selected a standard body with Thai face and hair preserved.
No source Remy file, existing rig, master or runtime is edited.
"""
import bpy,json,hashlib,shutil,traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_clinical_body_v28_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_CLINICAL_BASE_V28_20261027.json';STATUS=ROOT/'work/v28_clinical_base_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not any(p.exists()for p in(F,OUT,STATUS))
    source=Path(bpy.data.filepath);assert source.name=='PREP_CHARACTER_THAI_JOINT_ALIGNMENT_V26_20261027.blend'and not bpy.data.is_dirty
    source_sha=sha(source)
    library=ROOT/'art/blender/libraries/PREP_REMY_WHITE_UNIFORM_SURFACE_VALIDATED_FINAL_20261022.blend'
    assert sha(library)=='59726201c1f5173aa90d1513fcab0ee5d5a4b67c6af597a4766e5c9bbfbeea9d'
    cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_CLINICAL_BODY_V28_20261027.blend';work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_CLINICAL_BODY_V28_WORK_20261027.blend'
    assert not cp.exists()and not work.exists();shutil.copy2(source,cp);F.mkdir()
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    wanted='PREP_REMY_WHITE_UNIFORM_SURFACE_REIMPORT_FINAL_20261022'
    with bpy.data.libraries.load(str(library),link=False)as(a,b):assert wanted in a.scenes;b.scenes=[wanted]
    scene=b.scenes[0];scene.name='PREP_THAI_CLINICAL_STANDARD_BODY_V28';window.scene=scene;layer=scene.view_layers[0];layer.update()
    rigs=[o for o in scene.objects if o.type=='ARMATURE'];assert len(rigs)==1;arm=rigs[0]
    originals={o.name:o.name for o in scene.objects}
    for obj in scene.objects:obj['V28_original_source_name']=obj.name
    arm.name='V28_Clinical_Standard_Rig'
    names=list(arm.data.bones.keys());assert len(names)==55
    clips={};nla=[]
    if arm.animation_data:
        for track in arm.animation_data.nla_tracks:
            for strip in track.strips:
                row={'track':track.name,'strip':strip.name,'action':strip.action.name if strip.action else None,'actionRange':list(strip.action.frame_range)if strip.action else None,'slot':strip.action_slot.identifier if hasattr(strip,'action_slot')and strip.action_slot else None};nla.append(row)
                for label in('Idle','Walk','Dance','Interact'):
                    if strip.action and (track.name.split('.')[0]==label or strip.name.split('.')[0]==label or strip.action.name.split('.')[0]==label):clips[label]=strip.action
            track.mute=True
        if arm.animation_data.action:
            action=arm.animation_data.action
            for label in('Idle','Walk','Dance','Interact'):
                if action.name.split('.')[0]==label:clips.setdefault(label,action)
    assert set(clips)=={'Idle','Walk','Dance','Interact'},nla
    idle=clips['Idle'];arm.animation_data.action=idle
    if idle.slots:arm.animation_data.action_slot=idle.slots[0]
    scene.frame_set(int(idle.frame_range[0]));layer.update()
    def meshinfo(obj):
        ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);q=v.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
        return {'name':obj.name,'originalName':obj['V28_original_source_name'],'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),'bounds':None if len(q)==0 else[q.min(0).tolist(),q.max(0).tolist()],'materials':[m.name for m in obj.data.materials],'parent':obj.parent.name if obj.parent else None,'groups':list(obj.vertex_groups.keys()),'modifiers':[m.type for m in obj.modifiers],'hideRender':obj.hide_render,'hideViewport':obj.hide_viewport}
    meshes=[meshinfo(obj)for obj in scene.objects if obj.type=='MESH']
    bones=[{'name':n,'parent':arm.data.bones[n].parent.name if arm.data.bones[n].parent else None,'restHeadArmature':list(arm.data.bones[n].head_local),'restTailArmature':list(arm.data.bones[n].tail_local),'restHeadWorld':list(arm.matrix_world@arm.data.bones[n].head_local),'restTailWorld':list(arm.matrix_world@arm.data.bones[n].tail_local)}for n in names if any(x in n.lower()for x in('head','neck','spine2'))]
    scene['PREP_role']='Standard clinical body prototype, user approved strategy. Thai head/hair not attached yet. Native Remy originals preserved.'
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    result={'status':'separate-white-clinical-body-copy-loaded-head-not-attached-yet','library':str(work),'sha256':sha(work),'checkpoint':str(cp),'checkpointSha256':sha(cp),'priorThaiSource':str(source),'priorThaiSourceSha256':source_sha,'whiteUniformSourceLibrary':str(library),'whiteUniformSourceLibrarySha256':sha(library),'scene':scene.name,'rig':arm.name,'boneCount':len(names),'boneNames':names,'rigWorld':np.array(arm.matrix_world).tolist(),'headNeckBones':bones,'clips':{k:{'action':v.name,'range':list(v.frame_range),'slots':[s.identifier for s in v.slots]}for k,v in clips.items()},'nativeNLASource':nla,'meshes':meshes,'strategyExplicitlyChosenByUser':True,'originalRemyOrPriorThaiFilesModified':False,'headIdentityAttached':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    assert sha(source)==source_sha and sha(cp)==source_sha and sha(library)=='59726201c1f5173aa90d1513fcab0ee5d5a4b67c6af597a4766e5c9bbfbeea9d'
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps({'status':result['status'],'rig':arm.name,'bones':len(names),'clips':list(clips),'meshCount':len(meshes)}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
