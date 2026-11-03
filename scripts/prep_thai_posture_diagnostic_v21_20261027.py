"""Save a review library, never import the six rejected posture trials.

The displayed avatar remains the exact V20 standing surface. Face attributes
locate instability of the smallest numerical trial; they are not repairs or
anatomical labels. Only copies receive diagnostic materials/attributes.
"""
import bpy, json, hashlib, shutil, runpy, traceback
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SRC_REPORT = ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_20261027.json'
STUDY = ROOT/'work/qa_thai_posture_v21_20261027'
EXPORT = ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz'
OUTDIR = ROOT/'reports/thai_posture_diagnostic_v21_20261027'
LIB = ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.blend'
CP = ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_POSTURE_DIAGNOSTIC_V21_20261027.blend'
REPORT = ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.json'
STATUS = ROOT/'work/v21_diagnostic_build_status_20261027.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def points(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    v = np.empty(len(mesh.vertices)*3, np.float32)
    mesh.vertices.foreach_get('co', v)
    m = np.array(ev.matrix_world)
    ev.to_mesh_clear()
    return v.reshape(-1,3)@m[:3,:3].T+m[:3,3]

def geom(q, t):
    v = q[t]
    c = np.cross(v[:,1]-v[:,0], v[:,2]-v[:,0])
    a = np.linalg.norm(c, axis=1)
    return c/np.maximum(a[:,None], 1e-30), a*.5

def material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    node = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    node.inputs['Base Color'].default_value = rgba
    node.inputs['Roughness'].default_value = .72
    return mat

