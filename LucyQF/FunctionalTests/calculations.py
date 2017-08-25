# Unit tests for key calculatons in LQF
import unittest
from PythonLUCY.LUCYParams import LUCYParams
from PythonLUCY.LUCYfunctions import *
import pandas as pd
import numpy as np
import tempfile
_GOOD_PARAMS = """&params
            timezone = \"Europe/London\"
            use_uk_holidays = 1 ! Set to 1 to use UK public holidays, set to 0 to use none
            use_custom_holidays = 0	! Whether or not to use a list of public holidays specified using custom_holidays in the next line
            custom_holidays = ''
            avgspeed = 48000. !m/hour
            emissionfactors = 25.92, 13.16, 108.42 !W/m
            fueltype = "Petrol"
            balance_point_temperature = 12.
            balance_point_multfactor = 0.7
            QV_multfactor = 0.8
            sleep_metab = 75  ! Watts emitted by a sleeping human
            work_metab = 175  ! Watts emitted by a working human
        /
        &landCoverWeights
            grass      		= 0, 0, 0.025
            baresoil        = 0, 0, 0
            paved       	= 0, 1, 0.10
            buildings   	= 1, 0, 0.85
            water      		= 0, 0, 0
            decidioustrees  = 0, 0, 0.025
            evergreentrees  = 0, 0, 0
        /
        &CustomTemperatureResponse
            Th = 10
            Tc = 20
            Ah = 0.1
            Ac = 0.2
            c = 0.5
            Tmax = 50
            Tmin = -10
        /
        """

class CustomTempResponse(unittest.TestCase):
    ''' Tests for custom temperature response calculation'''
    def setUp(self):

        fn  = tempfile.mktemp()
        with open(fn, 'w') as outFile:
            outFile.write(_GOOD_PARAMS)
        self.params = LUCYParams(fn)

    def testExtremeLowT(self):
        ''' Extreme low should be a particular value'''
        self.assertTrue(round(customTResponse(-9.9, self.params), 3)==2.49)
        self.assertTrue(customTResponse(-10.0, self.params)==2.50)
        self.assertTrue(customTResponse(-10.1, self.params)==2.50)
        self.assertTrue(customTResponse(-100, self.params)==2.50)

    def testExtremeHighT(self):
        ''' Extreme low should be a particular value'''
        self.assertTrue(customTResponse(100, self.params)==6.50)
        self.assertTrue(customTResponse(50.1, self.params)==6.50)
        self.assertTrue(customTResponse(50.0, self.params)==6.50)
        self.assertTrue(customTResponse(49.9, self.params)==6.48)

    def testMediumRangeT(self):
        ''' Mid-range temperatures should be equal to 'c' parameter'''
        self.assertTrue(customTResponse(15, self.params)==0.5)

    def testAroundHeatingPoint(self):
        ''' Test temperatures around where heating is switched on'''
        self.assertTrue(customTResponse(10.1, self.params)==0.50)
        self.assertTrue(customTResponse(10.0, self.params)==0.50)
        self.assertTrue(customTResponse(9.9, self.params)==0.51)

    def testAroundCoolingPoint(self):
        ''' Test temperatures around where cooling is switched on'''
        self.assertTrue(customTResponse(19.9, self.params)==0.50)
        self.assertTrue(customTResponse(20.0, self.params)==0.50)
        self.assertTrue(round(customTResponse(20.1, self.params),2)==0.52)

class StandardTempResponse(unittest.TestCase):
    ''' Tests for built-in temperature response calculation'''
    def setUp(self):
        self.attribs = pd.concat([pd.Series([1,1, np.nan]), pd.Series([1,0, np.nan]), pd.Series([0.5,0.5, np.nan]), pd.Series([0.1,0.1, np.nan]), pd.Series([0.7,0.7, np.nan])], axis=1)
        self.attribs.columns =['ecostatus', 'summer_cooling', 'increasePerHDD', 'increasePerCDD', 'offset']
        self.attribs.index =['cooling', 'nocooling', 'invalid']
        self.BP = 12.0 # Balance point temperature

    def testBelowBalancePoint(self):
        T=11.9
        expectedValue = 30 * abs(T-self.BP)*self.attribs['increasePerHDD']['cooling'] +  self.attribs['offset']['cooling']
        a = getTMF(T, self.BP, self.attribs)
        self.assertTrue(a['cooling'] == expectedValue)

    def testAtBalancePoint(self):
        a = getTMF(12.0, self.BP, self.attribs)
        self.assertTrue(a['cooling']==self.attribs['offset']['cooling'])

    def testAboveBalancePointCooling(self):
        T=12.1
        a = getTMF(T, self.BP, self.attribs)
        expectedValue = 30 * abs(T-self.BP)*self.attribs['increasePerCDD']['cooling'] + self.attribs['offset']['cooling']
        self.assertEqual(a['cooling'], expectedValue)


    def testAboveBalancePointNoCooling(self):
        a = getTMF(12.1, self.BP, self.attribs)
        expectedValue = self.attribs['offset']['cooling']
        self.assertEqual(a['nocooling'], expectedValue)

    def testExtremelyHighT(self):
        # Should be extremely high energy use. There is no cap on this
        T = 1000
        a = getTMF(T, self.BP, self.attribs)
        expectedValue = 30 * abs(T-self.BP)*self.attribs['increasePerCDD']['cooling'] + self.attribs['offset']['cooling']
        self.assertEqual(a['cooling'], expectedValue)

    def testExtremelyLowT(self):
        # Energy use should follow different profile when temperature difference is extreme
        T=-1000
        HDD = 30 * abs(T-self.BP)
        expectedVal = HDD * (3E-10*HDD**2 - 1E-6*HDD+2.9E-3) + self.attribs['offset']['cooling']
        a = getTMF(T, self.BP, self.attribs)
        self.assertEqual(a['cooling'], expectedVal)

if __name__ == "__main__":
    unittest.main()



