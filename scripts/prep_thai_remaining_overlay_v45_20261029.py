"""Install static diagnostic face labels on a copy; no geometry or weights solve."""
import bpy,json,hashlib,runpy,sys,types
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json'
assert not OUT.exists()
stage=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_V45_STAGE_20261029.json').read_text())
F=ROOT/'reports/thai_remaining_review_v45_20261029';assert not F.exists();F.mkdir()
maskpath=ROOT/'work/probe_thai_remaining_failures_v45_20261029/remaining_failure_masks_v45.npz'
classification=ROOT/'work/probe_thai_remaining_failures_v45_20261029/remaining_failure_classification_v45.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(maskpath)=='2f6d094797ce6e66fdaf6e0cb04555e2916ab268571ae1007d0260554d3cf51c'
assert sha(classification)=='d62bcead92b49bfb5823dca80c5bb7cf4771a86236c9d4f8078f2e57538e3451'
assert Path(bpy.data.filepath)==Path(stage['working']) and sha(stage['working'])==stage['workingSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
with np.load(maskpath) as z:
    T=z['triangles'];masks={k:z[k].copy() for k in ['relativeFailureFaceMask','absoluteAreaNormalFailureFaceMask','fanFailureFaceMask','union_global']}
source=bpy.data.objects[stage['sourceBody']]
module=sys.modules['preparatorio_review_v44'];module._verify_bind(source,module._candidate())
assert np.array_equal(h['_snapshot'](source.data)['arrays']['triangles'],T)
assert all(v.shape==(len(T),) and v.dtype==np.bool_ for v in masks.values())
assert np.array_equal(masks['union_global'],masks['relativeFailureFaceMask']|masks['absoluteAreaNormalFailureFaceMask']|masks['fanFailureFaceMask'])
body=source.copy();body.data=source.data.copy();body.name='V45_Remaining_Surface_Review_Actor';body.data.name='V45_Remaining_Surface_Labels_Mesh'
source.users_collection[0].objects.link(body)
body.modifiers[1].node_group=body.modifiers[1].node_group.copy()
source['PREP_interactive_pose_review_v44']=False;source.hide_set(True);source.hide_render=True
body['PREP_interactive_pose_review_v44']=True;body['PREP_diagnostic_remaining_v45']=True
body['PREP_v45_static_union_all_eight_poses']=True;body['PREP_v45_mask_archive_sha256']=sha(maskpath)
body.hide_set(False);body.hide_render=False
for obj in bpy.context.selected_objects:obj.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
attrs={}
for short,key in [('Relative','relativeFailureFaceMask'),('AreaNormal','absoluteAreaNormalFailureFaceMask'),('Fan','fanFailureFaceMask'),('Any','union_global')]:
    name='V45_Remaining_'+short;attribute=body.data.attributes.new(name=name,type='BOOLEAN',domain='FACE');attribute.data.foreach_set('value',masks[key]);attrs[short]=name
    body['PREP_v45_count_'+short]=int(masks[key].sum())
count=masks['relativeFailureFaceMask'].astype(np.int8)+masks['absoluteAreaNormalFailureFaceMask'].astype(np.int8)+masks['fanFailureFaceMask'].astype(np.int8)
colors=np.tile(np.array([.38,.38,.38,1],np.float32),(len(T),1))
colors[masks['relativeFailureFaceMask']]=[.95,.025,.015,1]
colors[masks['absoluteAreaNormalFailureFaceMask']]=[1,.32,.01,1]
colors[masks['fanFailureFaceMask']]=[.38,.025,.8,1]
colors[count>=2]=[.015,.7,1,1]
corner=np.repeat(colors,3,axis=0)
assert len(body.data.polygons)==len(T) and len(body.data.loops)==len(corner)
colorname='V45_Remaining_Union_Diagnostic_Color'
color=body.data.color_attributes.new(name=colorname,type='FLOAT_COLOR',domain='CORNER');color.data.foreach_set('color',corner.reshape(-1));body.data.color_attributes.active_color=color
body.data.polygons.foreach_set('select',masks['union_global']);body.data.update()
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;space.shading.type='SOLID';space.shading.color_type='VERTEX';space.overlay.show_extras=False
        space.region_3d.view_location=(0,0,1.19);space.region_3d.view_distance=1.28
        next(r for r in area.regions if r.type=='UI').active_panel_category='Preparatório';area.tag_redraw()
LEGEND='''import bpy
class PREP45_PT_RemainingReview(bpy.types.Panel):
    bl_label='Áreas a revisar'
    bl_idname='PREP45_PT_RemainingReview'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='Preparatório'
    @classmethod
    def poll(cls,context):
        return any(o.get('PREP_diagnostic_remaining_v45',False) and o.get('PREP_interactive_pose_review_v44',False) for o in context.scene.objects)
    def draw(self,context):
        box=self.layout.box();box.label(text='União das oito poses de estudo')
        box.label(text='Vermelho: diferença entre posturas')
        box.label(text='Laranja: área ou orientação')
        box.label(text='Roxo: vizinhança da superfície')
        box.label(text='Ciano: mais de um dos critérios')
        self.layout.label(text='As cores são marcações estáticas.')
        self.layout.label(text='Superfície e roupas ainda em revisão.',icon='INFO')
def register():
    old=getattr(bpy.types,'PREP45_PT_RemainingReview',None)
    if old is not None:bpy.utils.unregister_class(old)
    bpy.utils.register_class(PREP45_PT_RemainingReview)
if __name__=='__main__':register()
'''
textname='PREPARATORIO_V45_DIAGNOSTIC_LEGEND_EXPLICIT_RUN.py'
text=bpy.data.texts.new(textname);text.write(LEGEND);text.use_module=False
legend=types.ModuleType('preparatorio_remaining_v45');exec(compile(LEGEND,textname,'exec'),legend.__dict__);sys.modules[legend.__name__]=legend;legend.register()
scene['PREP_v45_role']='Static diagnostic union of all eight sampled poses; colors do not change with displayed pose. No new corrective solve or clothing.'
module.apply_sample(scene,'Idle',101,'corrected','study')
library=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.blend';assert not library.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(library),compress=True)
saved=sha(library);bodyname=body.name
bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[stage['scene']];window.scene=scene;layer=scene.view_layers[0];body=bpy.data.objects[bodyname]
code=bpy.data.texts['PREPARATORIO_V44_REVIEW_CONTROLS_EXPLICIT_RUN.py'].as_string()
assert hashlib.sha256(code.encode()).hexdigest()=='7c9cca3ebcf3f85522caeb3986c79aecead4c4cf21d8ee51ccb08df4d82c8929'
module=types.ModuleType('preparatorio_review_v44');sys.modules[module.__name__]=module;exec(compile(code,'<saved_v44_controller>','exec'),module.__dict__);module.register()
assert bpy.data.texts[textname].as_string()==LEGEND and not bpy.data.texts[textname].use_module
legend=types.ModuleType('preparatorio_remaining_v45');sys.modules[legend.__name__]=legend;exec(compile(LEGEND,textname,'exec'),legend.__dict__);legend.register()
arrays=h['_snapshot'](body.data)['arrays'];W=h['_weights'](body.data,55);names=list(body.vertex_groups.keys())
module._verify_bind(body,module._candidate())
assert np.array_equal(arrays['triangles'],T)
archive={'actualRestWorld':arrays['coordinates'],'actualTriangles':arrays['triangles'],'actualWeights55':W,'actualNames55':np.asarray(names),
 'actualBoneRest55':np.array([np.array(bpy.data.objects[stage['nativeRig']].data.bones[n].matrix_local) for n in names]),
 'actualPoseRigBoneRest55':np.array([np.array(bpy.data.objects[stage['poseRig']].data.bones[n].matrix_local) for n in names])}
for short,name in attrs.items():
    values=np.empty(len(T),np.bool_);body.data.attributes[name].data.foreach_get('value',values)
    assert np.array_equal(values,masks[{'Relative':'relativeFailureFaceMask','AreaNormal':'absoluteAreaNormalFailureFaceMask','Fan':'fanFailureFaceMask','Any':'union_global'}[short]])
    archive['actualFace'+short+'Mask']=values
actual_colors=np.empty(corner.size,np.float32);body.data.color_attributes[colorname].data.foreach_get('color',actual_colors)
assert np.array_equal(actual_colors.reshape(-1,4),corner);archive['actualCornerColors']=actual_colors.reshape(-1,4)
def points(obj):
    layer.update();ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
cases=[]
with np.load(stage['sourceV44Cases']) as ref:
    for clip,frame in [('Idle',101),('Walk',19)]:
        for branch in ['native','corrected']:
            for variant in ['base','study']:
                scene['PREP_review_settings_guard']=True
                scene.prep44_branch=branch;scene.prep44_variant=variant;scene['PREP_review_settings_guard']=False
                assert bpy.ops.preparatorio.review_pose_sample_v44(clip=clip,sample_frame=frame)=={'FINISHED'}
                key=f'{clip}_{frame}_{branch}_{variant}Q';q=points(body);assert np.array_equal(q,ref[key]),key;archive[key]=q
                cases.append({'key':key,'pointsBitExactToV44':True,'frame':scene.frame_current,'targetArmature':body.modifiers[0].object.name,'GNenabled':body.modifiers[1].show_viewport,'rigActions':[bpy.data.objects[n].animation_data.action.name for n in [stage['nativeRig'],stage['poseRig']]],'rigSlots':[bpy.data.objects[n].animation_data.action_slot.identifier for n in [stage['nativeRig'],stage['poseRig']]]})
scene['PREP_review_settings_guard']=True;scene.prep44_branch='corrected';scene.prep44_variant='study';scene['PREP_review_settings_guard']=False
assert bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)=={'FINISHED'}
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
assert sha(stage['source'])==stage['sourceSha256'] and sha(library)==saved
ar=F/'actual_reopened_remaining_review_v45.npz';np.savez_compressed(ar,**archive)
result={'status':'STATIC_REMAINING_FACE_OVERLAY_SAVED_REOPENED_EIGHT_CONTROL_STATES','library':str(library),'sha256':saved,'actor':bodyname,'scene':scene.name,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],'sourceLibrary':stage['source'],'sourceLibrarySha256':stage['sourceSha256'],'maskArchive':str(maskpath),'maskArchiveSha256':sha(maskpath),'classificationReport':str(classification),'classificationReportSha256':sha(classification),'archive':str(ar),'archiveSha256':sha(ar),'colorAttribute':colorname,'colorDomain':'CORNER','maskAttributes':attrs,'faceCounts':{key:int(mask.sum()) for key,mask in masks.items()},'overlapFaceCount':int((count>=2).sum()),'legendTextBlock':textname,'legendTextSha256':hashlib.sha256(LEGEND.encode()).hexdigest(),'legendUseModule':False,'explicitRegistrationAfterReopen':True,'legendRNARegistered':hasattr(bpy.types,'PREP45_PT_RemainingReview'),'controllerRNAIdentifier':bpy.ops.preparatorio.review_pose_sample_v44.get_rna_type().identifier,'cases':cases,'allSourceGeometry55WeightsRestAnd2200CurvesPreserved':True,'newGeometryCorrection':False,'newSolverExecuted':False,'staticUnionNotPoseSpecific':True,'poseQualityApproved':False,'clothesApproved':False,'GLBApproved':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
OUT.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
