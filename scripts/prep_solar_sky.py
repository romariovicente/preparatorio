"""Build the reference-inspired solar sky additively in Blender 5.2.

Configuration and authored illustrated planet textures match SolarSky.jsx.
This is a didactic sky projection over an Earth-local city, not astronomical
ephemerides. No existing meshes, rigs, pivots, originals or exported GLBs change.

Run after the city finalizer and the Mixamo pipeline, with __file__ set.
Optional globals: PREP_SOLAR_CHECKPOINT=True, PREP_SOLAR_RENDER=True,
PREP_SOLAR_CLOCK_MODE='server-wall' or 'timeline', PREP_SOLAR_SAVE_BLEND=True.
The standalone blend contains only the new solar scene and dependencies. The
orchestrator separately saves the full master after all integrations finish.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import time

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'frontend/src/config/solarSystem.json'
MANIFEST_PATH = ROOT / 'frontend/src/config/cyberWorldManifest.json'
CONFIG = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
CLOCK = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))['clock']
SUFFIX = '20261005'
SCENE_NAME = 'PREP_SOLAR_SYSTEM_' + SUFFIX
COLLECTION_NAME = 'ARAP_11_SOLAR_SKY_' + SUFFIX
BLEND = ROOT / 'art/blender' / ('PREPARATORIO_SOLAR_SYSTEM_' + SUFFIX + '.blend')
REPORT = ROOT / 'reports' / ('solar_system_' + SUFFIX + '.json')
PREVIEW = ROOT / 'reports' / ('SOLAR_SYSTEM_' + SUFFIX + '.png')
CITY = '00_ARAPIRACA_CYBER_20261005'
TAU = math.tau
MODE = str(globals().get('PREP_SOLAR_CLOCK_MODE', CLOCK.get('clockMode', 'server-wall')))
if MODE not in ('server-wall', 'timeline'):
    raise ValueError('Supported clock modes: server-wall or timeline')


def xyz(point):
    return Vector((point[0], -point[2], point[1]))


def color(hex_color):
    return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def offset(planet, angle, radius):
    x, z = math.cos(angle) * radius, math.sin(angle) * radius
    inclination = math.radians(planet['inclinationDeg'])
    node = math.radians(planet['nodeDeg'])
    tilted_y, tilted_z = -z * math.sin(inclination), z * math.cos(inclination)
    return Vector((x * math.cos(node) + tilted_z * math.sin(node), tilted_y,
                   -x * math.sin(node) + tilted_z * math.cos(node)))


def elapsed_seconds(now_ms=None, frame=None):
    if MODE == 'server-wall':
        timestamp = time.time() * 1000 if now_ms is None else now_ms
        return (timestamp - CLOCK['epochMs']) / 1000
    return max(0, ((frame or 1) - 1) / CLOCK.get('blenderFps', 60))


def planet_position(planet, elapsed):
    angle = elapsed / CLOCK['orbitPeriodSeconds'] / planet['periodEarthYears'] * TAU
    if planet['id'] != 'earth':
        angle += math.radians(planet['phaseDeg'])
    return xyz(Vector(CLOCK['sunCenter']) + offset(planet, angle, CLOCK['orbitRadius'] * planet['orbitRatio']))


def illustrated_texture(planet):
    """Same equations/polygons as the frontend; no reference-image editing."""
    width, height = CONFIG['textureWidth'], CONFIG['textureHeight']
    lon, lat = np.meshgrid(np.linspace(-180, 180, width), np.linspace(-90, 90, height))

    def wave(longitude, latitude, seed):
        return .5 + .5 * np.sin(longitude * .113 + np.sin(latitude * .19 + seed) * 2.3 + seed) * np.cos(latitude * .177 - longitude * .057)

    first, second = [color(c) for c in planet['colors']]
    detail = wave(lon, lat, planet['orbitRatio'] * 7)
    amount = detail * .65 + .15
    if planet['surface'] == 'bands':
        stripe = .5 + .5 * np.sin(lat * .71 + np.sin(lon * .05) * .7)
        amount = stripe * .7 + detail * .3
    pixels = np.rint(first + (second - first) * amount[..., None])
    if planet['surface'] == 'earth':
        land_mask = np.zeros((height, width), dtype=bool)
        for polygon in CONFIG['continents']:
            inside = np.zeros((height, width), dtype=bool)
            previous = polygon[-1]
            for current in polygon:
                xi, yi = current
                xj, yj = previous
                if yj != yi:
                    crossing = ((yi > lat) != (yj > lat)) & (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)
                    inside ^= crossing
                previous = current
            land_mask |= inside
        arid = np.maximum(0, 1 - np.abs(np.abs(lat) - 23) / 16) * detail
        land, desert = color(CONFIG['earthLandColor']), color(CONFIG['earthDesertColor'])
        land_pixels = np.rint(land + (desert - land) * arid[..., None])
        land_pixels = np.rint(land_pixels * (.82 + detail[..., None] * .24))
        pixels[land_mask] = land_pixels[land_mask]
        polar = np.minimum(1, (np.abs(lat) - 76) / 8)
        polar = np.maximum(0, polar)
        pixels = np.rint(pixels + (np.array([232, 242, 240]) - pixels) * polar[..., None])
        clouds = wave(lon * 1.8, lat * .85, 17) * wave(lon * .61, lat * 1.9, 4)
        amount = np.clip((clouds - .46) * 2, 0, .65)
        pixels = np.rint(pixels + (np.array([246, 248, 247]) - pixels) * amount[..., None])
    rgba = np.concatenate((np.clip(pixels / 255, 0, 1), np.ones((height, width, 1))), axis=2)
    image = bpy.data.images.new('SOLAR_TEXTURE_' + planet['id'] + '_' + SUFFIX, width=width, height=height, alpha=True)
    image.colorspace_settings.name = 'sRGB'
    image.pixels.foreach_set(rgba.astype(np.float32).ravel())
    image.pack()
    return image


def material(name, base, image=None, emission=0, roughness=.8):
    mat = bpy.data.materials.new('MAT_SOLAR_' + name + '_' + SUFFIX)
    mat.use_nodes = True
    principled = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    rgb = (*tuple(color(base) / 255), 1)
    principled.inputs['Base Color'].default_value = rgb
    principled.inputs['Roughness'].default_value = roughness
    principled.inputs['Emission Color'].default_value = rgb
    principled.inputs['Emission Strength'].default_value = emission
    mat.diffuse_color = rgb
    if image:
        texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        mat.node_tree.links.new(texture.outputs['Color'], principled.inputs['Base Color'])
        if emission:
            mat.node_tree.links.new(texture.outputs['Color'], principled.inputs['Emission Color'])
    return mat


def uv_sphere(name, radius, mat, collection, parent=None, segments=48, rings=32):
    vertices, uvs, faces = [], [], []
    for row in range(rings + 1):
        theta = row / rings * math.pi
        for column in range(segments + 1):
            phi = column / segments * TAU
            vertices.append(tuple(xyz((-radius * math.cos(phi) * math.sin(theta), radius * math.cos(theta), radius * math.sin(phi) * math.sin(theta)))))
            uvs.append((column / segments, 1 - row / rings))
    for row in range(rings):
        for column in range(segments):
            a = row * (segments + 1) + column
            b, c, d = a + 1, a + segments + 1, a + segments + 2
            faces.append((a, c, d) if row == 0 else (a, c, b) if row == rings - 1 else (a, c, d, b))
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    layer = mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for loop in polygon.loop_indices:
            layer.data[loop].uv = uvs[mesh.loops[loop].vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def curve(name, points, radius, mat, collection):
    data = bpy.data.curves.new(name + '_Curve', 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth, data.bevel_resolution = radius, 2
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*value, 1)
    spline.use_cyclic_u = True
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    return obj


def text(name, body, position, mat, collection, size=.65):
    data = bpy.data.curves.new(name + '_Font', 'FONT')
    data.body, data.size, data.align_x = body, size, 'CENTER'
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = position
    return obj


def star_field(collection, center):
    seed, vertices, faces, indices = CONFIG['starSeed'], [], [], []

    def random():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296

    for _ in range(CONFIG['starCount']):
        y, angle = random() * 2 - 1, random() * TAU
        brightness, temperature = .4 + random() * .55, random()
        radial = math.sqrt(1 - y * y)
        direction = xyz((radial * math.cos(angle), y, radial * math.sin(angle)))
        point = center + direction * CONFIG['starRadius']
        right = direction.cross(Vector((0, 0, 1)))
        if right.length < .001:
            right = direction.cross(Vector((0, 1, 0)))
        right.normalize()
        up = direction.cross(right).normalized()
        scale = .06 + brightness ** 4 * .25
        start = len(vertices)
        vertices.extend(tuple(point + right * dx * scale + up * dy * scale) for dx, dy in [(-1, -1), (-1, 1), (1, 1), (1, -1)])
        faces.append((start, start + 1, start + 2, start + 3))
        indices.append(0 if temperature < .15 else 1 if temperature > .88 else 2)
    mesh = bpy.data.meshes.new('SOLAR_STAR_FIELD_Mesh')
    mesh.from_pydata(vertices, [], faces)
    for name, rgb in [('Cool', '#a8d4ff'), ('Warm', '#ffe0ad'), ('White', '#e3e8ed')]:
        mesh.materials.append(material('Star_' + name, rgb, emission=8))
    for polygon, index in zip(mesh.polygons, indices):
        polygon.material_index = index
    obj = bpy.data.objects.new('SOLAR_Stars_' + str(CONFIG['starCount']), mesh)
    collection.objects.link(obj)
    return obj


def frame_curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def baked_timeline(roots, bodies, planets):
    # 0.25 s key spacing keeps the Earth's chord error below 0.001 m.
    fps = CLOCK.get('blenderFps', 60)
    end = 1 + round(CLOCK['orbitPeriodSeconds'] * fps)
    for planet in planets:
        root, body = roots[planet['id']], bodies[planet['id']]
        for frame in range(1, end + 1, max(1, round(fps / 4))):
            elapsed = (frame - 1) / fps
            root.location = planet_position(planet, elapsed)
            root.keyframe_insert(data_path='location', frame=frame)
        for frame in (1, end):
            body.rotation_euler.z = (frame - 1) / fps / CLOCK['dayPeriodSeconds'] * TAU * planet['spinRatio']
            body.keyframe_insert(data_path='rotation_euler', frame=frame)
        for obj in (root, body):
            for fc in frame_curves(obj.animation_data.action):
                for key in fc.keyframe_points:
                    key.interpolation = 'LINEAR'
    return end


def register_wall_clock(roots, bodies, labels, scenes):
    """Register live wall-clock movement in this authorized Blender session.

    The persisted text is optional on reopening; security preferences are never
    changed. The same epoch and 120 s Earth phase are used by the frontend.
    """
    ids = {planet['id']: planet for planet in CONFIG['planets']}

    def tick():
        if any(root.name not in bpy.data.objects for root in roots.values()):
            return None
        now_ms = time.time() * 1000
        elapsed = (now_ms - CLOCK['epochMs']) / 1000
        for pid, root in roots.items():
            planet = ids[pid]
            root.location = planet_position(planet, elapsed)
            bodies[pid].rotation_euler.z = elapsed / CLOCK['dayPeriodSeconds'] * TAU * planet['spinRatio']
            labels[pid].location = root.location + xyz((0, planet['radius'] + 1.25, 0))
        local = datetime.fromtimestamp(now_ms / 1000, tz=timezone(timedelta(hours=-3)))
        phase = ('Noite' if local.hour < 6 or local.hour >= 18 else 'Manhã' if local.hour < 12 else 'Tarde')
        quarter = int(elapsed % CLOCK['orbitPeriodSeconds'] / CLOCK['orbitPeriodSeconds'] * 4) + 1
        caption = f'CHRONOVITAE | {local:%H:%M} | {phase} | ORBITA {quarter}/4'
        for scene in scenes:
            if scene.name not in bpy.data.scenes:
                continue
            scene['solar_wall_time_brasilia'] = local.isoformat()
            scene['solar_earth_phase_rad'] = elapsed / CLOCK['orbitPeriodSeconds'] * TAU % TAU
            for obj in scene.objects:
                if obj.name.startswith(('CLOCK_PHONE_Q', 'CLOCK_BILLBOARD_Q')) and obj.type == 'FONT':
                    obj.data.body = caption
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        return .2

    old = bpy.app.driver_namespace.get('prep_solar_wall_tick')
    if old and bpy.app.timers.is_registered(old):
        bpy.app.timers.unregister(old)
    bpy.app.driver_namespace['prep_solar_wall_tick'] = tick
    tick()
    bpy.app.timers.register(tick, first_interval=.2, persistent=True)
    return tick


def run():
    if bpy.data.collections.get(COLLECTION_NAME) or bpy.data.scenes.get(SCENE_NAME) or BLEND.exists() or REPORT.exists():
        raise FileExistsError('Inspect existing solar delivery/attempt before rerunning with the same names')
    city = bpy.data.scenes.get(CITY)
    if city is None:
        raise ValueError('Expected existing Arapiraca scene; do not create a replacement city here')
    previous_scene = bpy.context.window.scene
    if globals().get('PREP_SOLAR_CHECKPOINT', True):
        checkpoint = ROOT / 'art/blender/checkpoints' / ('BEFORE_SOLAR_SKY_' + SUFFIX + '.blend')
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        if checkpoint.exists():
            raise FileExistsError('Inspect existing solar checkpoint before rerunning')
        bpy.data.libraries.write(str(checkpoint), {city}, path_remap='ABSOLUTE', fake_user=True, compress=True)
    report = {'status': 'building', 'id': CONFIG['id'], 'blenderVersion': bpy.app.version_string,
              'clockMode': MODE, 'earthClock': CLOCK, 'presentation': CONFIG['presentation'],
              'cityFrame': CONFIG['cityFrame'], 'configSha256': hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
              'originalReferencePreserved': True, 'runtimeRegistryChanged': False}
    collection = bpy.data.collections.new(COLLECTION_NAME)
    city.collection.children.link(collection)
    scene = bpy.data.scenes.new(SCENE_NAME)
    scene.collection.children.link(collection)
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', 1
    scene.render.fps = CLOCK.get('blenderFps', 60)
    scene.frame_start, scene.frame_end = 1, 1 + round(CLOCK['orbitPeriodSeconds'] * scene.render.fps)
    scene['presentation'], scene['city_frame'], scene['clock_mode'] = CONFIG['presentation'], CONFIG['cityFrame'], MODE
    bpy.context.window.scene = scene
    center = xyz(CLOCK['sunCenter'])
    sun_image = illustrated_texture({'id': 'sun', 'colors': ['#ff9b35', '#fff2c2'], 'surface': 'cloud', 'orbitRatio': 2.3})
    sun_mat = material('Sun', '#fff1cc', image=sun_image, emission=7, roughness=.9)
    sun = uv_sphere('SOLAR_Sun', CONFIG['sunRadius'], sun_mat, collection, segments=64, rings=40)
    sun.location = center
    star_field(collection, center)
    roots, bodies, labels, planet_rows = {}, {}, {}, []
    initial_elapsed = elapsed_seconds()
    for planet in CONFIG['planets']:
        pid = planet['id']
        root = bpy.data.objects.new('SOLAR_Root_' + pid, None)
        collection.objects.link(root)
        root.location = planet_position(planet, initial_elapsed)
        root['solar_planet'], root['clock_epoch_ms'] = pid, float(CLOCK['epochMs'])
        body = bpy.data.objects.new('SOLAR_Body_' + pid, None)
        collection.objects.link(body)
        body.parent = root
        body.rotation_euler = (0, -math.radians(23.4) if pid == 'earth' else 0,
                               initial_elapsed / CLOCK['dayPeriodSeconds'] * TAU * planet['spinRatio'])
        image = illustrated_texture(planet)
        mat = material(pid, '#ffffff', image=image, emission=.045, roughness=.72 if pid == 'earth' else .88)
        sphere = uv_sphere('SOLAR_Planet_' + pid, planet['radius'], mat, collection, parent=body)
        guide_mat = material('Orbit_' + pid, planet['orbitColor'], emission=1.5)
        guide_points = [center + xyz(offset(planet, index / 192 * TAU, CLOCK['orbitRadius'] * planet['orbitRatio'])) for index in range(192)]
        curve('SOLAR_Orbit_' + pid, guide_points, .018 if pid == 'earth' else .012, guide_mat, collection)
        label = text('SOLAR_Label_' + pid, planet['label'], root.location + xyz((0, planet['radius'] + 1.25, 0)), guide_mat, collection)
        labels[pid] = label
        if pid == 'earth':
            marker = CONFIG['earthCityMarker']
            lat, lon = math.radians(marker['latitudeDeg']), math.radians(marker['longitudeDeg'])
            city_marker = uv_sphere('SOLAR_Arapiraca_City_Marker', .047, material('City_marker', '#ffd571', emission=4), collection, parent=body, segments=12, rings=8)
            city_marker.location = xyz((math.cos(lon) * math.cos(lat) * planet['radius'] * 1.025,
                                       math.sin(lat) * planet['radius'] * 1.025,
                                       -math.sin(lon) * math.cos(lat) * planet['radius'] * 1.025))
            city_marker['marker_not_a_city_mesh'] = True
            city_marker['earth_local_city_scene'] = CITY
        if planet.get('rings'):
            ring_mat = material('Saturn_Rings', '#d6c098', roughness=.95)
            vertices, faces = [], []
            for index in range(97):
                for radius in planet['rings']:
                    angle = index / 96 * TAU
                    vertices.append((math.cos(angle) * radius * planet['radius'], math.sin(angle) * radius * planet['radius'], 0))
            for index in range(96):
                start = index * 2
                faces.append((start, start + 1, start + 3, start + 2))
            mesh = bpy.data.meshes.new('SOLAR_Saturn_Rings_Mesh')
            mesh.from_pydata(vertices, [], faces)
            mesh.materials.append(ring_mat)
            ring_obj = bpy.data.objects.new('SOLAR_Saturn_Rings', mesh)
            collection.objects.link(ring_obj)
            ring_obj.parent = body
            ring_obj.rotation_euler.y = .22
        roots[pid], bodies[pid] = root, body
        planet_rows.append({'id': pid, 'label': planet['label'], 'object': sphere.name,
                            'radiusMetersInProjection': planet['radius'], 'orbitRadius': CLOCK['orbitRadius'] * planet['orbitRatio'],
                            'packedTexture': image.name, 'illustratedSurface': True})
    label_mat = material('Sun_Label', '#ffd98b', emission=2)
    text('SOLAR_Label_Sun', 'SOL', center + xyz((0, -CONFIG['sunRadius'] - 2, 0)), label_mat, collection, .9)
    # Retain the previous sky but exclude its collection only in the city's
    # current view layers. Existing saved versions and its geometry stay intact.
    old_exclusions = []
    for view_layer in city.view_layers:
        old_layer = view_layer.layer_collection.children.get('ARAP_08_HELIOCENTRIC_CLOCK')
        if old_layer:
            old_layer.exclude = True
            old_exclusions.append({'viewLayer': view_layer.name, 'collection': old_layer.collection.name})
    report['retainedPreviousSkyExcludedFromCity'] = old_exclusions
    bpy.ops.object.light_add(type='POINT', location=center)
    light = bpy.context.object
    light.name, light.data.energy, light.data.color, light.data.shadow_soft_size = 'SOLAR_Sun_Light', 7000, (1, .91, .74), 2.65
    for old in list(light.users_collection):
        old.objects.unlink(light)
    collection.objects.link(light)
    scene.world = bpy.data.worlds.new('SOLAR_Black_Starfield_World')
    scene.world.use_nodes = True
    background = next(node for node in scene.world.node_tree.nodes if node.type == 'BACKGROUND')
    background.inputs['Color'].default_value, background.inputs['Strength'].default_value = (.001, .002, .004, 1), .04
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.object.camera_add(location=center + xyz((60, 50, 80)))
    camera = bpy.context.object
    camera.name = 'SOLAR_Planetarium_Camera'
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type, camera.data.ortho_scale, camera.data.clip_end = 'ORTHO', 110, 1000
    scene.camera = camera
    # Only this dedicated scene contains a planetarium camera; linking the new
    # sky collection to the city does not change its active camera.
    if MODE == 'timeline':
        baked_timeline(roots, bodies, CONFIG['planets'])
        scene.frame_set(1)
    else:
        register_wall_clock(roots, bodies, labels, (city, scene))
    reactivation = '''# Authorized locally authored solar-sky wall-clock preview.\n# Execute this text after reopening to resume live updates.\nfrom pathlib import Path\nimport bpy, json, math, time, datetime\nfrom mathutils import Vector\nroot=Path(%r)\ncfg=json.loads((root/'frontend/src/config/solarSystem.json').read_text(encoding='utf-8'))\nclock=json.loads((root/'frontend/src/config/cyberWorldManifest.json').read_text(encoding='utf-8'))['clock']\ndef prep_solar_resume_tick():\n    elapsed=(time.time()*1000-clock['epochMs'])/1000\n    for p in cfg['planets']:\n        obj=bpy.data.objects.get('SOLAR_Root_'+p['id'])\n        body=bpy.data.objects.get('SOLAR_Body_'+p['id'])\n        if not obj or not body:return None\n        a=elapsed/clock['orbitPeriodSeconds']/p['periodEarthYears']*math.tau+(0 if p['id']=='earth' else math.radians(p['phaseDeg']))\n        r=clock['orbitRadius']*p['orbitRatio'];x=math.cos(a)*r;z=math.sin(a)*r;i=math.radians(p['inclinationDeg']);n=math.radians(p['nodeDeg']);y=-z*math.sin(i);zz=z*math.cos(i)\n        s=clock['sunCenter'];obj.location=(s[0]+x*math.cos(n)+zz*math.sin(n),-s[2]+x*math.sin(n)-zz*math.cos(n),s[1]+y)\n        body.rotation_euler.z=elapsed/clock['dayPeriodSeconds']*math.tau*p['spinRatio']\n        label=bpy.data.objects.get('SOLAR_Label_'+p['id'])\n        if label:label.location=obj.location+Vector((0,0,p['radius']+1.25))\n    local=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)));phase='Noite' if local.hour<6 or local.hour>=18 else 'Manhã' if local.hour<12 else 'Tarde';q=int((elapsed%%clock['orbitPeriodSeconds'])/clock['orbitPeriodSeconds']*4)+1\n    for obj in bpy.data.objects:\n        if obj.name.startswith(('CLOCK_PHONE_Q','CLOCK_BILLBOARD_Q')) and obj.type=='FONT':obj.data.body=f'CHRONOVITAE | {local:%%H:%%M} | {phase} | ORBITA {q}/4'\n    for window in bpy.context.window_manager.windows:\n        for area in window.screen.areas:\n            if area.type=='VIEW_3D':area.tag_redraw()\n    return .2\nold=bpy.app.driver_namespace.get('prep_solar_wall_tick')\nif old and bpy.app.timers.is_registered(old):bpy.app.timers.unregister(old)\nbpy.app.driver_namespace['prep_solar_wall_tick']=prep_solar_resume_tick\nprep_solar_resume_tick();bpy.app.timers.register(prep_solar_resume_tick,first_interval=.2,persistent=True)\n''' % str(ROOT)
    txt = bpy.data.texts.new('PREP_SOLAR_WALL_CLOCK.py')
    txt.write(reactivation)
    # Verify the expected Earth clock formula independently at representative
    # offsets; the rendered locations use the same sampling function.
    proof = []
    earth = next(planet for planet in CONFIG['planets'] if planet['id'] == 'earth')
    for elapsed in (0, 10.25, 30, 45.5, 60, 90, 120, 256.125):
        expected = xyz((CLOCK['sunCenter'][0] + math.cos(elapsed / CLOCK['orbitPeriodSeconds'] * TAU) * CLOCK['orbitRadius'],
                        CLOCK['sunCenter'][1], CLOCK['sunCenter'][2] + math.sin(elapsed / CLOCK['orbitPeriodSeconds'] * TAU) * CLOCK['orbitRadius']))
        error = (planet_position(earth, elapsed) - expected).length
        if error > .000001:
            raise AssertionError('Earth diverges from shared phase: ' + str(error))
        proof.append({'elapsedSeconds': elapsed, 'sharedClockEarthErrorMeters': error})
    report.update(planets=planet_rows, planetCount=len(planet_rows), stars=CONFIG['starCount'],
                  objects=len(collection.objects), collection=collection.name, scene=scene.name,
                  cityScene=city.name, earthPhaseChecks=proof, timerLiveThisSession=MODE == 'server-wall',
                  resumeText=txt.name, noAutoexecSecurityPreferenceChanged=True)
    if globals().get('PREP_SOLAR_RENDER', True):
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 16
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1440, 900, 100
        scene.render.filepath = str(PREVIEW)
        bpy.ops.render.render(write_still=True)
        report['preview'] = str(PREVIEW)
    if globals().get('PREP_SOLAR_SAVE_BLEND', True):
        BLEND.parent.mkdir(parents=True, exist_ok=True)
        bpy.data.libraries.write(str(BLEND), {scene, txt}, path_remap='ABSOLUTE', fake_user=True, compress=True)
        report['blend'], report['blendBytes'] = str(BLEND), BLEND.stat().st_size
        with bpy.data.libraries.load(str(BLEND), link=False) as (data_from, data_to):
            if SCENE_NAME not in data_from.scenes:
                raise AssertionError('Independent solar blend is missing its scene')
            report['blendScenesVerified'] = list(data_from.scenes)
    report['status'] = 'validated'
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    bpy.context.window.scene = previous_scene
    print(json.dumps({'status': report['status'], 'scene': scene.name, 'report': str(REPORT),
                      'planets': report['planetCount'], 'stars': report['stars'], 'clockMode': MODE}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    run()
