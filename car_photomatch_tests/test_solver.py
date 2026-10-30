import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'car_photomatch'))
import solver


def aim_camera(center, target):
    forward = np.asarray(target, float) - np.asarray(center, float)
    forward /= np.linalg.norm(forward)
    upref = np.array([0., 0., 1.])
    right = np.cross(forward, upref); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return np.column_stack([right, up, -forward])


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(81)
        self.points = self.rng.uniform([-2.2, -.85, .15], [2.2, .85, 1.55], (16, 3))
        self.center = np.array([6., -9., 3.4])
        self.rot = aim_camera(self.center, [0., 0., .8])
        self.w, self.h = 1600, 900
        self.lens = 53.
        self.fxx = self.w * 53 / 36.
        self.fyy = self.fxx
        self.uv, depth = solver.project(self.points, self.center, self.rot, self.fxx, self.fyy, self.w / 2, self.h / 2)
        assert np.all(depth > 0)

    def test_projection_look_at(self):
        p, d = solver.project(np.array([[0., 0., .8]]), self.center, self.rot, self.fxx, self.fyy, 800, 450)
        np.testing.assert_allclose(p, np.array([[800, 450]]), atol=1e-7)
        self.assertTrue(d[0] > 0)

    def test_dlt(self):
        pose = solver.dlt_initialization(self.points, self.uv, self.fxx, self.fyy, 800, 450)
        self.assertIsNotNone(pose)
        np.testing.assert_allclose(pose[0], self.center, atol=1e-5)
        np.testing.assert_allclose(pose[1], self.rot, atol=1e-5)

    def test_solve_unknown_lens(self):
        result = solver.solve_camera(self.points, self.uv, np.ones(len(self.points)),
                      np.array([4., -8., 2.]), aim_camera([4., -8., 2.], [0,0,.7]),
                      35., self.w * 35 / 36., self.w * 35 / 36., 800, 450)
        self.assertLess(result['rmse'], .01)
        self.assertAlmostEqual(result['lens'], self.lens, places=2)
        np.testing.assert_allclose(result['center'], self.center, atol=.001)

    def test_solve_noisy(self):
        pixel_noise = self.uv + self.rng.normal(0, .75, self.uv.shape)
        result = solver.solve_camera(self.points, pixel_noise, np.ones(len(self.points)),
                     self.center, self.rot, 45., self.w*45 / 36, self.w*45 / 36, 800, 450)
        self.assertLess(result['rmse'], 2.5)
        self.assertLess(abs(result['lens'] - self.lens), 2.)

    def test_planar_with_good_seed(self):
        pts = self.points.copy(); pts[:,2] = 0.7
        uv, _ = solver.project(pts, self.center, self.rot, self.fxx, self.fyy, 800, 450)
        result = solver.solve_camera(pts, uv, np.ones(len(pts)),
                     self.center + [.1, -.1, .1], self.rot, 52.,
                     self.w*52/36, self.w*52/36, 800, 450)
        self.assertLess(result['rmse'], .01)

    def test_locked_lens(self):
        start_center = self.center + [.3, -.3, .1]
        result = solver.solve_camera(self.points, self.uv, np.ones(len(self.points)),
                      start_center, self.rot, self.lens, self.fxx, self.fyy,
                      800, 450, lock_lens=True)
        self.assertAlmostEqual(result['lens'], self.lens)
        self.assertLess(result['rmse'], .01)

    def test_outlier_resistance(self):
        observed = self.uv + self.rng.normal(0, .6, self.uv.shape)
        observed[3] += [85, -120]
        result = solver.solve_camera(self.points, observed, np.ones(len(self.points)),
                      self.center, self.rot, 45., self.w*45/36., self.w*45/36.,
                      800, 450, huber_px=8.)
        self.assertLess(abs(result['lens'] - self.lens), 3.)
        self.assertLess(np.median(result['per_point_error']), 3.)

    def test_invalid_points(self):
        with self.assertRaises(solver.SolveError):
            solver.solve_camera(self.points[:5], self.uv[:5], np.ones(5),
                    self.center, self.rot, self.lens, self.fxx, self.fyy, 800, 450)


if __name__ == '__main__':
    unittest.main()
