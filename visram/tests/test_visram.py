"""For testing"""
import visram.chart
import unittest
import psutil


class TestVisram(unittest.TestCase):

    def _test_create_chart(self, chart_type):
        fig, axes, result_chart_type = visram.chart.create_chart(
            chart_type, 'spectral')

        # output chart type should be the same as the input
        self.assertEqual(chart_type, result_chart_type)

        # test size of bounds is not near-zero
        xlim = axes.get_xlim()
        ylim = axes.get_ylim()
        self.assertNotAlmostEqual(xlim[0] - xlim[1], 0)
        self.assertNotAlmostEqual(ylim[0] - ylim[1], 0)

    def test_ram_chart(self):
        self._test_create_chart('ram')

    def test_cpu_chart(self):
        self._test_create_chart('cpu')

    def test_get_root_processes(self):
        # no processes -> no root processes
        self.assertListEqual(visram.chart.get_root_processes([]), [])
        this_process = psutil.Process()

        # given all processes on this system, it should return at least one
        self.assertTrue(visram.chart.get_root_processes(psutil.process_iter()))

    def test_update_bounds(self):
        desired = {
            ((0, 0, 0, 0), (1, 1, 1, 1)): (1, 0, 0, 1),
            ((0, 0, 1, 1), (5, -5, -5, 5)): (5, -5, -5, 5),
        }

        for bounds_set in desired:
            bounds1, bounds2 = bounds_set
            self.assertEqual(desired[bounds_set],
                             visram.chart.update_bounds(bounds1, bounds2))

    def test_process_wedge(self):
        p_dict = {
            'pid': 123,
            'name': 'test_process',
        }

        depth = 2
        center = (0.5, 0.5)
        radius = 1
        start_angle = 90
        end_angle = 180

        wedge = visram.chart.ProcessWedge(
            p_dict, depth, center, radius, start_angle, end_angle, width=1,
            facecolor=(.25, .25, .25, .25), linewidth=.25)

        self.assertEqual(wedge.arc, 90)
        self.assertEqual(wedge.get_bounds(),
                         (2.5, -1.5, 0.5, 0.5))

        self.assertTrue(wedge.contains_point(.5 - 1.4, .5 - 1.4))
        self.assertTrue(wedge.contains_point(.5 - 0.01, .5 + 1.5))

        self.assertTrue(wedge.contains_polar(1.1, 91))
        self.assertTrue(wedge.contains_polar(1.9, 179))


if __name__ == '__main__':
    unittest.main()
