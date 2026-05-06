import json
import math
from collections import deque
from pathlib import Path

import bmesh
import bpy


OBJ_NAME = "LOD_Body"
MAT_NAME = "Muscle_Fiber_PoseManiacs"
UV_NAME = "UVFiber"
MASK_NAME = "TendonMask"
REPORT_PATH = Path(r"C:\Users\abesh\Documents\Blender\MaleAnatomy\Result\phase2_tendon_boundary_report.json")


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def gaussian(distance: float, width: float) -> float:
    return math.exp(-((distance / max(width, 1e-6)) ** 2))


def window(value: float, rise0: float, rise1: float, fall0: float, fall1: float) -> float:
    return smoothstep(rise0, rise1, value) * (1.0 - smoothstep(fall0, fall1, value))


def detect_uv_boundary_vertices(mesh: bpy.types.Mesh, uv_name: str):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.get(uv_name)
    if uv_layer is None:
        bm.free()
        raise RuntimeError(f"UV layer '{uv_name}' not found")

    boundary_verts = set()
    boundary_edges = 0
    for edge in bm.edges:
        if not edge.is_manifold:
            continue
        loops = edge.link_loops
        if len(loops) != 2:
            continue
        l0, l1 = loops
        a0 = l0[uv_layer].uv.copy()
        a1 = l0.link_loop_next[uv_layer].uv.copy()
        b0 = l1[uv_layer].uv.copy()
        b1 = l1.link_loop_next[uv_layer].uv.copy()
        same = ((a0 - b1).length < 1e-5 and (a1 - b0).length < 1e-5) or ((a0 - b0).length < 1e-5 and (a1 - b1).length < 1e-5)
        if not same:
            boundary_edges += 1
            boundary_verts.add(edge.verts[0].index)
            boundary_verts.add(edge.verts[1].index)
    bm.free()
    return boundary_verts, boundary_edges


def topological_distance_map(mesh: bpy.types.Mesh, seed_vertices: set[int], max_steps: int = 4):
    adjacency = [[] for _ in range(len(mesh.vertices))]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)

    distances = [-1] * len(mesh.vertices)
    queue = deque()
    for idx in seed_vertices:
        distances[idx] = 0
        queue.append(idx)

    while queue:
        current = queue.popleft()
        if distances[current] >= max_steps:
            continue
        for neighbor in adjacency[current]:
            if distances[neighbor] != -1:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    return distances


