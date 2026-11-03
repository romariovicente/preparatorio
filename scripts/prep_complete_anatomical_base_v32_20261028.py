"""Prepare a complete local body donor on the preserved native 55-bone rig.

The anatomical source/labels, Thai identity and old libraries remain untouched.
This creates a new unapproved skin-base prototype; original outfit work remains.
"""
import bpy,bmesh,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'work/qa_thai_body_completion_v31_20261028'
F=ROOT/'reports/thai_complete_anatomical_base_v32_20261028';OUT=ROOT/'reports/CHARACTER_THAI_COMPLETE_BASE_V32_20261028.json'
STATUS=ROOT/'work/v32_complete_base_status_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as n:return {k:n[k].copy()for k in n.files}
def progress(status,**kwargs):STATUS.write_text(json.dumps({'status':status,**kwargs},indent=2))
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def segment_map(q,s0,s1,t0,t1,radial=.86):
    sy=(s1-s0)/np.linalg.norm(s1-s0);ty=(t1-t0)/np.linalg.norm(t1-t0)
    front=np.array([0.,-1.,0.]);sx=np.cross(sy,front);sx/=np.linalg.norm(sx);sz=np.cross(sx,sy)
    tx=np.cross(ty,front);tx/=np.linalg.norm(tx);tz=np.cross(tx,ty)
    S=np.column_stack([sx,sy,sz]);T=np.column_stack([tx,ty,tz]);D=np.diag([radial,np.linalg.norm(t1-t0)/np.linalg.norm(s1-s0),radial])
    return (q-s0)@(T@D@S.T).T+t0
