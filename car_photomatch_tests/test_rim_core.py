"""Synthetic numerical tests. Blender integration still needs testing in Blender 5.2."""
import math
import pathlib
import sys
import unittest
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'car_photomatch'))
import rim_core as rc


class RimCoreTests(unittest.TestCase):
    def test_fit_ellipse_rotated(self):
        original = (450., 320., 190., 106., math.radians(25))
        fitted = rc.fit_ellipse(rc.ellipse_points(original, 180))
        np.testing.assert_allclose(fitted[:4], original[:4], atol=1e-6)
        self.assertLess(abs(math.sin(fitted[4]-original[4])), 1e-6)

    def test_invalid_ellipse(self):
        with self.assertRaises(rc.RimSolveError):
            rc.fit_ellipse(np.zeros((15,2)))

    def test_camera_pose_projection(self):
        p = [.6, 1.1, math.log(1.8), 515., 320.]
        projected = rc.project_circle(p, .25, 1667., 1667., 600., 400., 180)
        observed = rc.fit_ellipse(projected)
        solutions = rc.solve_circle_camera_candidates(observed, 500., 1667., 1667., 600., 400.)
        self.assertEqual(len(solutions), 2)
        self.assertLess(solutions[0]['error_px'], .02)
        self.assertGreater(float(solutions[0]['center'][2]), 0.)
        self.assertAlmostEqual(np.linalg.det(solutions[0]['blender_rotation']), 1., places=6)

    def test_bad_inputs(self):
        with self.assertRaises(rc.RimSolveError):
            rc.solve_circle_camera_candidates((0,0,100,120,0), 500, 900,900,0,0)

    def test_candidate_detector(self):
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (540, 480), '#111318')
        d = ImageDraw.Draw(img)
        d.ellipse((80, 75, 460, 405), outline='#e9e9e9', width=5)
        d.ellipse((129, 117, 411, 363), outline='#9f9f9f', width=4)
        found = rc.detect_ellipse_candidates(np.asarray(img), roi=(45, 40, 495, 440))
        self.assertGreaterEqual(len(found), 1)
        self.assertLess(abs(found[0][0][0]-270), 14)
        self.assertLess(abs(found[0][0][1]-240), 14)
        self.assertLess(abs(found[0][0][2]-190), 18)
        self.assertLess(abs(found[0][0][3]-165), 18)

    def test_blank_image_no_candidates(self):
        with self.assertRaises(rc.RimSolveError):
            rc.detect_ellipse_candidates(np.zeros((200,200),dtype=np.float32))


if __name__=='__main__':
    unittest.main()
