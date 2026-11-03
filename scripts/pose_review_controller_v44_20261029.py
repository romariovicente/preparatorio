"""Explicit-session Blender review controls. No handlers, auto-run or new solve."""
import bpy,bmesh,json,hashlib
import numpy as np
from pathlib import Path

PROJECT_ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
CANDIDATE=PROJECT_ROOT/'work/probe_thai_pose_poisson_v43_20261029/pose_poisson_candidate_v43.npz'
EXPECTED_SHA='3fefc2d3c6be8cb5e2f2962eb2073173e1d3ffe5424fa4596cab46c0a10513da'
ATTR='V43_Pose_Offset_ObjectSpace_Snapshot'
SAMPLES={'Idle':(1,51,101,151),'Walk':(1,7,13,19)}
_CACHE=None

def _candidate():
    global _CACHE
    st=CANDIDATE.stat();key=(str(CANDIDATE),st.st_size,st.st_mtime_ns,EXPECTED_SHA)
    if _CACHE is None or _CACHE[0]!=key:
        actual=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
        if actual!=EXPECTED_SHA:raise ValueError('O arquivo de referência mudou. A revisão foi interrompida para preservar o projeto.')
        with np.load(CANDIDATE,allow_pickle=False) as z:
            data={k:z[k].copy() for k in ['restWorldCandidate','trianglesCandidate','weights55Candidate','names55','boneRest55','editableVertexIndices']}
            outside=np.ones(len(data['restWorldCandidate']),bool);outside[data['editableVertexIndices']]=False
            for clip,frames in SAMPLES.items():
                for frame in frames:
                    for branch in ['native','corrected']:
                        name=f'{clip}_{frame}_{branch}DeltaQ';delta=np.asarray(z[name],dtype=np.float32)
                        if not np.isfinite(delta).all() or np.any(delta[outside]!=0):raise ValueError('Amostra de revisão inválida.')
                        data[name]=delta
        _CACHE=(key,data)
    return _CACHE[1]

def actor(scene,strict=True):
    found=[o for o in scene.objects if o.type=='MESH' and o.get('PREP_interactive_pose_review_v44',False)]
    if len(found)==1:return found[0]
    if strict:raise ValueError('O personagem de revisão não está disponível nesta cena.')
    return None

def _verify_bind(body,data):
    if body.mode!='OBJECT':raise ValueError('Saia do modo de edição ou pintura para trocar a amostra.')
    mesh=body.data
    p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p)
    t=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',t)
    if not np.array_equal(p.reshape(-1,3),data['restWorldCandidate']) or not np.array_equal(t.reshape(-1,3),data['trianglesCandidate']):
        raise ValueError('A malha foi editada. As edições foram preservadas; a prévia precisa ser revisada.')
    if list(body.vertex_groups.keys())!=data['names55'].tolist():raise ValueError('Os grupos do personagem mudaram. Revisão interrompida.')
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();dw=bm.verts.layers.deform.active
        weights=np.zeros_like(data['weights55Candidate'])
        if dw is not None:
            for vertex in bm.verts:
                for index,value in vertex[dw].items():
                    if index>=55 and value!=0:raise ValueError('Há novos grupos deformadores. Revisão interrompida.')
                    if index<55:weights[vertex.index,index]=value
    finally:bm.free()
    if not np.array_equal(weights,data['weights55Candidate']):raise ValueError('Os pesos foram editados. As edições foram preservadas; a prévia precisa ser revisada.')
    if not np.array_equal(np.array(body.matrix_world,dtype=float),np.eye(4)):raise ValueError('A transformação do personagem mudou. Revisão interrompida.')

def apply_sample(scene,clip,frame,branch=None,variant=None):
    """Validate everything first; restore the prior preview if an apply fails."""
    if clip not in SAMPLES or frame not in SAMPLES[clip]:raise ValueError('Escolha uma das oito amostras disponíveis.')
    branch=branch or scene.prep44_branch;variant=variant or scene.prep44_variant
    if branch not in ['native','corrected'] or variant not in ['base','study']:raise ValueError('Modo de revisão inválido.')
    body=actor(scene);data=_candidate();_verify_bind(body,data)
    rigs=[bpy.data.objects.get(body['PREP_review_native_rig']),bpy.data.objects.get(body['PREP_review_pose_rig'])]
    if any(o is None or o.type!='ARMATURE' for o in rigs):raise ValueError('A estrutura do personagem não está disponível.')
    for rig in rigs:
        rest=np.array([np.array(rig.data.bones[n].matrix_local,dtype=float) for n in data['names55'].tolist()])
        if not np.array_equal(rest,data['boneRest55']):raise ValueError('A estrutura foi editada. Revisão interrompida.')
    action=bpy.data.actions.get(clip+'.002')
    if action is None or not action.slots:raise ValueError('A animação de referência não está disponível.')
    if len(body.modifiers)!=2 or body.modifiers[0].type!='ARMATURE' or body.modifiers[1].type!='NODES':raise ValueError('A pilha de revisão mudou.')
    if ATTR not in body.data.attributes:raise ValueError('O ajuste da amostra não está disponível.')
    delta=data[f'{clip}_{frame}_{branch}DeltaQ'];attribute=body.data.attributes[ATTR]
    saved_offset=np.empty(delta.size,np.float32);attribute.data.foreach_get('vector',saved_offset)
    first,corrective=body.modifiers
    old_rigs=[(rig,rig.animation_data.action,rig.animation_data.action_slot,[tr.mute for tr in rig.animation_data.nla_tracks]) for rig in rigs]
    old=(scene.frame_start,scene.frame_end,scene.frame_current,first.object,corrective.show_viewport,corrective.show_render)
    keys=['PREP_snapshot_clip','PREP_snapshot_frame','PREP_snapshot_branch','PREP_review_variant']
    old_meta={key:body.get(key) for key in keys}
    try:
        for rig in rigs:
            rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
            for track in rig.animation_data.nla_tracks:track.mute=True
        attribute.data.foreach_set('vector',delta.reshape(-1));body.data.update()
        first.object=rigs[1 if branch=='corrected' else 0]
        corrective.show_viewport=variant=='study';corrective.show_render=variant=='study'
        scene.frame_start=frame;scene.frame_end=frame;scene.frame_set(frame)
        body['PREP_snapshot_clip']=clip;body['PREP_snapshot_frame']=frame;body['PREP_snapshot_branch']=branch;body['PREP_review_variant']=variant
        body.update_tag();bpy.context.view_layer.update()
    except BaseException:
        attribute.data.foreach_set('vector',saved_offset);body.data.update()
        for rig,previous,slot,mutes in old_rigs:
            rig.animation_data.action=previous
            if previous is not None and slot is not None:rig.animation_data.action_slot=slot
            for track,mute in zip(rig.animation_data.nla_tracks,mutes):track.mute=mute
        scene.frame_start,scene.frame_end=old[:2];scene.frame_set(old[2]);first.object=old[3]
        corrective.show_viewport=old[4];corrective.show_render=old[5]
        for key,value in old_meta.items():
            if value is None:
                if key in body:del body[key]
            else:body[key]=value
        body.update_tag();bpy.context.view_layer.update()
        raise
    scene['PREP_review_last_clip']=clip;scene['PREP_review_last_frame']=frame
    scene['PREP_review_last_branch']=branch;scene['PREP_review_last_variant']=variant
    scene['PREP_review_last_error']=''
    return body

