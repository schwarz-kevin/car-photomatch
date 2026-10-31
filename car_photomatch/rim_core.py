# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure-NumPy experimental rim-edge and fixed-focal-length circle pose tools.

Image convention: top-left pixel origin, +X right, +Y down.
3D construction circle: XY plane, normal +Z, units in metres.
No Blender or OpenCV dependency, so functions can be tested independently.

An image ellipse and nominal rim size do NOT uniquely recover a camera when
focal length / photographed edge diameter / geometric depth are uncertain.
"""

import math
import numpy as np


class RimSolveError(ValueError):
    pass


def ellipse_points(ellipse, n=120):
    """Ellipse (cx,cy,major_radius,minor_radius,major_angle_rad)."""
    cx, cy, a, b, angle = map(float, ellipse)
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    c, s = math.cos(angle), math.sin(angle)
    return np.stack((cx + a * np.cos(t) * c - b * np.sin(t) * s,
                     cy + a * np.cos(t) * s + b * np.sin(t) * c), axis=1)


def fit_ellipse(points):
    """Algebraic direct least-squares ellipse fit (Fitzgibbon / Halir-Flusser).

    Returns center, major/minor radii and major-axis angle. Rejects degenerate
    samples rather than returning fake circles or hyperbolas.
    """
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 6 or not np.all(np.isfinite(p)):
        raise RimSolveError('At least six finite ellipse points required')
    center = p.mean(axis=0)
    scale = max(float(np.std(p[:, 0])), float(np.std(p[:, 1])), 1e-9)
    x, y = ((p - center) / scale).T
    D1 = np.stack((x * x, x * y, y * y), axis=1)
    D2 = np.stack((x, y, np.ones_like(x)), axis=1)
    S1, S2, S3 = D1.T @ D1, D1.T @ D2, D2.T @ D2
    try:
        T = -np.linalg.solve(S3, S2.T)
        M = S1 + S2 @ T
        Cinv = np.array([[0., 0., .5], [0., -1., 0.], [.5, 0., 0.]])
        ev, vecs = np.linalg.eig(Cinv @ M)
        solutions = []
        for k in range(3):
            v = vecs[:, k]
            if abs(v.imag).max() > 1e-7:
                continue
            a, b, c = v.real
            if 4*a*c - b*b > 1e-8:
                solutions.append(np.concatenate([v.real, T @ v.real]))
        if not solutions:
            raise RimSolveError('No valid ellipse')
        A, B, C, D, E, F = solutions[0]
        Q = np.array([[A, B / 2.], [B / 2., C]])
        q = np.array([D, E]) / 2.
        loc = -np.linalg.solve(Q, q)
        v = float(loc @ Q @ loc - F)
        lam, axes = np.linalg.eigh(Q)
        sizes2 = v / lam
        if not np.all(sizes2 > 0) or not np.all(np.isfinite(sizes2)):
            raise RimSolveError('Non-elliptic conic')
        radii = np.sqrt(sizes2)
        main = int(np.argmax(radii))
        a0, b0 = float(radii[main] * scale), float(radii[1-main] * scale)
        angle = math.atan2(axes[1, main], axes[0, main]) % math.pi
        if min(a0, b0) < 1 or max(a0, b0) > 1e7:
            raise RimSolveError('Implausible ellipse dimensions')
        cx, cy = loc * scale + center
        return (float(cx), float(cy), a0, b0, angle)
    except (np.linalg.LinAlgError, FloatingPointError) as exc:
        raise RimSolveError('Ellipse fitting failed: degenerate edge points') from exc


def _gray(image):
    p = np.asarray(image)
    if p.ndim == 2:
        return p.astype(np.float32, copy=False)
    if p.ndim != 3 or p.shape[2] < 3:
        raise RimSolveError('Expected grayscale, RGB or RGBA image')
    return (p[..., 0]*.2126 + p[..., 1]*.7152 + p[..., 2]*.0722).astype(np.float32)


def _gradients(im):
    # Small separable blur reduces aliasing; Sobel derivative with zero-padding
    # avoided to prevent spurious strong edges around the crop boundary.
    g = np.pad(im, 1, mode='reflect')
    for axis in (0, 1):
        g = (np.take(g, range(0, g.shape[axis]-2), axis=axis) +
             2*np.take(g, range(1, g.shape[axis]-1), axis=axis) +
             np.take(g, range(2, g.shape[axis]), axis=axis)) / 4.
    a = np.pad(g, 1, mode='reflect')
    gx = (a[:-2, 2:] + 2*a[1:-1, 2:] + a[2:, 2:] -
          a[:-2, :-2] - 2*a[1:-1, :-2] - a[2:, :-2]) / 8.
    gy = (a[2:, :-2] + 2*a[2:, 1:-1] + a[2:, 2:] -
          a[:-2, :-2] - 2*a[:-2, 1:-1] - a[:-2, 2:]) / 8.
    return np.hypot(gx, gy)


def _sample(arr, x, y):
    h, w = arr.shape
    x = np.clip(x, 0., w-1.00001)
    y = np.clip(y, 0., h-1.00001)
    x0 = x.astype(np.int32)
    y0 = y.astype(np.int32)
    dx, dy = x-x0, y-y0
    return ((1-dx)*(1-dy)*arr[y0, x0] + dx*(1-dy)*arr[y0, x0+1] +
            (1-dx)*dy*arr[y0+1, x0] + dx*dy*arr[y0+1, x0+1])


def _edge_samples(gradient, ellipse, search_px=15, count=84):
    """Search on the normal to a trial ellipse, preferring nearby strong edges."""
    cx, cy, a, b, angle = ellipse
    t = np.linspace(0., 2*np.pi, count, endpoint=False)
    ca, sa = math.cos(angle), math.sin(angle)
    x = cx + a*np.cos(t)*ca - b*np.sin(t)*sa
    y = cy + a*np.cos(t)*sa + b*np.sin(t)*ca
    nx = (np.cos(t)/a)*ca - (np.sin(t)/b)*sa
    ny = (np.cos(t)/a)*sa + (np.sin(t)/b)*ca
    length = np.hypot(nx, ny)
    nx, ny = nx/length, ny/length
    offsets = np.linspace(-search_px, search_px, 41)
    xx = x[:, None] + nx[:, None]*offsets[None, :]
    yy = y[:, None] + ny[:, None]*offsets[None, :]
    magnitude = _sample(gradient, xx, yy)
    # Prefer a visible edge close to the starting contour, not a distant spoke.
    scores = magnitude * (0.72 + .28*np.exp(-.5*(offsets / max(search_px*.55, 1))**2))[None, :]
    ix = np.argmax(scores, axis=1)
    idx = np.arange(len(t))
    px, py = xx[idx, ix], yy[idx, ix]
    return np.stack((px, py), axis=1), magnitude[idx, ix]


def detect_ellipse_candidates(image, roi=None, max_side=620, max_candidates=5):
    """Find POSSIBLE ring edges in a user-selected image rectangle.

    Experimental gradient-guided multi-seed refinement. No machine-learning or
    OpenCV dependency. Returns scored, distinct ellipses in FULL image pixels.
    The user must verify the correct physical edge; no automatic claim of truth.

    ROI convention: left/top/right/bottom in top-left image pixel coordinates.
    """
    im = _gray(image)
    h, w = im.shape
    if roi is None:
        roi = (0, 0, w, h)
    l, t, r, b = [int(round(float(v))) for v in roi]
    l, r = max(l, 0), min(r, w)
    t, b = max(t, 0), min(b, h)
    if r-l < 45 or b-t < 45:
        raise RimSolveError('Drag a larger rectangle around the rim')
    stride = max(1, int(math.ceil(max(r-l, b-t) / max_side)))
    small = im[t:b:stride, l:r:stride]
    mag = _gradients(small)
    sh, sw = small.shape
    # Ignore frame edges (crop/window borders often create very strong gradients).
    mag[:3] = mag[-3:] = 0
    mag[:, :3] = mag[:, -3:] = 0
    contrast = float(np.percentile(mag, 97))
    if contrast < 1e-4:
        raise RimSolveError('No visible edges inside selected area')
    roi_cx, roi_cy = (sw-1)/2, (sh-1)/2
    generated = []
    for size in (0.94, 0.82, 0.70, 0.58, 0.46):
        for xshift, yshift in ((0, 0), (-.055, 0), (.055, 0), (0, -.055), (0, .055)):
            el = (roi_cx + xshift*sw, roi_cy+yshift*sh, sw*.49*size, sh*.49*size, 0.)
            for step in range(4):
                search = max(3., min(sw, sh) * (.072 if step==0 else .035))
                picks, strengths = _edge_samples(mag, el, search_px=search)
                enough = strengths > contrast*.12
                if enough.sum() < 35:
                    break
                try:
                    new = fit_ellipse(picks[enough])
                except RimSolveError:
                    break
                # Stop if fitted contour drifts too far away from the user box.
                if (not 0 <= new[0] <= sw or not 0 <= new[1] <= sh or
                    new[2] > sw*1.2 or new[3] > sh*1.2 or new[3] < 4):
                    break
                el = new
            else:
                pts = ellipse_points(el, n=160)
                strengths = _sample(mag, pts[:, 0], pts[:, 1])
                coverage = float(np.mean(strengths > contrast*.17))
                edge_strength = float(np.mean(np.minimum(strengths / max(contrast, 1e-6), 2.)))
                # Penalize contours that go outside the ROI.
                inside = float(np.mean((pts[:, 0] > 2) & (pts[:, 0] < sw-3) &
                                       (pts[:, 1] > 2) & (pts[:, 1] < sh-3)))
                score = coverage*.65 + min(edge_strength, 1.)*.35
                score *= inside
                if coverage > .22 and inside > .75:
                    generated.append((score, el))
    generated.sort(key=lambda q: q[0], reverse=True)
    unique = []
    for score, (cx, cy, a, b, ang) in generated:
        el = (l+stride*cx, t+stride*cy, a*stride, b*stride, ang)
        if any(abs(el[0]-old[0]) < max(4, el[2]*.055) and
               abs(el[1]-old[1]) < max(4, el[3]*.055) and
               abs(el[2]-old[2]) < max(4, el[2]*.075) and
               abs(el[3]-old[3]) < max(4, el[3]*.075) for old, _ in unique):
            continue
        unique.append((el, float(score)))
        if len(unique) >= max_candidates:
            break
    return unique


def _rotation_from_normal(n):
    """World XYZ normal (0,0,1) maps into conventional CV camera coordinates n."""
    n = np.asarray(n, dtype=float)
    n /= np.linalg.norm(n)
    base = np.array([0., 0., 1.])
    v = np.cross(base, n)
    sine = np.linalg.norm(v)
    cosine = float(base @ n)
    if sine < 1e-10:
        return np.eye(3) if cosine > 0 else np.diag([1., -1., -1.])
    K = np.array([[0., -v[2], v[1]], [v[2], 0., -v[0]], [-v[1], v[0], 0.]])
    return np.eye(3) + K + K@K*((1.-cosine)/(sine*sine))


def _pose(parameters, fx, fy, cx, cy):
    tilt, azimuth, log_depth, u0, v0 = parameters
    depth = math.exp(float(log_depth))
    normal = np.array([math.sin(tilt)*math.cos(azimuth),
                       math.sin(tilt)*math.sin(azimuth), -math.cos(tilt)])
    R = _rotation_from_normal(normal)
    object_center_cam = np.array([(u0-cx)/fx*depth, (v0-cy)/fy*depth, depth])
    C = -(R.T @ object_center_cam)
    return C, R


def project_circle(params, radius_m, fx, fy, cx, cy, count=96):
    C, R = _pose(params, fx, fy, cx, cy)
    angles = np.arange(count) * (2.*math.pi/count)
    pts = np.stack((radius_m * np.cos(angles), radius_m * np.sin(angles),
                    np.zeros_like(angles)), axis=1)
    pc = (pts - C) @ R.T
    if float(pc[:, 2].min()) < 1e-4:
        raise RimSolveError('Camera intersects or falls behind the selected ring')
    return np.stack((fx*pc[:, 0]/pc[:, 2]+cx, fy*pc[:, 1]/pc[:, 2]+cy), axis=1)


def _residual(parameters, ellipse, radius, fx, fy, cx, cy):
    try:
        pts = project_circle(parameters, radius, fx, fy, cx, cy, 96)
    except (RimSolveError, OverflowError, ValueError):
        return np.full(96, 1e5)
    ex, ey, a, b, angle = ellipse
    dx, dy = pts[:, 0]-ex, pts[:, 1]-ey
    c, s = math.cos(angle), math.sin(angle)
    localx, localy = (c*dx+s*dy)/a, (-s*dx+c*dy)/b
    return (np.hypot(localx, localy)-1.) * min(a, b)


def _lm(initial, ellipse, radius, fx, fy, cx, cy, iterations):
    p = np.array(initial, dtype=float)
    damping = .01
    residual = _residual(p, ellipse, radius, fx, fy, cx, cy)
    best = float(residual @ residual)
    for _ in range(iterations):
        cols = []
        for i, epsilon in enumerate((1e-5, 1e-5, 1e-5, .05, .05)):
            new = p.copy()
            new[i] += epsilon
            cols.append((_residual(new, ellipse, radius, fx, fy, cx, cy)-residual)/epsilon)
        J = np.stack(cols, axis=1)
        H = J.T @ J
        try:
            delta = np.linalg.solve(H + np.diag(np.maximum(H.diagonal(), 1.)*damping), -J.T @ residual)
        except np.linalg.LinAlgError:
            break
        candidate = p + delta
        candidate[0] = np.clip(candidate[0], .00001, 1.55)
        candidate[2] = np.clip(candidate[2], math.log(radius*.25), math.log(radius*100000))
        candidate[3] = np.clip(candidate[3], cx-4*fx, cx+4*fx)
        candidate[4] = np.clip(candidate[4], cy-4*fy, cy+4*fy)
        r2 = _residual(candidate, ellipse, radius, fx, fy, cx, cy)
        cost = float(r2 @ r2)
        if cost < best:
            p, residual, best = candidate, r2, cost
            damping = max(damping*.45, 1e-7)
            if float(np.linalg.norm(delta)) < 1e-7:
                break
        else:
            damping = min(damping*8., 1e6)
            if damping >= 1e6:
                break
    return p, math.sqrt(best / len(residual))


def solve_circle_camera_candidates(ellipse, diameter_mm, fx, fy, cx, cy, iterations=80):
    """Fixed-intrinsics pose estimates from a *known* physical planar circle.

    Multiple candidate solutions are returned, because a single observed circle
    can yield multiple orientations and unknown lens distortion may bias both.
    Normal points toward the camera, and ring sits in world XY at z=0.
    Results map to Blender camera via world_to_cv rotation matrices.
    """
    ex, ey, a, b, angle = map(float, ellipse)
    if min(a, b, diameter_mm, fx, fy) <= 0 or b > a or not np.all(np.isfinite(ellipse)):
        raise RimSolveError('Invalid ellipse, ring diameter, or camera calibration')
    radius = diameter_mm / 2000.
    tilt = math.acos(float(np.clip(b / a, .01, .99999)))
    depth = max(fx, fy) * radius / a
    if depth <= radius*.5:
        raise RimSolveError('Implausible ring diameter / focal length combination')
    candidates = []
    # Initial normal azimuths are along the *minor* ellipse axis, both signs.
    for az in (angle + math.pi/2., angle-math.pi/2.):
        initial = [max(.02, tilt), az, math.log(depth), ex, ey]
        p, err = _lm(initial, (ex,ey,a,b,angle), radius, fx,fy,cx,cy,iterations)
        camera_pos, R = _pose(p, fx,fy,cx,cy)
        # Convert CV camera (+Y down +Z forward) to Blender (+Y up -Z forward).
        blender_matrix = R.T @ np.diag([1., -1., -1.])
        camera = {
            'center': camera_pos,
            'blender_rotation': blender_matrix,
            'error_px': float(err),
            'inclination_deg': math.degrees(float(p[0])),
            'normal_camera': np.array([math.sin(p[0])*math.cos(p[1]),
                                       math.sin(p[0])*math.sin(p[1]), -math.cos(p[0])]),
            'parameters': p,
        }
        if math.isfinite(err):
            candidates.append(camera)
    candidates.sort(key=lambda p: p['error_px'])
    if not candidates or candidates[0]['error_px'] > max(15., .15*b):
        raise RimSolveError('Unable to fit a credible camera to this ellipse; check focal length and edge diameter')
    return candidates
