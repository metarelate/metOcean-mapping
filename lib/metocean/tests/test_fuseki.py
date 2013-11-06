# (C) British Crown Copyright 2013, Met Office
#
# This file is part of metOcean-mapping.
#
# metOcean-mapping is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# metOcean-mapping is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with metOcean-mapping. If not, see <http://www.gnu.org/licenses/>.
"""
Test the metOcean Apache Fuseki server.

"""

import unittest

import metocean
import metocean.tests as tests
from metocean.fuseki import FusekiServer

FORMAT_CF = '<http://www.metarelate.net/metOcean/format/cf>'
FORMAT_UM = '<http://www.metarelate.net/metOcean/format/um>'


class TestFuseki(tests.MetOceanTestCase):
    @classmethod
    def setUpClass(cls):
        cls.fuseki = FusekiServer(test=True)
        cls.fuseki.start()

    @classmethod
    def tearDownClass(cls):
        cls.fuseki.stop()

    def test_retrieve_um_cf(self):
        mappings = self.fuseki.retrieve_mappings(FORMAT_UM, FORMAT_CF)
        self.assertEqual(len(mappings), 1)

    def test_dot_um_cf(self):
        mappings = self.fuseki.retrieve_mappings(FORMAT_UM, FORMAT_CF)
        for mapping in sorted(mappings, key=lambda mapping: mapping.uri.data):
            self.check_dot(mapping)


if __name__ == '__main__':
    unittest.main()