def _settings_changed(scene,context):
    if scene.get('PREP_review_settings_guard',False) or actor(scene,False) is None:return
    try:apply_sample(scene,scene.get('PREP_review_last_clip','Idle'),int(scene.get('PREP_review_last_frame',101)))
    except Exception as exc:
        scene['PREP_review_last_error']=str(exc);scene['PREP_review_settings_guard']=True
        try:
            scene.prep44_branch=scene.get('PREP_review_last_branch','corrected')
            scene.prep44_variant=scene.get('PREP_review_last_variant','study')
        finally:scene['PREP_review_settings_guard']=False

class PREP44_OT_PoseSample(bpy.types.Operator):
    bl_idname='preparatorio.review_pose_sample_v44'
    bl_label='Mostrar amostra'
    bl_description='Trocar a pose e seu ajuste juntos, preservando as animações originais'
    bl_options={'REGISTER','UNDO'}
    clip:bpy.props.StringProperty(default='Idle')
    sample_frame:bpy.props.IntProperty(default=101,min=1)
    def execute(self,context):
        try:apply_sample(context.scene,self.clip,self.sample_frame)
        except Exception as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class PREP44_PT_PoseReview(bpy.types.Panel):
    bl_label='Revisão do personagem'
    bl_idname='PREP44_PT_PoseReview'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Preparatório'
    @classmethod
    def poll(cls,context):return context.scene is not None and actor(context.scene,False) is not None
    def draw(self,context):
        scene=context.scene;layout=self.layout
        layout.label(text='Prévia de oito poses',icon='ARMATURE_DATA')
        layout.prop(scene,'prep44_variant',expand=True)
        layout.prop(scene,'prep44_branch',text='Postura')
        for clip,label in [('Idle','Parado'),('Walk','Caminhada')]:
            box=layout.box();box.label(text=label);row=box.row(align=True)
            for frame in SAMPLES[clip]:
                op=row.operator(PREP44_OT_PoseSample.bl_idname,text=str(frame));op.clip=clip;op.sample_frame=frame
        clip=scene.get('PREP_review_last_clip','Idle');frame=scene.get('PREP_review_last_frame',101)
        layout.label(text=f'Amostra: {"Parado" if clip=="Idle" else "Caminhada"} {frame}')
        layout.label(text='Movimento completo em revisão.',icon='INFO')
        if scene.get('PREP_review_last_error',''):layout.label(text=scene['PREP_review_last_error'],icon='ERROR')

CLASSES=(PREP44_OT_PoseSample,PREP44_PT_PoseReview)
def register():
    for cls in reversed(CLASSES):
        previous=getattr(bpy.types,cls.__name__,None)
        if previous is not None:bpy.utils.unregister_class(previous)
    for name in ['prep44_variant','prep44_branch']:
        if hasattr(bpy.types.Scene,name):delattr(bpy.types.Scene,name)
    bpy.types.Scene.prep44_variant=bpy.props.EnumProperty(name='Comparação',items=[('base','Base','Referência sem o corretivo'),('study','Estudo','Corretivo de superfície ainda em revisão')],default='study',update=_settings_changed)
    bpy.types.Scene.prep44_branch=bpy.props.EnumProperty(name='Postura',items=[('native','Original','Pose nativa de referência'),('corrected','Afastamento dos braços','Postura aditiva de estudo já existente')],default='corrected',update=_settings_changed)
    for cls in CLASSES:bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(CLASSES):
        previous=getattr(bpy.types,cls.__name__,None)
        if previous is not None:bpy.utils.unregister_class(previous)
    for name in ['prep44_variant','prep44_branch']:
        if hasattr(bpy.types.Scene,name):delattr(bpy.types.Scene,name)

if __name__=='__main__':register()