def curve(scene, name, pts, mat, radius=.003):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 2
    line = data.splines.new('POLY')
    line.points.add(len(pts)-1)
    for p, xyz in zip(line.points, pts): p.co = (*map(float,xyz),1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    data.materials.append(mat)
    obj.show_in_front = True
    return obj

try:
    assert bpy.app.background and not STATUS.exists()
    assert not any(p.exists() for p in (LIB,CP,REPORT,OUTDIR))
    src = json.loads(SRC_REPORT.read_text())
    study = json.loads((STUDY/'controlled_posture_v21_measurements.json').read_text())
    source = Path(src['library'])
    assert sha(source)==src['sha256']==study['librarySHA256']
    assert study['passingRaisesMeters']==[] and len(study['trials'])==6
    assert sha(EXPORT)==study['sourceSHA256']
    with np.load(EXPORT) as n: data={k:n[k].copy() for k in n.files}
    trials = STUDY/'REJECTED_pose_trials_for_QA_only_v21.npz'
    with np.load(trials) as n:
        assert bool(n['do_not_import']) and int(n['accepted_candidate_count'])==0
        assert float(n['trial_pelvis_raise_meters'][0])==.002
        keys = n.files
        # Read only the smallest numerical experiment for a risk attribute.
        # No trial matrices or posed vertices enter Blender objects.
        trial_keys = [k for k in keys if n[k].shape==(6,len(data['vertices']),3)]
        if len(trial_keys)!=1:
            raise ValueError('Ambiguous rejected-trial array: '+repr([(k,n[k].shape) for k in keys]))
        q2 = n[trial_keys[0]][0].copy()
        qb = n['baseline_posed_world'].copy()
    q, t = data['posed'], data['triangles']
    assert np.linalg.norm(q-qb,axis=1).max()<1e-6
    normal, area = geom(qb,t)
    normal2, area2 = geom(q2,t)
    ratios = np.divide(area2,area,out=np.ones_like(area),where=area>5e-13)
    dots = (normal*normal2).sum(1)
    edges = np.linalg.norm(qb[t]-np.roll(qb[t],-1,axis=1),axis=2)
    edges2 = np.linalg.norm(q2[t]-np.roll(q2[t],-1,axis=1),axis=2)
    er = np.divide(edges2,edges,out=np.ones_like(edges),where=edges>1e-6)
    limits = study['fixedLimits']
    bits = ((ratios<limits['minimumAllFaceAreaRatio']) | (ratios>limits['maximumAllFaceAreaRatio'])).astype(np.int32)
    bits += 2*np.any((er<limits['minimumAllEdgeLengthRatio']) | (er>limits['maximumAllEdgeLengthRatio']),axis=1)
    bits += 4*(dots<limits['minimumAllFaceNormalDotToSameSourceFace'])
    direct = np.flatnonzero(bits)
    assert len(direct)>0
    source_ids = np.array([23904,23988,38884],np.int32)
    # Adjacent faces are a visibility halo, explicitly separate from direct risk.
    risk_vertices = np.unique(t[direct])
    halo = np.any(np.isin(t,risk_vertices),axis=1) & (bits==0)
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    original=bpy.data.objects[src['bodyObject']]
    original_scene=bpy.data.scenes[src['scene']]
    bpy.context.window.scene=original_scene
    bpy.context.view_layer.update()
    snap=helper['_snapshot'](original.data)
    w=helper['_weights'](original.data,len(original.vertex_groups))
    assert {k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in snap['arrays'].items()}==src['bodyArraysSha256']
    assert hashlib.sha256(w.tobytes()).hexdigest()==src['weightsSha256']
    assert np.array_equal(points(original),q)
    shutil.copy2(source,CP)
    OUTDIR.mkdir()
    bpy.ops.wm.save_as_mainfile(filepath=str(LIB),compress=True)
    scenes=[]
    body_names=[]
    gray=material('V21_DIAGNOSTIC_NEUTRAL',(.32,.37,.43,1))
    amber=material('V21_CONTEXT_HALO_NOT_DIRECT_RISK',(.9,.43,.05,1))
    red=material('V21_DIRECT_RISK_REJECTED_2MM_TRIAL',(.8,.025,.025,1))
    cyan=material('V21_ACTUAL_GUIDE_JOINTS',(.01,.6,.95,1))
    orange=material('V21_CONTOUR_PROXIES_NOT_ANATOMICAL',(.95,.3,.02,1))
    for mode in ('BASELINE','RISK'):
        scene=bpy.data.scenes.new('REVIEW_THAI_POSTURE_V21_'+mode)
        scene.world=original_scene.world
        scene['PREP_role']='DIAGNOSTIC_ONLY; unchanged V20 posture; no accepted pose; no runtime promotion'
        scene['PREP_legend']='Red: direct 2mm trial failure; amber: adjacent context only; cyan: actual guide; orange: geometric contour proxy, not anatomical joint'
        arm=original.parent.copy()
        arm.data=original.parent.data.copy()
        arm.name='DIAG_V21_'+mode+'_Rig'
        scene.collection.objects.link(arm)
        arm.show_in_front=True
        body=original.copy()
        body.data=original.data.copy()
        body.name='DIAG_V21_'+mode+'_Avatar'
        scene.collection.objects.link(body)
        body.parent=arm
        body.matrix_basis=original.matrix_basis.copy()
        body.matrix_parent_inverse=original.matrix_parent_inverse.copy()
        next(m for m in body.modifiers if m.type=='ARMATURE').object=arm
        bpy.context.window.scene=scene
        bpy.context.view_layer.update()
        assert not helper['_differences'](snap,helper['_snapshot'](body.data))
        assert np.array_equal(helper['_weights'](body.data,len(body.vertex_groups)),w)
        assert np.array_equal(points(body),q)
        body['PREP_source_sha256']=src['sha256']
        body['PREP_pose_repair_accepted']=False
        body['PREP_native_walk_validated']=False
        if mode=='RISK':
            for name, values in [('prep_v21_risk_2mm_bits',bits),('prep_v21_visibility_halo',halo.astype(np.int32)),('prep_v21_source_face_id',np.arange(len(t),dtype=np.int32))]:
                attr=body.data.attributes.new(name,'INT','FACE')
                attr.data.foreach_set('value',values)
            body.data.materials.clear()
            for mat in (gray,amber,red):body.data.materials.append(mat)
            indices=np.zeros(len(t),np.int32)
            indices[halo]=1
            indices[direct]=2
            body.data.polygons.foreach_set('material_index',indices)
            for face in source_ids:
                marker=bpy.data.objects.new('V21_SOURCE_FACE_'+str(face),None)
                marker.empty_display_type='SPHERE'
                marker.empty_display_size=.009
                marker.location=q[t[face]].mean(0)
                marker.show_in_front=True
                marker['sourceFaceIndex']=int(face)
                marker['semanticStatus']='Uncertified: do not infer skin/cloth from weights or height alone'
                scene.collection.objects.link(marker)
            for side in ('L','R'):
                leg=study['baselineSkeleton'][side]
                guide=curve(scene,'V21_'+side+'_ACTUAL_GUIDE',[leg[x] for x in ('hip','knee','ankle')],cyan)
                guide.hide_render=True  # In-front guide is a viewport diagnostic, no false rendered depth.
                for segment in ('lowerSections','upperSections'):
                    pts=[s['center05to95'] for s in study['baselineSurfaceAxes'][side][segment]]
                    proxy=curve(scene,'V21_'+side+'_'+segment+'_GEOMETRIC_PROXY',pts,orange,.002)
                    proxy.hide_render=True
        camera=bpy.data.objects.new('V21_'+mode+'_Camera',original_scene.camera.data.copy())
        scene.collection.objects.link(camera)
        camera.matrix_world=original_scene.camera.matrix_world.copy()
        scene.camera=camera
        for light in (o for o in original_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
        scenes.append(scene.name)
        body_names.append(body.name)
    note=bpy.data.texts.new('READ_ME_V21_POSTURE_NOT_FIXED.txt')
    note.write('DIAGNOSTIC ONLY — POSTURE NOT FIXED\n\nBoth scenes keep the exact V20 standing surface and rig pose. The RISK copy changes only diagnostic materials and adds attributes. All six pose-only trials were rejected and are NOT imported.\n\nRed faces exceed fixed area/edge/normal gates in the minimum 2mm pelvis experiment. Amber is one-ring visibility context, not direct failure. Source face IDs preserve provenance. Cyan guide and orange contour proxies are in-front viewport aids, hidden in renders to avoid misleading depth. Proxies do not certify anatomical joints.\n\nBaseline height 1.70m and soles on floor are already correct. Current scan/surface still has asymmetric legs, holes and incomplete clothing. Rebind/weights require a separate tested repair. Remy/source/runtime/master remain untouched. GUI/MCP absent; saved through official Blender background alias without visible windows.\n')
    baseline=bpy.data.objects[body_names[0]]
    risk=bpy.data.objects[body_names[1]]
    bpy.context.window.scene=original_scene
    bpy.context.view_layer.update()
    assert not helper['_differences'](snap,helper['_snapshot'](original.data))
    assert np.array_equal(points(original),q)
    bpy.context.window.scene=bpy.data.scenes[scenes[1]]
    bpy.context.view_layer.objects.active=risk
    risk.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(LIB),compress=True)
    attrs=helper['_snapshot'](risk.data)['arrays']
    np.savez_compressed(OUTDIR/'risk_attributes.npz',direct_faces=direct,risk_bits=bits,halo_faces=np.flatnonzero(halo),source_causal_face_ids=source_ids,area_ratio_2mm=ratios,normal_dot_2mm=dots,edge_ratio_2mm=er)
    report={'status':'diagnostic-library-saved-awaiting-reopen-and-preview','library':str(LIB),'sha256':sha(LIB),'source':str(source),'sourceSha256':src['sha256'],'checkpoint':str(CP),'checkpointSha256':sha(CP),'scenes':scenes,'baselineBody':baseline.name,'riskBody':risk.name,'bodyArraysSha256':src['bodyArraysSha256'],'weightsSha256':src['weightsSha256'],'riskBodyArraysSha256':{k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in attrs.items()},'direct2mmRiskFaces':direct.tolist(),'direct2mmRiskFaceCount':len(direct),'contextHaloFaceCount':int(halo.sum()),'sourceCausalFaceIds':source_ids.tolist(),'studySHA256':sha(STUDY/'controlled_posture_v21_measurements.json'),'rejectedNumericTrialsSHA256':sha(trials),'rejectedPoseImported':False,'acceptedPoseCount':0,'baselineGeometryWeightsUVNormalsAndPoseExact':True,'sourcePreserved':True,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,'postureFixed':False,'GUIOpened':False,'MCPUsed':False,'backgroundMode':True,'scope':'Saved diagnostic attributes and viewport markers only. The exact old posture remains; no repair or anatomical-label certification.'}
    assert sha(source)==src['sha256'] and sha(CP)==src['sha256']
    REPORT.write_text(json.dumps(report,indent=2))
    STATUS.write_text(json.dumps({'status':'success','report':str(REPORT)},indent=2))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2))
    raise
