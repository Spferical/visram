"""For testing"""
import visram.chart
import unittest


class TestVisram(unittest.TestCase):

    def _test_chart_type(self, chart_type):
        fig, axes, chart_type = visram.chart.create_chart(
            chart_type, 'spectral')

        # output chart type should be the same as the input
        self.assertEqual(chart_type, chart_type)

        # test size of bounds is not near-zero
        xlim = axes.get_xlim()
        ylim = axes.get_ylim()
        self.assertNotAlmostEqual(xlim[0] - xlim[1], 0)
        self.assertNotAlmostEqual(ylim[0] - ylim[1], 0)

    def test_ram_chart(self):
        self._test_chart_type('ram')

    def test_cpu_chart(self):
        self._test_chart_type('cpu')


if __name__ == '__main__':
    unittest.main()