def generate_tendon_mask(obj: bpy.types.Object, uv_name: str, mask_name: str):
    mesh = obj.data
    boundary_verts, boundary_edges = detect_uv_boundary_vertices(mesh, uv_name)
    topo_dist = topological_distance_map(mesh, boundary_verts, max_steps=3)

    mask_values = [0.0] * len(mesh.vertices)
    min_world = obj.matrix_world @ mesh.vertices[0].co
    max_world = min_world.copy()
    for vert in mesh.vertices:
        co = obj.matrix_world @ vert.co
        min_world.x = min(min_world.x, co.x)
        min_world.y = min(min_world.y, co.y)
        min_world.z = min(min_world.z, co.z)
        max_world.x = max(max_world.x, co.x)
        max_world.y = max(max_world.y, co.y)
        max_world.z = max(max_world.z, co.z)

    for vert in mesh.vertices:
        co = obj.matrix_world @ vert.co
        x_abs = abs(co.x)

        seam_base = 0.0
        dist = topo_dist[vert.index]
        if dist == 0:
            seam_base = 1.0
        elif dist == 1:
            seam_base = 0.38
        elif dist == 2:
            seam_base = 0.12

        front_factor = smoothstep(-0.055, -0.095, co.y)
        back_factor = smoothstep(0.045, 0.090, co.y)
        torso_front = front_factor * window(co.z, 0.74, 0.84, 1.50, 1.60)
        torso_back = back_factor * window(co.z, 0.82, 0.92, 1.70, 1.80)
        torso_factor = max(torso_front, torso_back)

        # UV seams help on limbs, but they made the torso too map-like.
        seam_mask = seam_base * (0.80 - 0.58 * torso_factor)

        sternum = (
            gaussian(x_abs, 0.018)
            * front_factor
            * window(co.z, 1.08, 1.16, 1.42, 1.50)
        )
        linea_alba = (
            gaussian(x_abs, 0.013)
            * front_factor
            * window(co.z, 0.78, 0.86, 1.16, 1.24)
        )
        spine = (
            gaussian(x_abs, 0.016)
            * back_factor
            * window(co.z, 0.90, 0.98, 1.68, 1.78)
        )
        nuchal = (
            gaussian(x_abs, 0.048)
            * back_factor
            * window(co.z, 1.46, 1.56, 1.75, 1.82)
        )
        chest_t = max(0.0, min(1.0, (co.z - 1.06) / 0.36))
        pec_lower_target = 1.07 + 0.14 * min(x_abs / 0.17, 1.0)
        pec_lower = (
            gaussian(co.z - pec_lower_target, 0.026)
            * gaussian(x_abs - 0.11, 0.11)
            * front_factor
            * window(co.z, 1.02, 1.08, 1.34, 1.42)
        )
        pec_outer = (
            gaussian(x_abs - (0.07 + 0.06 * chest_t), 0.018)
            * front_factor
            * window(co.z, 1.12, 1.18, 1.34, 1.44)
        )
        clavicle_band = (
            gaussian(co.z - 1.40, 0.024)
            * gaussian(x_abs - 0.12, 0.12)
            * front_factor
            * window(x_abs, 0.02, 0.06, 0.22, 0.27)
        )
        abdomen_t = max(0.0, min(1.0, (1.18 - co.z) / 0.34))
        semilunar_target = 0.070 + 0.022 * abdomen_t
        semilunar = (
            gaussian(x_abs - semilunar_target, 0.014)
            * front_factor
            * window(co.z, 0.82, 0.88, 1.16, 1.22)
        )
        intersections = max(
            gaussian(co.z - 1.11, 0.016) * gaussian(x_abs, 0.105),
            gaussian(co.z - 1.01, 0.016) * gaussian(x_abs, 0.105),
            gaussian(co.z - 0.90, 0.018) * gaussian(x_abs, 0.105),
        ) * front_factor * window(co.z, 0.84, 0.88, 1.14, 1.18)
        inguinal_target = 0.05 + 0.10 * max(0.0, min(1.0, (0.86 - co.z) / 0.14))
        inguinal = (
            gaussian(x_abs - inguinal_target, 0.018)
            * front_factor
            * window(co.z, 0.68, 0.74, 0.86, 0.92)
        )
        back_t = max(0.0, min(1.0, (1.60 - co.z) / 0.52))
        trap_lat = (
            gaussian(x_abs - (0.05 + 0.12 * back_t), 0.022)
            * back_factor
            * window(co.z, 1.08, 1.16, 1.56, 1.66)
        )
        lower_back = (
            gaussian(x_abs, 0.040)
            * back_factor
            * window(co.z, 0.88, 0.94, 1.16, 1.24)
        )
        lat_waist = (
            gaussian(x_abs - (0.12 + 0.05 * max(0.0, min(1.0, (1.18 - co.z) / 0.20))), 0.022)
            * back_factor
            * window(co.z, 0.96, 1.02, 1.30, 1.38)
        )
        patellar = (
            smoothstep(0.22, 0.12, x_abs)
            * front_factor
            * window(co.z, 0.42, 0.48, 0.64, 0.70)
        )
        elbow_knee_hint = (
            smoothstep(0.18, 0.08, x_abs)
            * (front_factor * 0.6 + back_factor * 0.4)
            * (
                window(co.z, 1.02, 1.10, 1.22, 1.30)
                + window(co.z, 0.38, 0.46, 0.72, 0.80)
            )
        )

        value = max(
            seam_mask,
            sternum * 0.78,
            pec_lower * 0.92,
            pec_outer * 0.70,
            clavicle_band * 0.60,
            linea_alba * 0.82,
            semilunar * 0.78,
            intersections * 0.86,
            inguinal * 0.76,
            spine * 0.90,
            nuchal * 0.74,
            trap_lat * 0.82,
            lower_back * 0.64,
            lat_waist * 0.68,
            patellar * 0.50,
            elbow_knee_hint * 0.30,
        )
        mask_values[vert.index] = max(0.0, min(1.0, value))

    color_attr = mesh.color_attributes.get(mask_name)
    if color_attr is None:
        color_attr = mesh.color_attributes.new(name=mask_name, type="FLOAT_COLOR", domain="POINT")
    elif color_attr.domain != "POINT":
        raise RuntimeError(f"Color attribute '{mask_name}' exists but is not POINT domain")

    for idx, value in enumerate(mask_values):
        color_attr.data[idx].color = (value, value, value, 1.0)

    return {
        "boundary_edge_count": boundary_edges,
        "seed_vertex_count": len(boundary_verts),
        "mask_max": max(mask_values),
        "mask_mean": sum(mask_values) / len(mask_values),
        "mask_gt_0_5": sum(v > 0.5 for v in mask_values),
        "mask_gt_0_8": sum(v > 0.8 for v in mask_values),
    }


