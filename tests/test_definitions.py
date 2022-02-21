"""
Test for errors in datafield and payload definitions

Created on 19 Feb 2022

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import unittest
from pyrtcm import RTCM_PAYLOADS_GET, RTCM_DATA_FIELDS


class DefinitionTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def testpayloaddfs(
        self,
    ):  # test all payload datafields are defined in RTCM_DATA_FIELDS
        for _, pdict in RTCM_PAYLOADS_GET.items():
            for df, _ in pdict.items():
                if df[0:5] != "group":
                    self.assertIn(df, RTCM_DATA_FIELDS)

    def testdfres(self):  # test all resolution values are int or float
        for _, (_, res, _) in RTCM_DATA_FIELDS.items():
            self.assertIsInstance(res, (int, float))