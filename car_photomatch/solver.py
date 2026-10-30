# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure NumPy perspective camera solver for Car PhotoMatch.

Camera rotation maps camera-local coordinates into world coordinates.
Blender cameras look along -Z, with +X right and +Y up.
Image coordinates are (x right, y down), in pixels.
"""
import math
import numpy as np


class SolveError(ValueError):
    pass


def so3_exp(w):
    """Convert a small rotation vector to a right-handed rotation matrix."""
    theta = float(np.linalg.norm(w))
    if theta < 1e-12:
        return np.eye(3)
    k = np.asarray(w, dtype=float) / theta
    kx, ky, kz = k
    K = np.array([[0., -kz, ky], [kz, 0., -kx], [-ky, kx, 0.]])
    return np.eye(3) + math.sin(theta) * K + (1. - math.cos(theta)) * K @ K


# Rcv maps world offset to camera (right, DOWN, forward) coordinates.
_CAM_FLIP = np.diag([1., -1., -1.])


def blender_to_cv_rotation(rotation_world):
    return _CAM_FLIP @ np.asarray(rotation_world, dtype=float).T


def cv_to_blender_rotation(rotation_cv):
    return np.asarray(rotation_cv, dtype=float).T @ _CAM_FLIP


def project(points, center, rotation_world, focal_px_x, focal_px_y, cx, cy):
    """Return pixel predictions (top-left origin) and signed forward depths."""
    Rcv = blender_to_cv_rotation(rotation_world)
    local = (np.asarray(points, dtype=float) - center) @ Rcv.T
    depth = local[:, 2]
    safe_z = np.where(np.abs(depth) < 1e-8, np.where(depth < 0, -1e-8, 1e-8), depth)
    x = focal_px_x * (local[:, 0] / safe_z) + cx
    y = focal_px_y * (local[:, 1] / safe_z) + cy
    return np.column_stack((x, y)), depth


def dlt_initialization(points, pixels, fx, fy, cx, cy):
    """Estimate world-to-camera pose with normalized DLT.

    Needs 6+ non-coplanar points. Does not estimate lens itself.
    Returns (center, world_rotation) or None if degenerate.
    """
    pts = np.asarray(points, dtype=float)
    uv = np.asarray(pixels, dtype=float)
    if len(pts) < 6:
        return None
    centroid = pts.mean(axis=0)
    scale = float(np.sqrt(np.mean(np.sum((pts - centroid) ** 2, axis=1))))
    if scale < 1e-7:
        return None
    X = np.column_stack(((pts - centroid) / scale, np.ones(len(pts))))
    xy = np.column_stack(((uv[:, 0] - cx) / fx, (uv[:, 1] - cy) / fy))
    A = np.zeros((2 * len(pts), 12), dtype=float)
    A[0::2, :4] = X
    A[1::2, 4:8] = X
    A[0::2, 8:] = -xy[:, 0, None] * X
    A[1::2, 8:] = -xy[:, 1, None] * X
    try:
        _, sing, vt = np.linalg.svd(A, full_matrices=False)
        # If the design matrix is rank deficient, its nullspace is not unique.
        if len(sing) < 12 or sing[-2] < sing[0] * 1e-10:
            return None
        P = vt[-1].reshape(3, 4)
        M = P[:, :3]
        if np.linalg.det(M) < 0:
            P = -P
            M = -M
        U, vals, Vt = np.linalg.svd(M)
        Rcv = U @ Vt
        if np.linalg.det(Rcv) < 0:
            return None
        if vals[-1] < 1e-12 or vals[0] / vals[-1] > 30:
            return None
        t = P[:, 3] / float(np.mean(vals))
        center = centroid - scale * (Rcv.T @ t)
        Rworld = cv_to_blender_rotation(Rcv)
        _, depth = project(pts, center, Rworld, fx, fy, cx, cy)
        if np.sum(depth > 0) < max(6, math.ceil(.8 * len(pts))):
            return None
        return center, Rworld
    except np.linalg.LinAlgError:
        return None


def robust_cost(pred, obs, weights, huber_px):
    dist = np.linalg.norm(pred - obs, axis=1)
    # Huber with half-squared interior to yield stable LM minimization.
    rho = np.where(dist <= huber_px, 0.5 * dist * dist,
                   huber_px * (dist - 0.5 * huber_px))
    return float(np.sum(weights * rho))


def optimize(points, pixels, weights, seed_center, seed_rotation, seed_lens,
             base_fx, base_fy, cx, cy, lock_lens=False,
             huber_px=12., max_iterations=80):
    """Damped Gauss-Newton/IRLS solve, with finite-difference Jacobian.

    base_fx and base_fy are pixels of focal length for seed_lens.
    Camera pose is optimized with a locally parameterized SO(3) rotation.
    """
    points = np.asarray(points, dtype=float)
    pixels = np.asarray(pixels, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if len(points) < (4 if lock_lens else 6):
        raise SolveError('Not enough complete, enabled point pairs')
    span = float(np.max(np.ptp(points, axis=0)))
    if span < 1e-8:
        raise SolveError('3D points have no spatial extent')
    nparams = 6 if lock_lens else 7
    seed_center = np.asarray(seed_center, dtype=float)
    seed_rotation = np.asarray(seed_rotation, dtype=float)
    x = np.zeros(nparams, dtype=float)
    damping = .01
    max_lens = 300.0
    min_lens = 8.0

    def evaluate(parameters):
        C = seed_center + span * parameters[:3]
        R = so3_exp(parameters[3:6]) @ seed_rotation
        lens = seed_lens * math.exp(float(parameters[6])) if not lock_lens else seed_lens
        fx, fy = base_fx * lens / seed_lens, base_fy * lens / seed_lens
        prediction, depths = project(points, C, R, fx, fy, cx, cy)
        if np.any(depths <= 1e-7 * span) or not np.all(np.isfinite(prediction)):
            return None
        return prediction, C, R, lens

    ev = evaluate(x)
    if ev is None:
        return None
    for _ in range(max_iterations):
        pred = ev[0]
        error = pred - pixels
        norm = np.linalg.norm(error, axis=1)
        huber_weights = weights * np.minimum(1., huber_px / np.maximum(norm, 1e-9))
        w = np.sqrt(huber_weights.repeat(2))
        residual = error.reshape(-1) * w
        J = np.zeros((len(residual), nparams), dtype=float)
        for j in range(nparams):
            step = 1e-5
            xd = x.copy()
            xd[j] += step
            trial = evaluate(xd)
            if trial is None:
                xd[j] -= 2 * step
                trial = evaluate(xd)
                if trial is None:
                    return None
                J[:, j] = ((pred - trial[0]).reshape(-1) / step) * w
            else:
                J[:, j] = ((trial[0] - pred).reshape(-1) / step) * w
        H = J.T @ J
        g = J.T @ residual
        cost = robust_cost(pred, pixels, weights, huber_px)
        accepted = False
        for _retry in range(12):
            try:
                diag = np.maximum(np.diag(H), 1e-7)
                delta = np.linalg.solve(H + damping * np.diag(diag), -g)
            except np.linalg.LinAlgError:
                return None
            test_x = x + delta
            if not lock_lens:
                test_lens = seed_lens * math.exp(float(np.clip(test_x[6], -12., 12.)))
                if not min_lens <= test_lens <= max_lens:
                    damping *= 5.
                    continue
            test_ev = evaluate(test_x)
            if test_ev is not None and robust_cost(test_ev[0], pixels, weights, huber_px) < cost:
                x = test_x
                ev = test_ev
                accepted = True
                damping = max(damping * .35, 1e-7)
                break
            damping = min(damping * 5., 1e12)
        if not accepted or np.linalg.norm(delta) < 1e-8:
            break
    pred, C, R, lens = ev
    error = np.linalg.norm(pred - pixels, axis=1)
    rmse = float(np.sqrt(np.mean(error * error)))
    return dict(center=C, rotation=R, lens=float(lens), rmse=rmse,
                per_point_error=error, robust_cost=robust_cost(pred, pixels, weights, huber_px))


def solve_camera(points, pixels, weights, current_center, current_rotation,
                 current_lens, base_fx, base_fy, cx, cy, lock_lens=False,
                 huber_px=12., max_iterations=80):
    """Solve against camera seed and (when possible) a DLT-derived seed.

    Inputs use Blender world coordinates and photo pixels with top-left origin.
    base_fx/fy describe current_lens and must reflect Blender's camera frame.
    """
    points = np.asarray(points, dtype=float)
    pixels = np.asarray(pixels, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or pixels.shape != (len(points), 2):
        raise SolveError('Invalid 3D/2D correspondence arrays')
    if len(points) < 6:
        raise SolveError('At least 6 complete point pairs are required')
    if np.linalg.matrix_rank(points - points.mean(axis=0), tol=1e-7) < 2:
        raise SolveError('3D points must not be collinear')
    if np.any(~np.isfinite(points)) or np.any(~np.isfinite(pixels)):
        raise SolveError('Point coordinates must be finite')
    if np.any(weights <= 0) or np.any(~np.isfinite(weights)):
        raise SolveError('Weights must be positive')

    candidates = [(np.asarray(current_center, dtype=float),
                   np.asarray(current_rotation, dtype=float), float(current_lens))]
    if np.linalg.matrix_rank(points - points.mean(axis=0), tol=1e-7) == 3:
        for lens in ([current_lens] if lock_lens else [24., 35., 50., 85., float(current_lens)]):
            estimate = dlt_initialization(points, pixels,
                                          base_fx * lens / current_lens,
                                          base_fy * lens / current_lens, cx, cy)
            if estimate is not None:
                candidates.append((*estimate, float(lens)))

    best = None
    for C, R, lens in candidates:
        result = optimize(points, pixels, weights, C, R, lens,
                          base_fx * lens / current_lens,
                          base_fy * lens / current_lens, cx, cy,
                          lock_lens=lock_lens, huber_px=huber_px,
                          max_iterations=max_iterations)
        if result is not None and (best is None or result['robust_cost'] < best['robust_cost']):
            best = result
    if best is None:
        raise SolveError('Could not initialize the camera. Aim the camera roughly toward the car, or add landmarks at different depths and heights.')
    return best