def ensure_rgb_node(nodes, name: str, color, location):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeRGB")
        node.name = name
        node.label = name
    node.location = location
    node.outputs[0].default_value = color
    return node


def ensure_vertex_color_node(nodes, name: str, layer_name: str, location):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeVertexColor")
        node.name = name
        node.label = name
    node.location = location
    node.layer_name = layer_name
    return node


def ensure_color_ramp(nodes, name: str, location, stops):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeValToRGB")
        node.name = name
        node.label = name
    node.location = location
    ramp = node.color_ramp
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])
    ramp.elements[0].position = stops[0][0]
    ramp.elements[0].color = stops[0][1]
    if len(stops) == 2:
        ramp.elements[1].position = stops[1][0]
        ramp.elements[1].color = stops[1][1]
    else:
        for stop in stops[1:-1]:
            elem = ramp.elements.new(stop[0])
            elem.color = stop[1]
        ramp.elements[-1].position = stops[-1][0]
        ramp.elements[-1].color = stops[-1][1]
    return node


def ensure_mixrgb(nodes, name: str, location, blend_type="MIX", factor=1.0):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeMixRGB")
        node.name = name
        node.label = name
    node.location = location
    node.blend_type = blend_type
    node.inputs["Fac"].default_value = factor
    return node


def ensure_wave_texture(nodes, name: str, location, scale: float, distortion: float, detail: float, detail_scale: float):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeTexWave")
        node.name = name
        node.label = name
    node.location = location
    node.wave_type = "BANDS"
    node.bands_direction = "X"
    node.wave_profile = "SIN"
    node.inputs["Scale"].default_value = scale
    node.inputs["Distortion"].default_value = distortion
    node.inputs["Detail"].default_value = detail
    node.inputs["Detail Scale"].default_value = detail_scale
    return node


def ensure_noise_texture(nodes, name: str, location, scale: float, detail: float, roughness: float):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeTexNoise")
        node.name = name
        node.label = name
    node.location = location
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Roughness"].default_value = roughness
    return node


def ensure_bump(nodes, name: str, location, strength: float, distance: float):
    node = nodes.get(name)
    if node is None:
        node = nodes.new("ShaderNodeBump")
        node.name = name
        node.label = name
    node.location = location
    node.inputs["Strength"].default_value = strength
    node.inputs["Distance"].default_value = distance
    return node


def ensure_link(links, from_socket, to_socket):
    for link in links:
        if link.from_socket == from_socket and link.to_socket == to_socket:
            return
    links.new(from_socket, to_socket)


