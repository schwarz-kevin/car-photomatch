# SPDX-License-Identifier: GPL-3.0-or-later
"""Dependency-free geometry helpers for Rim PhotoMatch construction meshes.

Coordinates are local to the rig root: wheel face in XY, axle in Z.
One mesh is returned, containing disconnected closed edge loops.
"""

import math


def lug_guide_mesh(count, pcd_radius, hole_radius, segments, z=0.0):
    """Generate evenly spaced lug-hole guide circles as one edge-only mesh.

    Radii and z are in Blender units (meters in the Rim PhotoMatch rig).
    Returns (vertices, edges) suitable for Mesh.from_pydata(..., ..., []).
    Each hole forms one independent closed loop; no faces are generated.
    First hole center is on local +X, then counterclockwise in XY.
    """
    count = int(count)
    segments = int(segments)
    if not 3 <= count <= 12:
        raise ValueError('Bolt count must be between 3 and 12')
    if not 6 <= segments <= 256:
        raise ValueError('Lug vertices must be between 6 and 256')
    if not (math.isfinite(pcd_radius) and math.isfinite(hole_radius) and math.isfinite(z)):
        raise ValueError('Lug guide dimensions must be finite')
    if pcd_radius <= 0 or hole_radius <= 0:
        raise ValueError('Lug guide radii must be positive')

    vertices = []
    edges = []
    for lug_index in range(count):
        phi = 2.0 * math.pi * lug_index / count
        cx = pcd_radius * math.cos(phi)
        cy = pcd_radius * math.sin(phi)
        start = len(vertices)
        for vertex_index in range(segments):
            angle = 2.0 * math.pi * vertex_index / segments
            vertices.append((
                cx + hole_radius * math.cos(angle),
                cy + hole_radius * math.sin(angle),
                float(z),
            ))
            edges.append((start + vertex_index,
                          start + (vertex_index + 1) % segments))
    return vertices, edges




def effective_photo_ring_diameter_mm(nominal_diameter_in, ring_type,
                                     center_bore_mm=66.6,
                                     manual_edge_diameter_mm=500.0,
                                     override=False):
    """Resolve ring scale without requiring a separate diameter input.

    Returns (diameter_mm, accuracy). The nominal size is precisely the bead
    seat diameter, not the photographed metal lip diameter. A lip or an
    unidentified ring therefore uses nominal size only as an EXPLICIT
    approximation; the camera's physical scale then remains approximate.
    """
    for v in (nominal_diameter_in, center_bore_mm, manual_edge_diameter_mm):
        if not math.isfinite(float(v)) or float(v) <= 0:
            raise ValueError('Rim diameter values must be positive and finite')
    if override:
        return float(manual_edge_diameter_mm), 'OVERRIDE'
    bead_mm = float(nominal_diameter_in) * 25.4
    if ring_type in {'FRONT_BEAD', 'REAR_BEAD'}:
        return bead_mm, 'EXACT_BEAD'
    if ring_type == 'CENTER_BORE':
        return float(center_bore_mm), 'CENTER_BORE'
    if ring_type == 'HUB_FACE':
        # Only accurate if the selected edge is indeed the center bore.
        return float(center_bore_mm), 'ASSUMED_CENTER_BORE'
    if ring_type in {'FRONT_LIP', 'REAR_LIP', 'MANUAL'}:
        return bead_mm, 'APPROX_BEAD'
    raise ValueError(f'Unknown photo ring type: {ring_type}')

def photo_ring_front_bead_z_mm(width_in, offset_et_mm, ring_type='MANUAL',
                               lip_overhang_mm=12.0, manual_z_mm=-12.0):
    """Locate front/outboard bead seat relative to the selected PHOTO ring (Z=0).

    +Z points outboard. Rim width is the bead-seat-to-bead-seat measurement.
    Outer/front and inner/rear lip distances are NOT defined by nominal width:
    the user must measure or estimate the axial lip overhang.

    MANUAL preserves v0.4.6's per-scene manual bead seat offset on upgrade.
    """
    vals = (width_in, offset_et_mm, lip_overhang_mm, manual_z_mm)
    if not all(math.isfinite(float(x)) for x in vals):
        raise ValueError('Reference dimensions must be finite')
    if width_in <= 0:
        raise ValueError('Rim width must be positive')
    if lip_overhang_mm < 0:
        raise ValueError('Lip overhang must not be negative')
    width_mm = float(width_in) * 25.4
    mapping = {
        'MANUAL': float(manual_z_mm),
        'FRONT_BEAD': 0.0,
        'REAR_BEAD': width_mm,
        'FRONT_LIP': -float(lip_overhang_mm),
        'REAR_LIP': width_mm + float(lip_overhang_mm),
        'HUB_FACE': width_mm / 2.0 - float(offset_et_mm),
        'CENTER_BORE': width_mm / 2.0 - float(offset_et_mm),
    }
    if ring_type not in mapping:
        raise ValueError(f'Unknown photo ring reference: {ring_type}')
    return mapping[ring_type]


def mounting_face_z_m(width_in, offset_et_mm, front_bead_seat_z_mm=-12.0):
    """Hub mounting-face Z in local rig meters.

    The selected photographed circle defines Z=0. The wheel faces toward +Z.
    The true wheel-width measurement is between bead-seat planes, *not* the
    outside lips. A signed distance locates the front bead-seat plane with
    respect to the chosen photo ring. Positive ET puts the mounting face
    toward the outside face; negative ET moves it inboard.
    """
    values = (width_in, offset_et_mm, front_bead_seat_z_mm)
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError('Wheel dimensions and ET must be finite')
    if width_in <= 0:
        raise ValueError('Wheel width must be positive')
    width_mm = float(width_in) * 25.4
    return (float(front_bead_seat_z_mm) - width_mm / 2.0 + float(offset_et_mm)) / 1000.0


def circle_edge_loop(radius, segments, z=0.0):
    """One closed XY edge loop at specified Z, without faces."""
    segments = int(segments)
    if not 6 <= segments <= 512:
        raise ValueError('Guide vertices must be between 6 and 512')
    if not all(math.isfinite(float(x)) for x in (radius, z)) or radius <= 0:
        raise ValueError('Guide radius must be positive and dimensions finite')
    verts = [(float(radius)*math.cos(math.tau * i / segments),
              float(radius)*math.sin(math.tau * i / segments), float(z))
             for i in range(segments)]
    edges = [(i, (i+1) % segments) for i in range(segments)]
    return verts, edges
