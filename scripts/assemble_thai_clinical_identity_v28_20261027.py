"""User-approved standard body, with Thai face/hair preserved on a rigid head attachment."""
import bpy,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_clinical_body_v28_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_CLINICAL_IDENTITY_V28_20261027.json';STATUS=ROOT/'work/v28_clinical_identity_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and not STATUS.exists()
    base=json.loads((ROOT/'reports/CHARACTER_THAI_CLINICAL_BASE_V28_20261027.json').read_text());work=Path(base['library'])
    assert Path(bpy.data.filepath)==work and sha(work)==base['sha256']and not bpy.data.is_dirty
    mask_path=ROOT/'work/qa_thai_head_identity_v28_20261027/head_identity_face_mask_v28.npz'
    assert sha(mask_path)=='e485a4ee9bd6b8fb847cd5af52575de42492d52107e59ea0c34dcf920bf87718'
    cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_HEAD_ATTACHMENT_V28_20261027.blend';assert not cp.exists();shutil.copy2(work,cp)
    with np.load(mask_path)as n:mask={k:n[k].copy()for k in n.files}
    with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:thai={k:n[k].copy()for k in n.files}
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    source_thai=bpy.data.objects['V23_UNBOUND_World_Baseline_Source'];sa=h['_snapshot'](source_thai.data)['arrays']
    assert np.array_equal(sa['triangles'],thai['triangles'])
    scene=bpy.data.scenes[base['scene']];window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[base['rig']];idle=bpy.data.actions[base['clips']['Idle']['action']]
    arm.animation_data.action=idle;arm.animation_data.action_slot=idle.slots[0]
    for track in arm.animation_data.nla_tracks:track.mute=True
    bind_frame=int(idle.frame_range[0]);scene.frame_set(bind_frame);layer.update()
    def evaluated(obj):
        ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();a=h['_snapshot'](mesh)['arrays'];M=np.array(ev.matrix_world)
        q=a['coordinates']@M[:3,:3].T+M[:3,3];d=a['cornerNormals'].astype(float)@np.linalg.inv(M[:3,:3]);d/=np.linalg.norm(d,axis=1)[:,None];ev.to_mesh_clear();return q,d
    head_bone=next(n for n in arm.data.bones.keys()if n.replace(':','').lower()=='mixamorighead')
    neck_bone=next(n for n in arm.data.bones.keys()if n.replace(':','').lower()=='mixamorigneck')
    neck_world=arm.matrix_world@arm.evaluated_get(layer.depsgraph).pose.bones[neck_bone].head
    with np.load(ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz')as n:
        index=n['group_names'].tolist().index('neck');source_neck=n['bone_pose_heads'][index]@n['arm_world'][:3,:3].T+n['arm_world'][:3,3]
    delta=np.array(neck_world)-source_neck
    # Hide only the imported original identity meshes in this local body copy.
    hidden=[]
    for obj in scene.objects:
        original=obj.get('V28_original_source_name','').split('.')[0]
        if original in('Hair','Eyes','Eyelashes'):
            obj.hide_render=True;obj.hide_set(True,view_layer=layer);obj['V28_export_excluded']=True;hidden.append(obj.name)
    original_body=next(o for o in scene.objects if o.type=='MESH'and o.get('V28_original_source_name','').split('.')[0]=='Body')
    ba=h['_snapshot'](original_body.data)['arrays'];bw=h['_weights'](original_body.data,len(original_body.vertex_groups))
    bodyq,_=evaluated(original_body);bt=ba['triangles'];centers=bodyq[bt].mean(1)
    # Native shoulders/hands remain; the old face above the collar is removed.
    remove=np.flatnonzero(centers[:,2]>float(neck_world.z)+.012)
    keep=np.flatnonzero(centers[:,2]<=float(neck_world.z)+.012);assert len(remove)>100 and len(keep)>100
    def subset_mesh(name,positions,triangles,face_ids,arrays,normal_values=None):
        used=np.unique(triangles[face_ids]);mapping=np.full(len(positions),-1,np.int32);mapping[used]=np.arange(len(used));loops=(face_ids[:,None]*3+np.arange(3)).reshape(-1)
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(positions[used].tolist(),[],mapping[triangles[face_ids]].tolist());mesh.update()
        mesh.polygons.foreach_set('use_smooth',arrays['polygonSmooth'][face_ids]);mesh.polygons.foreach_set('material_index',arrays['polygonMaterial'][face_ids])
        for key,v in arrays.items():
            if key.startswith('uv:'):
                uv=mesh.uv_layers.new(name=key[3:]);uv.data.foreach_set('uv',v[loops].reshape(-1))
        if normal_values is not None:mesh.normals_split_custom_set(normal_values[loops].tolist())
        return mesh,used,loops
    clean_mesh,body_used,body_loops=subset_mesh('V28_Standard_Body_Head_Removed',ba['coordinates'],bt,keep,ba,ba['cornerNormals'])
    for material in original_body.data.materials:clean_mesh.materials.append(material)
    import bmesh
    bm=bmesh.new();bm.from_mesh(clean_mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
    for v in bm.verts:
        for gi in np.flatnonzero(bw[body_used[v.index]]>0):v[deform][int(gi)]=float(bw[body_used[v.index],gi])
    bm.to_mesh(clean_mesh);bm.free();clean_mesh.update();clean_mesh.normals_split_custom_set(ba['cornerNormals'][body_loops].tolist())
    clean=original_body.copy();clean.data=clean_mesh;clean.name='V28_Standard_Clinical_Body_No_Original_Head';clean.animation_data_clear();scene.collection.objects.link(clean)
    original_body.hide_render=True;original_body.hide_set(True,view_layer=layer);original_body['V28_export_excluded']=True;hidden.append(original_body.name)
    head_faces=mask['face_indices_to_keep'];assert np.isin(mask['face_identity_faces'],head_faces).all()and np.isin(mask['hair_faces_below_cut_plane'],head_faces).all()
    head_mesh,head_used,head_loops=subset_mesh('V28_Thai_Identity_Head_Mesh',thai['posedWorld'],thai['triangles'],head_faces,sa,thai['evaluatedCornerNormalsWorld'])
    for material in source_thai.data.materials:head_mesh.materials.append(material)
    head=bpy.data.objects.new('V28_Thai_Face_And_Hair_Preserved',head_mesh);scene.collection.objects.link(head)
    normal_attr=head_mesh.attributes.new('V28_identity_corner_normal','FLOAT_VECTOR','CORNER');normal_attr.data.foreach_set('vector',thai['evaluatedCornerNormalsWorld'][head_loops].astype(np.float32).reshape(-1))
    ng=bpy.data.node_groups.new('V28_Rigid_Head_Static_Local_Normals','GeometryNodeTree');ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    ni=ng.nodes.new('NodeGroupInput');no=ng.nodes.new('NodeGroupOutput');na=ng.nodes.new('GeometryNodeInputNamedAttribute');na.data_type='FLOAT_VECTOR';na.inputs['Name'].default_value=normal_attr.name
    sn=ng.nodes.new('GeometryNodeSetMeshNormal');sn.mode='FREE';sn.domain='CORNER';ng.links.new(ni.outputs['Geometry'],sn.inputs['Mesh']);ng.links.new(na.outputs['Attribute'],sn.inputs['Custom Normal']);ng.links.new(sn.outputs['Mesh'],no.inputs['Geometry'])
    gn=head.modifiers.new('Preserved_Local_Identity_Normals','NODES');gn.node_group=ng
    head.parent=arm;head.parent_type='BONE';head.parent_bone=head_bone;head.matrix_parent_inverse=Matrix.Identity(4);head.matrix_basis=Matrix.Identity(4);layer.update()
    parent_world=head.evaluated_get(layer.depsgraph).matrix_world.copy();desired=Matrix.Translation(Vector(delta));head.matrix_parent_inverse=parent_world.inverted()@desired;layer.update()
    hq,hn=evaluated(head);expected=thai['posedWorld'][head_used]+delta
    bind_error=float(np.linalg.norm(hq-expected,axis=1).max());assert bind_error<5e-5,bind_error
    # One shared scale/ground adjustment preserves all native body-relative motion.
    avatar=bpy.data.objects.new('V28_Thai_Clinical_Avatar_Root',None);scene.collection.objects.link(avatar)
    roots=[o for o in scene.objects if o is not avatar and o.parent is None and o.type not in('CAMERA','LIGHT')]
    for obj in roots:
        M=obj.matrix_world.copy();obj.parent=avatar;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_world=M
    layer.update()
    visible=[o for o in scene.objects if o.type=='MESH'and not o.hide_render]
    allq=np.concatenate([evaluated(o)[0]for o in visible]);minimum=float(allq[:,2].min());maximum=float(allq[:,2].max());factor=1.70/(maximum-minimum)
    avatar.matrix_world=Matrix.Translation((0,0,-minimum*factor))@Matrix.Diagonal((factor,factor,factor,1));layer.update()
    qfinal=np.concatenate([evaluated(o)[0]for o in visible]);height=float(np.ptp(qfinal[:,2]));minz=float(qfinal[:,2].min());assert abs(height-1.70)<1e-4 and abs(minz)<1e-4
    scene['PREP_role']='User-approved standard clinical body + preserved Thai identity prototype; native clip validation pending'
    head['PREP_identity_face_count']=len(mask['face_identity_faces']);head['PREP_hair_below_neck_preserved']=True;head['PREP_rigid_head_attachment']=True
    clean['PREP_native_Remy_weights_unchanged_on_retained_vertices']=True
    np.savez_compressed(F/'head_and_body_extraction_provenance.npz',headSourceFaceIndices=head_faces,headSourceVertexIndices=head_used,headSourceLoopIndices=head_loops,bodyKeptSourceFaces=keep,bodyRemovedSourceFaces=remove,bodyKeptSourceVertices=body_used,bodySourceWeights=bw,sourceHeadPositions=thai['posedWorld'][head_used],sourceHeadCornerNormals=thai['evaluatedCornerNormalsWorld'][head_loops],bindTranslation=delta,bindHeadWorldMatrix=np.array(head.matrix_world),avatarRootMatrix=np.array(avatar.matrix_world))
    for obj in scene.objects:obj.select_set(False,view_layer=layer)
    head.select_set(True,view_layer=layer);layer.objects.active=head
    camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.9;target=Vector((0,0,.85));camera.location=Vector((0,-3,.85));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                sp=area.spaces.active;sp.region_3d.view_location=target;sp.region_3d.view_distance=2.2;sp.region_3d.view_rotation=camera.rotation_euler.to_quaternion();sp.region_3d.view_perspective='ORTHO'
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    assert sha(base['whiteUniformSourceLibrary'])==base['whiteUniformSourceLibrarySha256']and sha(cp)==base['sha256']
    result={'status':'standard-white-body-with-preserved-Thai-face-hair-assembled-awaiting-render-and-native-walk-QA','library':str(work),'sha256':sha(work),'checkpoint':str(cp),'checkpointSha256':sha(cp),'scene':scene.name,'rig':arm.name,'avatarRoot':avatar.name,'headObject':head.name,'bodyObject':clean.name,'headBone':head_bone,'neckBone':neck_bone,'headMask':str(mask_path),'headMaskSha256':sha(mask_path),'headFaces':len(head_faces),'mandatoryFaceIdentityFaces':len(mask['face_identity_faces']),'protectedHairFacesBelowCut':len(mask['hair_faces_below_cut_plane']),'retainedHeadVertices':len(head_used),'bodyFacesRemoved':len(remove),'bodyFacesKept':len(keep),'originalIdentityObjectsHiddenAndExcluded':hidden,'headBinding':'rigid bone parent, no Armature modifier on extracted head; static local normals transform with object world matrix','maximumBindPositionErrorMeters':bind_error,'bindFrame':bind_frame,'bindTranslation':delta.tolist(),'uniformRootScale':factor,'idleHeightMeters':height,'idleMinZ':minz,'nativeClips':base['clips'],'whiteBodySource':base['whiteUniformSourceLibrary'],'whiteBodySourceSha256':base['whiteUniformSourceLibrarySha256'],'userApprovedStandardBodyStrategy':True,'headFaceHairSourceGeometryAndUVPreservedExceptGlobalRigidFitAndScale':True,'nativeBodyBoneWeightsPreservedOnRetainedVertices':True,'nativeWalkValidated':False,'neckSeamAndHairCollarIntersectionsValidated':False,'ambiguousCollarFaceCountForVisualReview':len(mask['ambiguous_collar_face_indices']),'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps({'status':result['status'],'headFaces':len(head_faces),'bodyFacesRemoved':len(remove),'height':height,'minimumZ':minz,'bindError':bind_error,'librarySha256':result['sha256']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