def update_material(mask_name: str):
    mat = bpy.data.materials.get(MAT_NAME)
    if mat is None or not mat.use_nodes:
        raise RuntimeError(f"Material '{MAT_NAME}' not found or not using nodes")

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    fiber_ramp = nodes.get("カラーランプ")
    variation_ramp = nodes.get("カラーランプ.001")
    old_mix = nodes.get("ミックス (旧)")
    cavity_mix = nodes.get("CAVITY_MIX")
    principled = nodes.get("プリンシプルBSDF")
    head_mix = nodes.get("HEAD_MIX")
    mapping = nodes.get("マッピング")
    if not all([fiber_ramp, variation_ramp, old_mix, cavity_mix, principled, head_mix]):
        raise RuntimeError("Expected base material nodes are missing")
    if mapping is None:
        raise RuntimeError("Expected mapping node is missing")

    # Shift the palette closer to PoseManiacs: warm salmon, less dark crimson.
    fr = fiber_ramp.color_ramp
    while len(fr.elements) > 3:
        fr.elements.remove(fr.elements[-1])
    fr.elements[0].position = 0.41
    fr.elements[0].color = (0.90, 0.48, 0.28, 1.0)
    if len(fr.elements) == 2:
        fr.elements.new(0.50)
    fr.elements[1].position = 0.50
    fr.elements[1].color = (0.46, 0.16, 0.09, 1.0)
    fr.elements[2].position = 0.59
    fr.elements[2].color = (0.90, 0.49, 0.29, 1.0)

    vr = variation_ramp.color_ramp
    while len(vr.elements) > 2:
        vr.elements.remove(vr.elements[-1])
    vr.elements[0].position = 0.42
    vr.elements[0].color = (0.72, 0.31, 0.19, 1.0)
    vr.elements[1].position = 0.90
    vr.elements[1].color = (0.96, 0.75, 0.59, 1.0)

    wave_node = nodes.get("波テクスチャ")
    if wave_node:
        wave_node.wave_type = "BANDS"
        wave_node.bands_direction = "X"
        wave_node.wave_profile = "SIN"
        wave_node.inputs["Scale"].default_value = 62.0
        wave_node.inputs["Distortion"].default_value = 0.15
        wave_node.inputs["Detail"].default_value = 5.0
        wave_node.inputs["Detail Scale"].default_value = 1.35

    noise_node = nodes.get("ノイズテクスチャ")
    if noise_node:
        noise_node.inputs["Scale"].default_value = 15.0
        noise_node.inputs["Detail"].default_value = 6.0
        noise_node.inputs["Roughness"].default_value = 0.48

    tendon_attr = ensure_vertex_color_node(nodes, "VERTEX_TENDON_MASK", mask_name, (-140, -360))
    tendon_ramp = ensure_color_ramp(
        nodes,
        "TENDON_MASK_RAMP",
        (80, -360),
        [
            (0.52, (0.0, 0.0, 0.0, 1.0)),
            (0.76, (0.72, 0.72, 0.72, 1.0)),
            (0.94, (1.0, 1.0, 1.0, 1.0)),
        ],
    )
    tendon_color = ensure_rgb_node(nodes, "TENDON_COLOR", (0.94, 0.87, 0.76, 1.0), (80, -520))
    tendon_mix = ensure_mixrgb(nodes, "TENDON_MIX", (300, -380), factor=0.62)
    detail_wave = ensure_wave_texture(nodes, "FIBER_FINE_WAVE", (-520, 140), 124.0, 0.04, 2.0, 1.05)
    detail_noise = ensure_noise_texture(nodes, "FIBER_BREAKUP_NOISE", (-520, -20), 36.0, 8.0, 0.46)
    detail_ramp = ensure_color_ramp(
        nodes,
        "FIBER_FINE_RAMP",
        (-260, 140),
        [
            (0.38, (1.0, 1.0, 1.0, 1.0)),
            (0.50, (0.52, 0.52, 0.52, 1.0)),
            (0.62, (1.0, 1.0, 1.0, 1.0)),
        ],
    )
    breakup_ramp = ensure_color_ramp(
        nodes,
        "FIBER_BREAKUP_RAMP",
        (-260, -20),
        [
            (0.28, (0.0, 0.0, 0.0, 1.0)),
            (0.52, (0.46, 0.46, 0.46, 1.0)),
            (0.78, (1.0, 1.0, 1.0, 1.0)),
        ],
    )
    white_rgb = ensure_rgb_node(nodes, "FIBER_WHITE", (1.0, 1.0, 1.0, 1.0), (-40, -160))
    detail_gate = ensure_mixrgb(nodes, "FIBER_DETAIL_GATE", (-20, 40), factor=1.0)
    detail_multiply = ensure_mixrgb(nodes, "FIBER_DETAIL_MULTIPLY", (150, 40), blend_type="MULTIPLY", factor=1.0)
    fiber_bump = ensure_bump(nodes, "FIBER_BUMP", (350, 120), 0.025, 0.08)

    # Detach old cavity input if needed and insert tendon mix before cavity.
    old_color_socket = old_mix.outputs["Color"]
    cavity_color1 = cavity_mix.inputs["Color1"]
    tendon_color1 = tendon_mix.inputs["Color1"]
    tendon_color2 = tendon_mix.inputs["Color2"]
    tendon_factor = tendon_mix.inputs["Fac"]

    # Remove existing direct link from old mix to cavity mix so the tendon mix sits in the chain.
    for link in list(links):
        if link.from_socket == old_color_socket and link.to_socket == cavity_color1:
            links.remove(link)
        if link.from_socket == old_color_socket and link.to_socket == tendon_color1:
            links.remove(link)

    ensure_link(links, mapping.outputs["Vector"], detail_wave.inputs["Vector"])
    ensure_link(links, mapping.outputs["Vector"], detail_noise.inputs["Vector"])
    ensure_link(links, detail_wave.outputs["Color"], detail_ramp.inputs["Fac"])
    ensure_link(links, detail_noise.outputs["Fac"], breakup_ramp.inputs["Fac"])
    ensure_link(links, breakup_ramp.outputs["Color"], detail_gate.inputs["Fac"])
    ensure_link(links, white_rgb.outputs["Color"], detail_gate.inputs["Color1"])
    ensure_link(links, detail_ramp.outputs["Color"], detail_gate.inputs["Color2"])
    ensure_link(links, old_color_socket, detail_multiply.inputs["Color1"])
    ensure_link(links, detail_gate.outputs["Color"], detail_multiply.inputs["Color2"])
    ensure_link(links, detail_multiply.outputs["Color"], tendon_color1)
    ensure_link(links, tendon_attr.outputs["Color"], tendon_ramp.inputs["Fac"])
    ensure_link(links, tendon_ramp.outputs["Color"], tendon_factor)
    ensure_link(links, tendon_color.outputs["Color"], tendon_color2)
    ensure_link(links, tendon_mix.outputs["Color"], cavity_color1)
    ensure_link(links, detail_gate.outputs["Color"], fiber_bump.inputs["Height"])
    ensure_link(links, fiber_bump.outputs["Normal"], principled.inputs["Normal"])

    # Surface response closer to the flat printed look.
    principled.inputs["Roughness"].default_value = 0.86
    spec_socket_name = "Specular IOR Level" if "Specular IOR Level" in principled.inputs else "Specular"
    principled.inputs[spec_socket_name].default_value = 0.06

    # Slightly warmer skin for the head to match the references.
    skin_node = nodes.get("SKIN_COLOR")
    if skin_node:
        skin_node.outputs["Color"].default_value = (0.93, 0.88, 0.80, 1.0)

    return {
        "roughness": principled.inputs["Roughness"].default_value,
        "specular_input": spec_socket_name,
        "specular_value": principled.inputs[spec_socket_name].default_value,
    }


def main():
    obj = bpy.data.objects.get(OBJ_NAME)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Object '{OBJ_NAME}' not found")

    mask_stats = generate_tendon_mask(obj, UV_NAME, MASK_NAME)
    material_stats = update_material(MASK_NAME)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "object": OBJ_NAME,
        "material": MAT_NAME,
        "mask_name": MASK_NAME,
        "mask_stats": mask_stats,
        "material_stats": material_stats,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
