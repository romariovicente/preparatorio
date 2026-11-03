import bpy,json
out=[]
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            out.append({'areaSize':[area.width,area.height],'spaceProperties':[p.identifier for p in space.bl_rna.properties if 'panel' in p.identifier or 'region' in p.identifier],'regions':[{'type':r.type,'properties':[p.identifier for p in r.bl_rna.properties if 'panel' in p.identifier or 'active' in p.identifier]} for r in area.regions],'viewDistance':space.region_3d.view_distance,'viewLocation':list(space.region_3d.view_location),'viewRotation':list(space.region_3d.view_rotation)})
print(json.dumps(out))
