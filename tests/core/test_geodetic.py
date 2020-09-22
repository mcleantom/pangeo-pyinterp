# Copyright (c) 2020 CNES
#
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.
import pickle
import unittest
import math
import numpy as np
from pyinterp import core


class TextSystem(unittest.TestCase):
    """Test of the C+++/Python interface of the pyinterp::geodetic::System
    class"""
    def test_system_wgs84(self):
        """Checking expected WGS-84 properties"""
        wgs84 = core.geodetic.System()
        # https://fr.wikipedia.org/wiki/WGS_84
        # https://en.wikipedia.org/wiki/Geodetic_datum
        # http://earth-info.nga.mil/GandG/publications/tr8350.2/wgs84fin.pdf
        self.assertAlmostEqual(wgs84.semi_major_axis, 6378137)
        self.assertAlmostEqual(wgs84.flattening, 1 / 298.257223563)
        self.assertAlmostEqual(wgs84.semi_minor_axis(),
                               6356752.314245179497563967)
        self.assertAlmostEqual(math.sqrt(wgs84.first_eccentricity_squared()),
                               0.081819190842622,
                               delta=1e-15)
        self.assertAlmostEqual(math.sqrt(wgs84.second_eccentricity_squared()),
                               8.2094437949696 * 1e-2,
                               delta=1e-15)
        self.assertAlmostEqual(wgs84.equatorial_circumference() * 1e-3,
                               40075.017,
                               delta=1e-3)
        self.assertAlmostEqual(wgs84.equatorial_circumference(False) * 1e-3,
                               39940.652,
                               delta=1e-3)
        self.assertAlmostEqual(wgs84.polar_radius_of_curvature(),
                               6399593.6258,
                               delta=1e-4)
        self.assertAlmostEqual(wgs84.equatorial_radius_of_curvature(),
                               6335439.3272,
                               delta=1e-4)
        self.assertAlmostEqual(wgs84.axis_ratio(), 0.996647189335, delta=1e-12)
        self.assertAlmostEqual(wgs84.linear_eccentricity(),
                               5.2185400842339 * 1E5,
                               delta=1e-6)
        self.assertAlmostEqual(wgs84.mean_radius(), 6371008.7714, delta=1e-4)
        self.assertAlmostEqual(wgs84.authalic_radius(),
                               6371007.1809,
                               delta=1e-4)
        self.assertAlmostEqual(wgs84.volumetric_radius(),
                               6371000.7900,
                               delta=1e-4)

    def test_system_operators(self):
        """Test operators"""
        wgs84 = core.geodetic.System()
        # https://en.wikipedia.org/wiki/Geodetic_Reference_System_1980
        grs80 = core.geodetic.System(6378137, 1 / 298.257222101)
        self.assertAlmostEqual(grs80.semi_major_axis, 6378137)
        self.assertAlmostEqual(grs80.flattening, 1 / 298.257222101)
        self.assertEqual(wgs84, wgs84)
        self.assertNotEqual(wgs84, grs80)

    def test_system_pickle(self):
        """Serialization test"""
        wgs84 = core.geodetic.System()
        self.assertEqual(wgs84, pickle.loads(pickle.dumps(wgs84)))


class TestCoordinates(unittest.TestCase):
    """Test of the C+++/Python interface of the pyinterp::geodetic::Coordinates
    class"""
    def test_coordinates_ecef_lla(self):
        """ECEF/LLA Conversion Test"""
        lon, lat, alt = core.geodetic.Coordinates(None).ecef_to_lla(
            [1176498.769459714], [5555043.905503586], [2895446.8901510699])
        self.assertAlmostEqual(78.042068, lon[0], delta=1e-8)
        self.assertAlmostEqual(27.173891, lat[0], delta=1e-8)
        self.assertAlmostEqual(168.0, alt[0], delta=1e-8)

    def test_coordinates_lla_to_ecef(self):
        """LLA/ECEF Conversion Test"""
        x, y, z = core.geodetic.Coordinates(None).lla_to_ecef([78.042068],
                                                              [27.173891],
                                                              [168.0])
        self.assertAlmostEqual(1176498.769459714, x[0], delta=1e-8)
        self.assertAlmostEqual(5555043.905503586, y[0], delta=1e-8)
        self.assertAlmostEqual(2895446.8901510699, z[0], delta=1e-8)

    def test_coordinates_round_trip(self):
        """Check algorithm precision"""
        lon1 = np.random.uniform(-180.0, 180.0, 1000000)
        lat1 = np.random.uniform(-90.0, 90.0, 1000000)
        alt1 = np.random.uniform(-10000, 100000, 1000000)

        a = core.geodetic.Coordinates(None)
        b = core.geodetic.Coordinates(None)

        lon2, lat2, alt2 = a.transform(b, lon1, lat1, alt1, num_threads=0)

        self.assertAlmostEqual((lon1 - lon2).mean(), 0, delta=1e-12)
        self.assertAlmostEqual((lat1 - lat2).mean(), 0, delta=1e-12)
        self.assertAlmostEqual((alt1 - alt2).mean(), 0, delta=1e-10)

    def test_pickle(self):
        """Serialization test"""
        a = core.geodetic.Coordinates(None)
        b = pickle.loads(pickle.dumps(a))
        self.assertTrue(np.all(a.__getstate__() == b.__getstate__()))


