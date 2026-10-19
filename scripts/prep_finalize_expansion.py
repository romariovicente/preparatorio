# Execute after prep_organize_expansion in the same namespace via runpy return dictionary.
def build_main():
 scene=bpy.data.scenes.new('00_PREP_CAMPUS');bpy.context.window.scene=scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 col=bpy.data.collections.new('01_CAMPUS_EDIFICIOS');scene.collection.children.link(col)
 ground=mat('PREP_Pavimento',(.39,.47,.48));grass=mat('PREP_Grama',(.08,.25,.13))
 box(scene,col,'Terreno',(0,4,-.35),(62,65,.6),grass)
 box(scene,col,'Patio',(0,0,-.08),(25,28,.12),ground)
 box(scene,col,'Caminho_Hospital',(0,16,-.06),(6,14,.16),ivory)
 for x in [-13,13]:box(scene,col,'Faixa_Jardim',(x,0,.02),(1,28,.16),teal)
 byid={r['id']:r for r in records}
 for id,loc,size in [('SUP_hospital_02',(0,26,0),26),('SUP_facultad_de_enfermeria_unal_colombia',(-23,4,0),16)]:
  import_asset(scene,byid[id],col,loc,extent=size)
 box(scene,col,'Mesa_de_Estudos',(0,4.5,.55),(3.4,1.6,1.1),teal)
 for x,id in [(-7,'SUP_esqueleto'),(7,'SUP_Anatomic_Muscle_study')]:
  box(scene,col,'Base_Anatomia',(x,4,.5),(1.4,1.4,1),ivory);import_asset(scene,byid[id],col,(x,4,1),height=1.5)
 import_asset(scene,byid['SUP_kit_hospital'],col,(1,4.5,1.12),height=.4)
 for x in [-6,6]:
  box(scene,col,'Banco_Assento',(x,-5,.48),(2.6,.65,.16),teal)
  for offset in [-.95,.95]:box(scene,col,'Banco_Pe',(x+offset,-5,.22),(.15,.55,.44),navy)
 for x in [-10,10]:
  for y in [-9,0,9]:
   box(scene,col,'Poste',(x,y,1.8),(.1,.1,3.6),navy);box(scene,col,'Luminaria',(x,y,3.65),(.5,.5,.18),gold)
 page_path=ROOT.parents[1]/'work/nursing_lesson_page.png'
 if page_path.exists():
  page=mat('PREP_Livro',(.9,.9,.85));im=bpy.data.images.load(str(page_path));im.pack();tex=page.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;page.node_tree.links.new(tex.outputs['Color'],next(n for n in page.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
  bpy.ops.mesh.primitive_plane_add(size=1,location=(-.55,4.5,1.11));o=bpy.context.object;o.name='Livro_Enfermagem_Pagina_7';o.scale=(.6,.85,1);o.data.materials.append(page)
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o)
 # The final environment has a versioned path; previous exports remain recoverable.
 dest=ROOT/'frontend/public/assets/models/ENV_PREP_Campus_v2.glb'
 bpy.ops.object.select_all(action='DESELECT')
 for o in col.all_objects:
  if o.type=='MESH':o.select_set(True)
 bpy.context.view_layer.update()
 bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_apply=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
 validation=bpy.data.scenes.new('VALIDATE_CAMPUS_V2');bpy.context.window.scene=validation;bpy.ops.import_scene.gltf(filepath=str(dest));assert any(o.type=='MESH' for o in validation.objects)
 bpy.context.window.scene=scene
 characters=bpy.data.collections.new('02_PERSONAGENS_ANIMADOS');scene.collection.children.link(characters)
 selected=['SUP_jumpsuit_low_poly','SUP_doctor_horror_hospital','SUP_school_girl_v21','SUP_woman_standing_v16','SUP_lowpoly_anime_character_cyberstyle']
 for i,id in enumerate(selected):
  if id in byid:
   npc=import_asset(scene,byid[id],characters,(-4+i*2,-1,0),height=1.7)
   arm=next((o for o in npc.children_recursive if o.type=='ARMATURE'),None)
   if arm and arm.animation_data:
    clip='Dance' if id=='SUP_doctor_horror_hospital' else 'Interact' if id=='SUP_jumpsuit_low_poly' else 'Idle'
    for track in arm.animation_data.nla_tracks:
     track.mute=track.name!=clip
     if not track.mute:
      for strip in track.strips:strip.repeat=3
    if id=='SUP_jumpsuit_low_poly':
     copy=import_asset(scene,byid['SUP_kit_hospital'],characters,(0,0,0),height=.24)
     socket=bpy.data.objects.new('DEMO_Player_01_Hand_Socket',None);characters.objects.link(socket);socket.parent=arm;socket.parent_type='BONE';socket.parent_bone='R_hand';socket.location=(.04,.05,0)
     copy.parent=socket;copy['owner_id']='DEMO_Player_01';copy['template_id']='SUP_kit_hospital';copy['interaction_note']='Personal carried copy; original kit remains on study desk'
 # A movable hospital cart demonstrates placement changes on the timeline.
 cart=bpy.data.objects.new('PROP_Hospital_Cart_Movable',None);characters.objects.link(cart)
 tray=box(scene,characters,'Carrinho_Bandeja',(0,0,.8),(1,.65,.12),ivory);tray.parent=cart
 for x in [-.42,.42]:
  leg=box(scene,characters,'Carrinho_Suporte',(x,0,.4),(.07,.5,.8),teal);leg.parent=cart
  for y in [-.24,.24]:
   wheel=box(scene,characters,'Carrinho_Roda',(x,y,.07),(.12,.12,.12),navy);wheel.parent=cart
 for frame,x in [(1,4),(60,6),(120,4)]:cart.location=(x,2,0);cart.keyframe_insert(data_path='location',frame=frame)
 cart['interaction_note']='Timeline preview of moving a hospital object; interactive controls are in the browser'

 scene.frame_start=1;scene.frame_end=120;scene.frame_set(1);lighting(scene,38,(0,7,0));scene.camera.data.type='PERSP';scene.camera.data.lens=36;scene.camera.location=(24,-30,22);scene.camera.rotation_euler=(Vector((0,7,1))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'reports/PREP_CAMPUS_20261002.png');bpy.ops.render.render(write_still=True)
 # Restore the map and modular kit as separate scenes, preserving their saved contents.
 with bpy.data.libraries.load(str(ROOT/'art/blender/PREPARATORIO_ISLAND.blend'),link=False) as (available,target):
  target.scenes=[n for n in available.scenes if n in ['PREP_ISLAND','PREP_CITY']]
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False;area.spaces.active.region_3d.view_perspective='CAMERA'
 scene['LEIA_ME']='Campus principal. Outras cenas ACERVO_* contêm os modelos organizados por categoria. Espaço reproduz a animação. Materiais incorporados. Consulte reports/EXPANSAO_20261002.md.'
 bpy.ops.file.pack_all();destblend=ROOT/'art/blender/PREPARATORIO_PROJETO_20261002.blend';bpy.ops.wm.save_as_mainfile(filepath=str(destblend),compress=True)
 report={'blend':str(destblend),'activeScene':scene.name,'scenes':[s.name for s in bpy.data.scenes],'catalogModels':len(records),'materials':len(bpy.data.materials),'objects':len(bpy.data.objects),'armatures':len(bpy.data.armatures),'packedImages':sum(bool(i.packed_file) for i in bpy.data.images),'environmentReimportValidated':True,'environmentBytes':dest.stat().st_size}
 (ROOT/'reports/blender_expansion_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
build_main()
