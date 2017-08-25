# Unit tests for LUCYParams.py
import unittest
from PythonLUCY.LUCYParams import LUCYParams
import tempfile
_GOOD_DATA = """&params
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
        """

_GOOD_LANDCOVERS = """
            &landCoverWeights
            grass      		= 0, 0, 0.025
            baresoil        = 0, 0, 0
            paved       	= 0, 1, 0.10
            buildings   	= 1, 0, 0.85
            water      		= 0, 0, 0
            decidioustrees  = 0, 0, 0.025
            evergreentrees  = 0, 0, 0
        /
        """
_BAD_LANDCOVERS =  """"
        &landCoverWeights

            grass      		= 2, 0
            baresoil        = 2, 0
            paved       	= 2, 1
            buildings   	= 2, 0
            water      		= 2, 0, 0
            decidioustrees  = 2, 0
            evergreentrees  = 2, 0
        /
        """

_GOOD_TRESPONSE =  """
        &CustomTemperatureResponse
            Th = 20
            Tc = 10
            Ah = 0.1
            Ac = 0.2
            c = 0.5
            Tmax = 50
            Tmin = -10
        /
        """

_INCOMPLETE_TRESPONSE =  """
        &CustomTemperatureResponse
            Th = 20
            Tc = 10
            Ac = 0.2
            c = 0.5
            Tmax = 50
            Tmin = -10
        /
        """
class ParamsTest(unittest.TestCase):
    def createBadFile(self):
        ''' Write a temporary file that's not NML compliant'''
        fn  = tempfile.mktemp()
        with open(fn, 'w') as outFile:
            outFile.write('test')

        return fn

    def createGoodFile(self):
        ''' Write a temporary file that's got basic parameters but not optional ones'''
        fn  = tempfile.mktemp()
        data = _GOOD_DATA + _GOOD_LANDCOVERS

        with open(fn, 'w') as outFile:
            outFile.write(data)
        return fn

    def createBadWeights(self):
        ''' Write a temporary file that's technically fine but contains the wrong number of columns in weightings file '''
        fn  = tempfile.mktemp()
        data = _GOOD_DATA + _BAD_LANDCOVERS

        with open(fn, 'w') as outFile:
            outFile.write(data)
        return fn

    def createIncompleteTresp(self):
        ''' Write a temporary file that specifies an incomplete temperature response parameter set'''
        fn  = tempfile.mktemp()
        data = _GOOD_DATA + _GOOD_LANDCOVERS + _INCOMPLETE_TRESPONSE

        with open(fn, 'w') as outFile:
            outFile.write(data)
        return fn

    def createCompleteTresp(self):
        ''' Write a temporary file that specifies a complete temperature response parameter set'''
        fn  = tempfile.mktemp()
        data = _GOOD_DATA + _GOOD_LANDCOVERS + _GOOD_TRESPONSE

        with open(fn, 'w') as outFile:
            outFile.write(data)
        return fn


    def testBadFileRejected(self):
        filename = self.createBadFile()
        self.assertRaises(Exception, LUCYParams, filename)

    def testGoodBasicFile(self):
        filename = self.createGoodFile()
        self.assertTrue(isinstance(LUCYParams(filename),  LUCYParams))

    def testBadWeightsRejected(self):
        filename = self.createBadWeights()
        self.assertRaises(Exception, LUCYParams, filename)

    def testNoTResponseMeansNoEntry(self):
        ''' Once temperature response is specified, check the full complement of variables is checked'''
        filename = self.createGoodFile()
        a = LUCYParams(filename)
        self.assertTrue(a.TResponse is None)

    def testTResponsePresentNeedsAllVariables(self):
        ''' Once temperature response is specified, check the full complement of variables is checked'''
        filename = self.createIncompleteTresp()
        self.assertRaises(ValueError, LUCYParams, filename)

    def testTResponseAllVariablesPresent(self):
        ''' Once temperature response is specified, check the full complement of variables is checked'''
        filename = self.createCompleteTresp()
        a =  LUCYParams(filename)
        self.assertTrue(a.TResponse is not None)

if __name__ == "__main__":
    unittest.main()