class TestPoint(unittest.TestCase):
    """Test of the C+++/Python interface of the pyinterp::geodetic::Point
    class"""
    def test_point_init(self):
        """Test construction and accessors of the object"""
        pt = core.geodetic.Point(12, 24)
        self.assertEqual(pt.lon, 12)
        self.assertEqual(pt.lat, 24)
        self.assertEqual(str(pt), "(12, 24)")
        pt.lon = 55
        self.assertEqual(pt.lon, 55)
        pt.lat = 33
        self.assertEqual(pt.lat, 33)
        point = core.geodetic.Point.read_wkt("POINT(-2 2)")
        assert point.wkt() == "POINT(-2 2)"

    def test_point_pickle(self):
        """Serialization tests"""
        a = core.geodetic.Point(1, 2)
        b = pickle.loads(pickle.dumps(a))
        self.assertEqual(a.lon, b.lon)
        self.assertEqual(a.lat, b.lat)
        self.assertNotEqual(id(a), id(b))


class TestBox(unittest.TestCase):
    """Test of the C+++/Python interface of the pyinterp::geodetic::Box
    class"""
    def test_box_init(self):
        """Test construction and accessors of the object"""
        min_corner = core.geodetic.Point(0, 1)
        max_corner = core.geodetic.Point(2, 3)

        box = core.geodetic.Box(min_corner, max_corner)
        self.assertEqual(str(box), "((0, 1), (2, 3))")
        self.assertEqual(box.min_corner.lon, 0)
        self.assertEqual(box.min_corner.lat, 1)
        self.assertEqual(box.max_corner.lon, 2)
        self.assertEqual(box.max_corner.lat, 3)

        self.assertTrue(box.covered_by(min_corner))
        self.assertTrue(box.covered_by(max_corner))
        self.assertTrue(box.covered_by(core.geodetic.Point(1, 2)))
        self.assertFalse(box.covered_by(core.geodetic.Point(0, 0)))

        flags = box.covered_by([1, 0], [2, 0])
        self.assertTrue(np.all(flags == [1, 0]))

        box.min_corner, box.max_corner = max_corner, min_corner
        self.assertEqual(box.min_corner.lon, 2)
        self.assertEqual(box.min_corner.lat, 3)
        self.assertEqual(box.max_corner.lon, 0)
        self.assertEqual(box.max_corner.lat, 1)

        assert box.wkt() == "POLYGON((2 3,2 1,0 1,0 3,2 3))"
        box = core.geodetic.Box.read_wkt(
            "POLYGON((2 3,2 1,0 1,0 3,2 3))")
        assert repr(box) == "((2, 3), (0, 1))"


    def test_pickle(self):
        """Serialization tests"""
        min_corner = core.geodetic.Point(0, 1)
        max_corner = core.geodetic.Point(2, 3)
        a = core.geodetic.Box(min_corner, max_corner)
        b = pickle.loads(pickle.dumps(a))
        self.assertEqual(a.min_corner.lon, b.min_corner.lon)
        self.assertEqual(a.min_corner.lat, b.min_corner.lat)
        self.assertEqual(a.max_corner.lon, b.max_corner.lon)
        self.assertEqual(a.max_corner.lat, b.max_corner.lat)


if __name__ == "__main__":
    unittest.main()
