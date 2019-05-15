from collections import OrderedDict
class LookupLogger:
    # Logger object to keep track of data requests and what was provided when the available data didn't match the requested date

    def __init__(self):
        self.log = {}

    def flush(self):
        self.log = {}

    def addEvent(self, eventType, requestedDate, actualDate, paramName, description):
        '''
        Record an event in the log
        :param eventType: string: Type of event being recorded
        :param requestedDate: datetime: the date that was requested by an external program
        :param actualDate: datetime: the datetime of the data provided by the data store to best match requestedDate
        :param paramName: string: the parameter being provided
        :param description: string: any extra information
        :return: None
        '''

        if eventType not in list(self.log.keys()):
            self.log[eventType] = OrderedDict()

        if requestedDate not in list(self.log[eventType].keys()):
            self.log[eventType][requestedDate] = []

        newEntry = [actualDate, paramName, description]
        self.log[eventType][requestedDate].append(newEntry)

    def getEventsForParameter(self, paramName):
        '''
        Return list of request dates and provided dates for the specified parameeter name
        :param paramName: string: parameter name (as it appears in the log)
        :return: dict of request {requestedDate:[matchedValues]}
        '''
    def getEvents(self):
        '''
        Return list of request dates and provided dates for everything
        :return: dict of events: {eventType: {date: [info]}}
        '''

        return self.log

    def writeFile(self, filename):
        '''
        Write out log file (everything)
        :param: filename (string): Absolute filename to which to write
        :return: None
        '''
        try:
            f = open(filename, 'w')
        except Exception as e:
            raise Exception('Could not write to log file:' + str(filename) + ':' + str(e))
        f.write('Requested Date (if applic):: Date returned (if applic) :: Param name :: Description\r\n')

        for eventType in list(self.log.keys()):
            f.write('======' + str(eventType) + '=======\r\n')
            for requestTime in list(self.log[eventType].keys()):
                printReqTime = 'None' if requestTime is None else requestTime.strftime('%Y-%m-%d %H:%M:%S %Z')
                for logLine in self.log[eventType][requestTime]:
                    printActualTime = 'None' if logLine[0] is None else logLine[0].strftime('%Y-%m-%d %H:%M:%S %Z')
                    logLin = printReqTime + ' :: ' + printActualTime + ' :: ' + str(logLine[1]) + ' :: ' + str(logLine[2]) + '\r\n'
                    f.write(logLin)
        f.close()
