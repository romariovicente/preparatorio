"""Persisted object channels, independent of a scene's evaluated world cache."""
import hashlib
import json

def object_state(objects):
    result = {}
    for o in sorted(objects, key=lambda o:o.name):
        result[o.name] = {"type":o.type,"parent":o.parent.name if o.parent else None,
                          "data":o.data.name if o.data else None,
                          "collections":sorted(c.name for c in o.users_collection),
                          "hidden":[o.hide_viewport,o.hide_render],
                          "rotation_mode":o.rotation_mode,
                          "matrix_parent_inverse":[list(row) for row in o.matrix_parent_inverse],
                          "action":o.animation_data.action.name if o.animation_data and o.animation_data.action else None}
        for field in ("location","rotation_euler","rotation_quaternion","rotation_axis_angle","scale",
                      "delta_location","delta_rotation_euler","delta_rotation_quaternion","delta_scale"):
            result[o.name][field] = list(getattr(o,field))
    return result

def state_hash(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