def topology(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    result={'vertices':len(bm.verts),'edges':len(bm.edges),'faces':len(bm.faces),
        'boundaryEdges':sum(e.is_boundary for e in bm.edges),'nonmanifoldEdges':sum(not e.is_manifold for e in bm.edges),
        'euler':len(bm.verts)-len(bm.edges)+len(bm.faces)}
    seen=set();components=0
    for v in bm.verts:
        if v in seen:continue
        components+=1;todo=[v];seen.add(v)
        while todo:
            a=todo.pop()
            for edge in a.link_edges:
                b=edge.other_vert(a)
                if b not in seen:seen.add(b);todo.append(b)
    result['connectedComponents']=components;bm.free();return result
try:
    assert not OUT.exists() and not F.exists();F.mkdir();progress('checking-sources')
    prior=json.loads((ROOT/'reports/CHARACTER_THAI_COMPLETE_BASE_V31_20261028.json').read_text())
    donor=json.loads((I/'anatomy_female_donor_topology_v31.json').read_text())
    native_report=json.loads((ROOT/'work/qa_thai_original_outfit_v30_20261028/target_surface_and_rig_report.json').read_text())
    assert sha(prior['library'])==prior['sha256'] and sha(donor['analysisNPZ'])==donor['analysisNPZSHA256']
    assert sha(native_report['archive'])==native_report['archiveSha256']
    assert Path(bpy.data.filepath)==Path(prior['library'])and not bpy.data.is_dirty
    cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_COMPLETE_BASE_V32_20261028.blend';assert not cp.exists();shutil.copy2(prior['library'],cp)
    bpy.ops.wm.open_mainfile(filepath=prior['library'],load_ui=False,use_scripts=False)
    staging=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COMPLETE_DERIVED_BASE_V32_WORK_20261028.blend';assert not staging.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(staging),compress=True)
    scene=bpy.data.scenes[prior['scene']];scene.name='REVIEW_THAI_COMPLETE_ANATOMICAL_BASE_V32'
    window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0]
    native=bpy.data.objects['V28_Clinical_Standard_Rig'];avatar=bpy.data.objects['V28_Thai_Clinical_Avatar_Root']
    data=load(donor['analysisNPZ']);target=load(native_report['archive']);names=target['boneNames'].tolist()
    A=target['armWorld'];R=target['boneRestMatrices'];H=(A@R)[:,:3,3];heads={n:H[i]for i,n in enumerate(names)}
    parents=json.loads((ROOT/'reports/CHARACTER_THAI_V28_RESUME_AUDIT_20261028.json').read_text())['currentData']['bones']
    mesh=bpy.data.meshes.new('V32_Derived_Full_Body_Surface');mesh.from_pydata(data['bodyCoords'].tolist(),[],data['bodyT'].tolist());mesh.update()
    obj=bpy.data.objects.new('V32_Complete_Standard_Body_Prototype',mesh);scene.collection.objects.link(obj)
    # Remove the donor's original head, and cap its neck in this separate derived mesh.
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
        plane_co=Vector((0,0,1.645)),plane_no=Vector((0,0,1)),clear_outer=True,clear_inner=False)
    boundary=[e for e in bm.edges if e.is_boundary];assert boundary and all(min(v.co.z for v in e.verts)>1.64 for e in boundary)
    bmesh.ops.holes_fill(bm,edges=boundary,sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    before_fit=topology(mesh);assert before_fit['boundaryEdges']==0 and before_fit['nonmanifoldEdges']==0 and before_fit['connectedComponents']==1
    source=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',source);q=source.reshape(-1,3).astype(float)
    # Explicit fitting landmarks in the donor's source metres. These are modelling guides,
    # not clinical measurements or a claim that anatomical geometry equals final skin.
    sz=np.array([0,.095,.595,1.08,1.12,1.25,1.36,1.47,1.63,1.645])
    nz=np.array([0,heads['mixamorig:LeftFoot'][2],heads['mixamorig:LeftLeg'][2],heads['mixamorig:LeftUpLeg'][2],
        heads['mixamorig:Hips'][2],heads['mixamorig:Spine'][2],heads['mixamorig:Spine1'][2],heads['mixamorig:Spine2'][2],
        heads['mixamorig:Neck'][2],heads['mixamorig:Neck'][2]+.015])
    centerx=np.interp(q[:,2],[0,1.12,1.47,1.63],[-.0063,heads['mixamorig:Hips'][0],heads['mixamorig:Spine2'][0],heads['mixamorig:Neck'][0]])
    centery=np.interp(q[:,2],[0,1.12,1.25,1.36,1.47,1.63],[0,heads['mixamorig:Hips'][1],heads['mixamorig:Spine'][1],heads['mixamorig:Spine1'][1],heads['mixamorig:Spine2'][1],heads['mixamorig:Neck'][1]])
    core=np.column_stack([q[:,0]*.84+centerx,(q[:,1]-.015)*.84+centery,np.interp(q[:,2],sz,nz)])
    fitted=core.copy();landmarks={}
    for sign,prefix in [(1,'Left'),(-1,'Right')]:
        ids=np.flatnonzero(q[:,0]*sign>=0);p=q[ids]
        hip=np.array([sign*.105,.015,1.08]);knee=np.array([sign*.125,.005,.595]);ankle=np.array([sign*.15,.015,.095]);toe=np.array([sign*.15,-.12,.025])
        leg_upper=segment_map(p,hip,knee,heads['mixamorig:'+prefix+'UpLeg'],heads['mixamorig:'+prefix+'Leg'])
        leg_lower=segment_map(p,knee,ankle,heads['mixamorig:'+prefix+'Leg'],heads['mixamorig:'+prefix+'Foot'])
        foot=segment_map(p,ankle,toe,heads['mixamorig:'+prefix+'Foot'],heads['mixamorig:'+prefix+'ToeBase'])
        low=smooth((.64-p[:,2])/.09);footmix=1-smooth((p[:,2]-.065)/.075)
        leg=leg_upper*(1-low[:,None])+leg_lower*low[:,None];leg=leg*(1-footmix[:,None])+foot*footmix[:,None]
        legmix=(1-smooth((p[:,2]-1.00)/.14))*smooth((np.abs(p[:,0])-.012)/.045)
        fitted[ids]=core[ids]*(1-legmix[:,None])+leg*legmix[:,None]
        shoulder=np.array([sign*.20,0,1.515]);elbow=np.array([sign*.365,0,1.285]);wrist=np.array([sign*.49,0,1.075]);handtip=np.array([sign*.56,0,.94])
        upper=segment_map(p,shoulder,elbow,heads['mixamorig:'+prefix+'Arm'],heads['mixamorig:'+prefix+'ForeArm'])
        fore=segment_map(p,elbow,wrist,heads['mixamorig:'+prefix+'ForeArm'],heads['mixamorig:'+prefix+'Hand'])
        t=((p-shoulder)@(elbow-shoulder))/np.sum((elbow-shoulder)**2);foremix=smooth((t-.80)/.40)
        armq=upper*(1-foremix[:,None])+fore*foremix[:,None]
        distances=[]
        for s0,s1 in [(shoulder,elbow),(elbow,wrist),(wrist,handtip)]:
            v=s1-s0;u=np.clip(((p-s0)@v)/(v@v),0,1);distances.append(np.linalg.norm(p-(s0+u[:,None]*v),axis=1))
        arm_distance=np.min(distances,axis=0);armmix=smooth((np.abs(p[:,0])-.13)/.12)*(1-smooth((arm_distance-.075)/.055))
        armmix=np.maximum(armmix,smooth((np.abs(p[:,0])-.30)/.08))
        fitted[ids]=fitted[ids]*(1-armmix[:,None])+armq*armmix[:,None]
        landmarks[prefix]={'hip':hip.tolist(),'knee':knee.tolist(),'ankle':ankle.tolist(),'toe':toe.tolist(),
            'shoulder':shoulder.tolist(),'elbow':elbow.tolist(),'wrist':wrist.tolist(),'handtip':handtip.tolist()}
    assert np.isfinite(fitted).all();mesh.vertices.foreach_set('co',fitted.astype(np.float32).reshape(-1));mesh.update()
    for o in scene.objects:o.select_set(False,view_layer=layer)
    obj.select_set(True,view_layer=layer);layer.objects.active=obj
    progress('reducing-and-softening-derived-body')
    dec=obj.modifiers.new('V32_Derived_Game_Resolution','DECIMATE');dec.ratio=.24;dec.use_collapse_triangulate=True
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.object.modifier_apply(modifier=dec.name)
    lap=obj.modifiers.new('V32_Soft_Skin_Envelope','LAPLACIANSMOOTH');lap.iterations=6;lap.lambda_factor=.35;lap.lambda_border=0;lap.use_volume_preserve=True
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.object.modifier_apply(modifier=lap.name)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    derived_topology=topology(obj.data);assert derived_topology['boundaryEdges']==0 and derived_topology['nonmanifoldEdges']==0 and derived_topology['connectedComponents']==1
    mat=bpy.data.materials.new('V32_Neutral_Personal_Skin_No_Muscle_Labels');mat.use_nodes=True
    def linear(c):return ((c+.055)/1.055)**2.4 if c>.04045 else c/12.92
    color=tuple(linear(c)for c in [.75,.56,.46])+(1,);bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=color
    bsdf.inputs['Roughness'].default_value=.58;bsdf.inputs['Subsurface Weight'].default_value=.06;bsdf.inputs['Subsurface Scale'].default_value=.01
    mat.diffuse_color=color;obj.data.materials.append(mat)
    # Only a temporary heat rig gets practical tails. The native rest/curves stay exact.
    progress('creating-temporary-weighting-rig')
    rd=bpy.data.armatures.new('V32_TEMP_Heat_Rig_Data');heat=bpy.data.objects.new('V32_TEMP_Heat_Rig',rd);scene.collection.objects.link(heat)
    obj.select_set(False,view_layer=layer);heat.select_set(True,view_layer=layer);layer.objects.active=heat
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.object.mode_set(mode='EDIT')
    primary={'Hips':'Spine','Spine':'Spine1','Spine1':'Spine2','Spine2':'Neck','Neck':'Head','Head':'HeadTop_End'}
    for side in ['Left','Right']:
        primary.update({side+'Shoulder':side+'Arm',side+'Arm':side+'ForeArm',side+'ForeArm':side+'Hand',side+'Hand':side+'HandMiddle1',side+'UpLeg':side+'Leg',side+'Leg':side+'Foot',side+'Foot':side+'ToeBase'})
        for digit in ['Thumb','Index','Middle','Ring','Pinky']:
            for number in [1,2]:primary[side+'Hand'+digit+str(number)]=side+'Hand'+digit+str(number+1)
    for name in names:
        short=name.split(':')[-1];bone=rd.edit_bones.new(name);bone.head=Vector(heads[name])
        child='mixamorig:'+primary[short]if short in primary else None
        if child:tail=heads[child].copy()
        elif short.endswith('3')and parents[name]['parent']:
            tail=heads[name]+.7*(heads[name]-heads[parents[name]['parent']])
        elif short.endswith('ToeBase'):
            tail=heads[name]+np.array([0,-.045,0])
        else:tail=heads[name]+np.array([0,0,.025])
        if np.linalg.norm(tail-heads[name])<.004:tail=heads[name]+np.array([0,0,.01])
        bone.tail=Vector(tail);bone.use_deform=not any(x in short for x in ['Eye','Head'])
    for name in names:
        parent=parents[name]['parent']
        if parent:rd.edit_bones[name].parent=rd.edit_bones[parent]
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True,view_layer=layer);layer.objects.active=heat
    progress('bone-heat-binding-complete-body')
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));hw=h['_weights'](obj.data,len(obj.vertex_groups));W=np.zeros((len(obj.data.vertices),55),np.float32)
    for group in obj.vertex_groups:
        assert group.name in names;W[:,names.index(group.name)]=hw[:,group.index]
    total=W.sum(1,dtype=float);assert float(total.min())>1e-8,('unweighted vertices',int((total<=1e-8).sum()))
    W/=total[:,None];heat_raw=W.copy()
    rest_coords=np.empty(len(obj.data.vertices)*3,np.float32);obj.data.vertices.foreach_get('co',rest_coords);rest_coords=rest_coords.reshape(-1,3)
    mid=(heads['mixamorig:LeftUpLeg'][0]+heads['mixamorig:RightUpLeg'][0])/2
    side=rest_coords[:,0]-mid
    isolation=(1-smooth((rest_coords[:,2]-.84)/.08))*smooth((np.abs(side)-.012)/.020)
    leftcols=[i for i,n in enumerate(names)if n.split(':')[-1]in ['LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase']]
    rightcols=[i for i,n in enumerate(names)if n.split(':')[-1]in ['RightUpLeg','RightLeg','RightFoot','RightToeBase']]
    leftrows=np.flatnonzero(side>0);rightrows=np.flatnonzero(side<0)
    W[np.ix_(leftrows,rightcols)]*=1-isolation[leftrows,None]
    W[np.ix_(rightrows,leftcols)]*=1-isolation[rightrows,None]
    assert (W.sum(1)>0).all();W/=W.sum(1)[:,None];region_raw=W.copy()
    top4=np.argpartition(W,-4,axis=1)[:,-4:];limited=np.zeros_like(W)
    np.put_along_axis(limited,top4,np.take_along_axis(W,top4,axis=1),axis=1)
    discarded=1-limited.sum(1,dtype=float);limited/=limited.sum(1)[:,None]
    for mod in list(obj.modifiers):obj.modifiers.remove(mod)
    obj.parent=None;obj.matrix_world=Matrix.Identity(4);obj.vertex_groups.clear()
    for name in names:obj.vertex_groups.new(name=name)
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
    for vertex in bm.verts:
        for j in np.flatnonzero(limited[vertex.index]>0):vertex[deform][int(j)]=float(limited[vertex.index,j])
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    bpy.data.objects.remove(heat,do_unlink=True);bpy.data.armatures.remove(rd)
    obj.parent=avatar;obj.matrix_parent_inverse=avatar.matrix_world.inverted();obj.matrix_world=Matrix.Identity(4)
    skin=obj.modifiers.new('V32_Preserved_Native55_Deformer','ARMATURE');skin.object=native;skin.use_deform_preserve_volume=False
    old=bpy.data.objects['V28_Standard_Clinical_Body_No_Original_Head'];old.hide_render=True;old.hide_set(True,view_layer=layer)
    if bpy.data.objects.get('V31_Complete_Standard_Body_Prototype'):
        previous_body=bpy.data.objects['V31_Complete_Standard_Body_Prototype'];previous_body.hide_render=True;previous_body.hide_set(True,view_layer=layer)
    obj['PREP_complete_body_donor']=str(donor['analysisNPZ']);obj['PREP_no_anatomy_labels_as_skin']=True
    obj['PREP_derived_skin_base_not_final_appearance']=True;obj['PREP_native_rig_and_curves_preserved']=True
    scene['PREP_role']='Complete derived anatomical skin base prototype; original shirt/skirt remain default direction and unfinished'
    scene['PREP_appearance_approved']=False
    idle=bpy.data.actions['Idle.002'];native.animation_data.action=idle;native.animation_data.action_slot=idle.slots[0]
    for track in native.animation_data.nla_tracks:track.mute=True
    scene.frame_set(1);layer.update()
    arrays=h['_snapshot'](obj.data)['arrays'];actualW=h['_weights'](obj.data,55)
    assert np.isfinite(actualW).all() and actualW.min()>=0 and np.max(np.abs(actualW.sum(1,dtype=float)-1))<1e-6 and np.max((actualW>0).sum(1))<=4
    np.savez_compressed(F/'derived_body_bind_v32.npz',restWorld=arrays['coordinates'],triangles=arrays['triangles'],weights55=actualW,
        names55=np.array(names),armWorld=A,boneRest55=R,boneIdle55=target['boneIdleMatrices'],objectWorld=np.eye(4),rawHeatWeights55=heat_raw,rawRegionIsolatedWeights55=region_raw,top4DiscardedMass=discarded,legIsolationFactor=isolation)
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COMPLETE_DERIVED_BASE_V32_20261028.blend';assert not path.exists()
    progress('saving-body-base-checkpoint')
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    result={'status':'complete-body-base-derived-and-bound-awaiting-reopen-and-motion-review','library':str(path),'sha256':sha(path),'scene':scene.name,
        'bodyObject':obj.name,'rig':native.name,'checkpoint':str(cp),'checkpointSha256':sha(cp),'sourceLibrary':prior['library'],'sourceSha256':prior['sha256'],
        'donorReport':str(I/'anatomy_female_donor_topology_v31.json'),'donorReportSha256':sha(I/'anatomy_female_donor_topology_v31.json'),
        'donorAnalysis':donor['analysisNPZ'],'donorAnalysisSha256':donor['analysisNPZSHA256'],'donorSourceHeight':donor['bodyHeightSourceUnits'],
        'donorNeckCutSourceZ':1.645,'sourceBodyHadEyesExcluded':True,'originalDonorHeadRemoved':True,'noMuscleNameTextureOnPlayer':True,
        'sourceFitLandmarks':landmarks,'beforeFitTopology':before_fit,'derivedRestTopology':derived_topology,
        'temporaryHeatRigDeleted':True,'nativeBoneRestOrActionsEdited':False,'maxDroppedWeightMassForFourInfluences':float(discarded.max()),'handWarpFullyAppliedBeyondSourceX':.38,'bilateralLegIsolationApplied':True,'rawWeightsAndDiscardByVertexArchived':True,
        'weightSumMaxError':float(np.abs(actualW.sum(1,dtype=float)-1).max()),'maxInfluences':int((actualW>0).sum(1).max()),
        'preservedFaceHair':True,'originalShirtSkirtPreservedAsWorkPieces':True,'clothingSurfaceDefectsSolved':False,'appearanceApproved':False,
        'motionValidated':False,'GLBExportedOrReimported':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,
        'MCPAvailable':True,'MCPUsed':True,'execution':'Existing project Blender via local MCP; no focus or desktop switch','blenderVersion':bpy.app.version_string,
        'newVisibleWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    assert sha(prior['library'])==prior['sha256'] and sha(donor['analysisNPZ'])==donor['analysisNPZSHA256']
    OUT.write_text(json.dumps(result,indent=2));progress('success',report=str(OUT));print(json.dumps(result))
except BaseException as exc:
    progress('error',error=str(exc),traceback=traceback.format_exc());raise
