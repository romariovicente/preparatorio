import bpy,json
print(json.dumps({'version':bpy.app.version_string,'file':bpy.data.filepath,'scene':bpy.context.scene.name,'objects':len(bpy.context.scene.objects),'scenes':[s.name for s in bpy.data.scenes],'vehicleNames':[o.name for o in bpy.context.scene.objects if o.name.startswith(('VEH_','SUPPLACE_','INTERACTIVE_'))]},ensure_ascii=False))
