#!/usr/bin/env python
#
# Copyright (C) 2017 VMware, Inc.
# All Rights Reserved
#

from __future__ import division
import requests
import json
import logging
import os
import sys
import getpass
import optparse
import re
import time

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, \
    Image, LongTable, TableStyle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin
from reportlab.lib.colors import PCMYKColor
from reportlab.platypus.flowables import KeepTogether

DEFAULT_DOMAIN = 'vsphere'
DEFAULT_PROJECT = 'esx'

log = logging.getLogger('Rpt')
loglevel = os.environ.get('LOGLEVEL', 'DEBUG')
log.setLevel(loglevel)

pieData = {}
bug_list = []
No_bug_list = []
status_dict = {'Passed': 0, 'Failed': 0, 'No Run': 0}
nbsp_str = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'


def process_args(args, usage):
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--domain", dest="domain", action="store",
                      default=DEFAULT_DOMAIN, type="string",
                      help="hpqc domain name")
    parser.add_option("-j", "--project", dest="project", action="store",
                      default=DEFAULT_PROJECT, type="string",
                      help="hpqc project name")
    parser.add_option("-r", "--resultdir", dest="resultdir", action="store",
                      type="string", help=" result directory")
    parser.add_option("-l", "--logdir", dest="logdir", action="store",
                      type="string", help="dir to store log file")
    parser.add_option("-c", "--cycleid", dest="cycleid", action="store",
                      type="string", help="cycleid")
    parser.add_option("-n", "--cyclename", dest="cyclename", action="store",
                      type="string", help="cyclename")
    parser.add_option("-u", "--user", dest="user", action="store",
                      type="string", help="username (Domain user account)")
    parser.add_option("-p", "--password", dest="password", action="store",
                      type="string", help="password (Domain user password)")

    (options, args) = parser.parse_args(args)
    return (options, args)


def setup_logging(logdir):
    '''
    Setup log
    @type logdir: str
    @param logdir: folder under which to generate log
    @return: None
    '''
    global log
    log_format = '%(asctime)s %(lineno)d %(levelname)-6s %(message)s'
    date_format = '%m/%d/%Y %I:%M:%S %p'
    logfile = logdir + os.sep + __name__ + '.log'
    log = logging.getLogger(__name__)
    logging.basicConfig(format=log_format, datefmt=date_format,
                        level=logging.DEBUG)
    log.setLevel(loglevel)

    fh = logging.FileHandler(logfile)
    fh.setLevel(loglevel)
    log.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    log.addHandler(ch)


class ALMUrl:
    '''
    Class of HPQC access to certain query
    '''
    def __init__(self, base_url, domain, project):
        self.__base = base_url
        self.__work = self.__base + '/rest/domains/' + domain \
                                  + '/projects/' + project

    def get_isauth(self):
        return self.__base + '/rest/is-authenticated'

    def get_auth(self):
        return self.__base + '/authentication-point/authenticate'

    def get_session(self):
        return self.__base + '/rest/site-session'

    def get_logout(self):
        return self.__base + '/authentication-point/logout'

    def __getattr__(self, *args):
        result = self.__work
        for arg in args:
            result += '/' + arg
        return result


class ALMSession:
    '''
    Class of a session to access HPQC
    '''
    def __init__(self, user, password):
        try:
            self.__headers = {"Accept": "application/json",
                              "Content-Type": "application/json",
                              "KeepAlive": "true",
                              "Cookie": None}
            self.__user_pass = (user, password)
        except:
            log.error("Exception while creating ALMSession",
                      self.__headers, self.__h)

    def parse_json(self, obj):
        obj = json.loads(obj)
        return obj

    def is_authed(self, ALMUrl):
        '''
        @type ALMUrl: str
        @param ALMUrl: instance of ALMUrl object
        @rtype: int
        @return: 0 or 1 or http return code
        '''

        r = requests.get(ALMUrl.get_isauth(), auth=self.__user_pass)
        if r.status_code == 200:
            log.info("Already authenticated: %s" % ALMUrl.get_isauth())
            return 0
        elif r.status_code == 401:
            log.info("Not authenticated: %s" % ALMUrl.get_isauth())
            return 1
        else:
            log.error("Open ALM failed: %s,%s" % (r.status_code, r.reason))
            log.error('AUTH_URL:%s' % ALMUrl.ge_isauth())
            return int(r.status_code)

    def Open(self, ALMUrl):
        '''
        @type ALMUrl: str
        @param ALMUrl: instance of ALMUrl object
        @rtype: int
        @return: 0 or http return code as error code
        '''

        r = requests.get(ALMUrl.get_auth(), auth=self.__user_pass)
        if r.status_code is 200:
            mach = re.match(r'LWSSO_COOKIE_KEY=.*?;', r.headers['set-cookie'])
            self.__headers["Cookie"] = mach.group(0)
            log.info("Open ALM success, AUTH URL: %s" % ALMUrl.get_auth())
            log.info('HEADERS: %s' % self.__headers)
            return 0
        else:
            log.error("Open ALM failed: %s,%s" % (r.status_code, r.reason))
            log.error('AUTH URL: %s' % ALMUrl.ge_auth())
            log.error('HEADERS: %s' % self.__headers)
            return int(r.status_code)

    def SessionManage(self, ALMUrl):
        '''
        @type ALMUrl: str
        @param ALMUrl: instance of ALMUrl object
        @rtype: int
        @return: 0 or http return code as error code
        '''

        if self.__headers["Cookie"] is None:
            log.error("[ALMSession] Failed, No cookie! URL:%s HEADERS:%s"
                      % (ALMUrl.get_session(), self.__headers))
            return 406, None

        r = requests.post(ALMUrl.get_session(), headers=self.__headers,
                          auth=self.__user_pass)
        if r.status_code == 201:
            pattern = re.compile('QCSession=.*?;')
            result = pattern.findall(r.headers['set-cookie'])
            self.__headers["Cookie"] += result[0]
            log.info("[ALMSession] Success! URL:%s HEADERS:%s"
                     % (ALMUrl.get_session(), self.__headers))
            return 0
        else:
            log.error("[ALMSession] Failed, URL:%s HEADERS:%s"
                      % (ALMUrl.get_session(), self.__headers))
            return int(r.status_code), None

    def Close(self, ALMUrl):
        '''
        Close ALM Session
        @type ALMUrl: str
        @param ALMUrl: instance of ALMUrl object
        @rtype: int
        @return: 0 or http return code as error code
        '''

        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.get_logout(), headers=self.__headers,
                             auth=self.__user_pass)
            if r.status_code is 200:
                log.info(
                    "Logout ALM session success: %s" % ALMUrl.get_logout())
                return 0
            else:
                log.error("Failed to close ALM session:%s, %s"
                          % (r.status_code, r.reason))
                log.error('LOGOUT URL:%s' % ALMUrl.get_logout())
                log.error('HEADERS:%s' % self.__headers)
                return int(r.status_code)
        else:
            log.error("Close ALM session.  httplib2.Http was not initialized")
            return 1

    def Get(self, ALMUrl, *args):
        '''
        Get ALM session content
        @type ALMUrl: str
        @param ALMUrl: instance of ALMUrl object
        @rtype: int
        @return: 0 or http return code as error code
        '''

        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.__getattr__(*args), headers=self.__headers)
            if r.status_code == 200:
                log.info("[ALMSession] Get success, URL:%s"
                         % ALMUrl.__getattr__(*args))
                data = self.parse_json(r.content)
                return 0, data
            else:
                log.error("[ALMSession] Error getting ALM function: %s, %s"
                          % (r.status_code, r.reason))
                log.error("PATH:%s" % ALMUrl.__getattr__(*args))
                log.error("HEADERS:%s" % self.__headers)
                return int(r.status_code), None
        else:
            log.error("[ALMSession] Error: httplib2.Http not initialized")
            return 1, None


class Reportlab:
    '''
    Class of PDF Report
    '''

    def makeForm(self, bug_list, No_bug_list, cmdOpts, report_name):
        '''
        Generate pdf file using bug information
        @type bug_list: list
        @param bug_list: list of list information
        @type No_bug_list: list
        @param No_bug_list: list of cases that failed with no related bug
        @type cmdOpts: command line options
        @param cmdOpts: user specified command line options
        @type report_name: str
        @param report_name: PDF file name
        @return: None
        '''

        story = []
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        resultdir = cmdOpts.resultdir

        # report title
        data_format = '<para autoLeading="off" fontSize=15 align=center>' \
            + '<b>Report for Cycle %s</b><br/><br/><br/></para>'
        rpt_title = data_format % (report_name)
        story.append(Paragraph(rpt_title, normalStyle))

        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
            + '<br/><b>1. Test Set ID: %s </b><br/></para>'
        text = data_format % cmdOpts.cycleid
        story.append(Paragraph(text, normalStyle))
        # test pie chart img
        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
            + '<br/><b>2. Test Result</b><br/></para>'
        text = data_format
        story.append(Paragraph(text, normalStyle))
        img = Image(os.path.join(resultdir, 'PieChart000.png'))
        img.drawHeight = 150
        img.drawWidth = 300
        story.append(img)

        # bug list table
        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
            + '<b>3. Bug List</b><br/></para>'
        text = data_format
        story.append(Paragraph(text, normalStyle))

        mylist = ['TestSet', 'Bug_ID', 'Summary', 'Status', 'Priority',
                  'Reporter', 'Assignee', 'Case_Num', 'CaseName']
        component_data = [mylist]
        th_fmt = '<para autoLeading="off" fontSize=5.5 align=left>%s</para>'
        for item in bug_list:
            x = [Paragraph(th_fmt % (item[entry]), normalStyle)
                 for entry in mylist]
            component_data.append(x)

        component_table = LongTable(
            component_data,
            colWidths=[35, 35, 160, 35, 30, 48, 48, 30, 150])
        table_style = TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (0, 0), (0, -1), 0.1, colors.grey),
            ('TEXTCOLOR', (0, 1), (-2, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)])
        component_table.setStyle(table_style)
        story.append(component_table)

        # no bug list table
        text = '<para autoLeading="off" fontSize=9 align=center><br/><b>' \
            + '4.Failed cases with no Bug Linked</b><br/></para>'
        my2list = ['TestSet', 'Case_Num', 'Cases_Name']
        component_data = [my2list]
        next_line = '<br>'
        for item in No_bug_list:
            old_value = item['Cases_Name']
            item['Cases_Name'] = next_line.join(old_value)

            x = [Paragraph(th_fmt % item[entry], normalStyle)
                 for entry in my2list]
            component_data.append(x)

        component_table = LongTable(component_data, colWidths=[35, 35, 500])
        component_table.setStyle(table_style)
        para_no_bug = Paragraph(text, normalStyle)
        story.append(KeepTogether([para_no_bug, component_table]))

        pdf_name = os.path.join(resultdir, 'Rpt-' + report_name + '.pdf')
        doc = SimpleDocTemplate(pdf_name)
        doc.build(story)
        log.info("SUCCESS! Report (%s) is generated." % pdf_name)


class PieChart(_DrawingEditorMixin, Drawing):
    '''
    Class of Pie chart with a basic legend.
    '''

    def __init__(self, width=400, height=200, *args, **kw):
        Drawing.__init__(self, width, height, *args, **kw)
        global pieData
        mycolor = [PCMYKColor(100, 0, 90, 50, alpha=100),
                   PCMYKColor(0, 100, 100, 40, alpha=100),
                   PCMYKColor(66, 13, 0, 22, alpha=100)]

        num_pass = pieData['Passed']
        num_fail = pieData['Failed']
        num_norun = pieData['No Run']

        total = num_pass + num_fail + num_norun
        passed, failed, norun = '0', '0', '0'
        if total != 0:
            passed = str(round(float(num_pass / total) * 100, 2)) + '%'
            failed = str(round(float(num_fail / total) * 100, 2)) + '%'
            norun = str(round(float(num_norun / total) * 100, 2)) + '%'

            # pie
            self._add(self, Pie(), name='pie', validate=None, desc=None)
            self.pie.strokeWidth = 1
            self.pie.slices.strokeColor = PCMYKColor(0, 0, 0, 0)
            self.pie.slices.strokeWidth = 1
            self.pie.data = [num_pass, num_fail, num_norun]
            for i in range(len(self.pie.data)):
                self.pie.slices[i].fillColor = mycolor[i]
            self.pie.strokeColor = PCMYKColor(0, 0, 0, 0, alpha=100)
            self.pie.width = 150
            self.pie.height = 150
            self.pie.y = 25
            self.pie.x = 25

        # legend
        self._add(self, Legend(), name='legend', validate=None, desc=None)
        self.legend.columnMaximum = 99
        self.legend.alignment = 'right'
        self.legend.dx = 6
        self.legend.dy = 6
        self.legend.dxTextSpace = 5
        self.legend.deltay = 10
        self.legend.strokeWidth = 0
        self.legend.subCols[0].minWidth = 75
        self.legend.subCols[0].align = 'left'
        self.legend.subCols[1].minWidth = 25
        self.legend.subCols[1].align = 'right'

        self.height = 200
        self.legend.boxAnchor = 'c'
        self.legend.y = 100

        self.legend.colorNamePairs = [(mycolor[0], ('Passed', passed)),
                                      (mycolor[1], ('Failed', failed)),
                                      (mycolor[2], ('No Run', norun))]
        self.width = 400
        self.legend.x = 350


def query_cycle(almSession, almUrl, cycleid):
    '''
    @type almSession: ALMSession
    @param almSession: instance of HPQC session
    @type almUrl: ALMUrl
    @param almUrl: instance of URL to access HPQC
    @type cycleid: str
    @param cycleid: testsed ID in HPQC
    @rtype: list
    @return: a list of testcase instance in the 'cycleid'
    '''

    query = 'test-instances?fields=id,name&query={cycle-id[%s];status[Failed]}'
    data = almSession.Get(almUrl, query % cycleid)

    entity = data[1][u'entities']
    instance_list = []
    for i in range(0, int(data[1][u'TotalResults'])):
        instanceId = entity[i][u'Fields'][0][u'values'][0][u'value']
        instanceName = entity[i][u'Fields'][1][u'values'][0][u'value']
        instance_dict = {}
        instance_dict['instanceId'] = instanceId
        instance_dict['instanceName'] = instanceName[:-4]
        instance_list.append(instance_dict)
    return instance_list


def query_instance(almSession, almUrl, cycleid, instance):
    '''
    @type almSession: ALMSession
    @param almSession: instance of HPQC session
    @type almUrl: ALMUrl
    @param almUrl: instance of URL to access HPQC
    @type cycleid: str
    @param cycleid: testsed ID in HPQC
    @type instance: dict
    @param instance: testcase instance
    @rtype: set
    @return: (has_bug_flag, case name) if failed case has linked bug
        has_bug_flag will be 1, case name is None. Otherwise,
        has_bug_flag will be 0, case name is the failed case name
    '''

    query2 = 'defect-links?fields=first-endpoint-id&query={second-end' \
        + 'point-type[test-instance];second-endpoint-id[%s]}'

    case_id = instance['instanceId']
    case_name = instance['instanceName']
    data = almSession.Get(almUrl, query2 % case_id)
    if data[1][u'TotalResults'] != 0:
        entity = data[1][u'entities']
        for i in range(0, int(data[1][u'TotalResults'])):
            defectId = entity[i][u'Fields'][1][u'values'][0][u'value']
            query_defect(almSession, almUrl, defectId, case_name, cycleid)
        return (1, "")
    else:
        return (0, case_name)


def query_defect(almSession, almUrl, defectId, case_name, cycleid):
    '''
    @type almSession: ALMSession
    @param almSession: instance of HPQC session
    @type almUrl: ALMUrl
    @param almUrl: instance of URL to access HPQC
    @type defectId: str
    @param defectId: bug number ID
    @type case_name: str
    @param case_name: name of test case
    @type cycleid: str
    @param cycleid: testsed ID in HPQC
    '''

    global bug_list
    query3 = 'defects?fields=user-template-01,name,status,priority,' \
        + 'detected-by,owner&query={id[%s]}'

    defect_data = almSession.Get(almUrl, query3 % defectId)
    bug_field = defect_data[1][u'entities'][0][u'Fields']
    bug_dict = parse_defect(bug_field, case_name, cycleid)
    if bug_dict not in bug_list:
        bug_list.append(bug_dict)


def parse_defect(bug_field, case_name, cycleid):
    '''
    @type bug_field: list
    @param bug_field: list of bug field such as 'reporter', 'priority'
    @type case_name: str
    @param case_name: the name of testcase which failed due to this bug
    @type cycleid: str
    @param cycleid: testsed ID in HPQC
    '''

    bug_dict = {}
    bug_dict['TestSet'] = cycleid
    bug_dict['Bug_ID'] = bug_field[6][u'values'][0][u'value']
    bug_dict['Status'] = bug_field[2][u'values'][0][u'value']
    bug_dict['Priority'] = bug_field[3][u'values'][0][u'value']
    bug_dict['Summary'] = bug_field[4][u'values'][0][u'value']
    bug_dict['Reporter'] = bug_field[1][u'values'][0][u'value']
    bug_dict['Assignee'] = bug_field[5][u'values'][0][u'value']
    bug_dict['Case_Num'] = 1
    bug_dict['CaseName'] = case_name
    return bug_dict


def query_result(almSession, almUrl, cycleid):
    '''
    @type almSession: ALMSession
    @param almSession: instance of HPQC session
    @type almUrl: ALMUrl
    @param almUrl: instance of URL to access HPQC
    @type cycleid: str
    @param cycleid: testsed ID in HPQC
    Global variable 'status_dict' will be updated
    '''

    global status_dict
    query4 = 'test-instances?fields=status&query={cycle-id[%s]}'

    data = almSession.Get(almUrl, query4 % cycleid)
    entity3 = data[1][u'entities']
    for i in range(0, int(data[1][u'TotalResults'])):
        status = entity3[i][u'Fields'][1][u'values'][0][u'value']
        if status == 'Passed':
            status_dict['Passed'] += 1
        elif status == 'Failed':
            status_dict['Failed'] += 1
        elif status == 'No Run':
            status_dict['No Run'] += 1


def getBugsByCycleID(almSession, almUrl, cycleid1, cycleid2):
    '''
    Get all bugs which were filed during test cycle
    @type almSession: ALMSession
    @param almSession: instance of ALMSession used to access HPQC
    @type almUrl: ALMUrl
    @param almUrl: instance of ALMUrl to query HPQC
    @type cycleid1: str
    @param cycleid1: start testset id
    @type cycleid2: str
    @param cycleid2: end testset id
    @return: None
    '''

    global No_bug_list

    for cycleid in range(int(cycleid1), int(cycleid2) + 1):
        instance_list = query_cycle(almSession, almUrl, cycleid)

        No_bug_dict = {'TestSet': cycleid, 'Case_Num': 0, 'Cases_Name': []}
        for instance in instance_list:
            (has_bug, case_name) = query_instance(almSession, almUrl,
                                                  cycleid, instance)
            if has_bug == 0:
                No_bug_dict['Case_Num'] += 1
                No_bug_dict['Cases_Name'].append(case_name)

        if No_bug_dict not in No_bug_list and No_bug_dict['Case_Num'] > 0:
            No_bug_list.append(No_bug_dict)

        query_result(almSession, almUrl, cycleid)


def main(args):
    '''
    Parse command line options specified by user
    Get user name and password
    Fetch bugs information from HPQC
    Generate PDF file per bugs
    Generate JSON file per bugs
    '''

    usage = "usage: python rpt.py [-l|--logdir] [-r|--resultdir] " \
            + " [-d|--domain] [-j|--project] [-c|--cycleid]" \
            + " [-u|--user] [-p|--password]"

    try:
        cmdOpts, _ = process_args(args, usage)
        if not cmdOpts.logdir:
            cmdOpts.logdir = cmdOpts.resultdir
        setup_logging(cmdOpts.logdir)
        log.info("reporttool cmdOpts are %s" % cmdOpts)
        if not cmdOpts.domain or not cmdOpts.project:
            log.error('domain or project is missing!')
            raise Exception('domain or project is missing!')
        if not cmdOpts.resultdir:
            log.error('resultdir is missing!')
            raise Exception('resultdir is missing!')
        if not cmdOpts.cycleid:
            log.error('At lease 1 cycleid!')
            raise Exception('cycleid is missing!')

        if cmdOpts.cyclename:
            report_name = cmdOpts.cyclename
        else:
            report_name = time.strftime('%Y.%m.%d_%H.%M.%S',
                                        time.localtime(time.time()))

        # innitial url and almsession
        base_url = 'https://quality.eng.vmware.com/qcbin'
        almUrl = ALMUrl(base_url, cmdOpts.domain, cmdOpts.project)
        if cmdOpts.user:
            user = cmdOpts.user
        else:
            user = raw_input('username:')
        if cmdOpts.password:
            password = cmdOpts.password
        else:
            password = getpass.getpass('password:')
        almSession = ALMSession(user, password)

        # authenticate
        if almSession.is_authed(almUrl) != 0:
            almSession.Open(almUrl)
        almSession.SessionManage(almUrl)

        global bug_list
        global No_bug_list
        global status_dict

        rangeList = cmdOpts.cycleid.split(',')
        for cycleRange in rangeList:
            if '-' in cycleRange:
                cycleid_list = cycleRange.split('-')
                getBugsByCycleID(almSession, almUrl, cycleid_list[0],
                                 cycleid_list[1])
            else:
                getBugsByCycleID(almSession, almUrl, cycleRange, cycleRange)

        # close session
        almSession.Close(almUrl)

        result_dic = {}
        for item in bug_list:
            if (item['Bug_ID'] not in result_dic.keys()):
                result_dic[item['Bug_ID']] = item['CaseName']
            elif result_dic[item['Bug_ID']] != item['CaseName']:
                temp_bug_id = result_dic[item['Bug_ID']]
                result_dic[item['Bug_ID']] = ''.join([temp_bug_id, '<br/>',
                                                     item['CaseName']])

        for key in result_dic.keys():
            for item in bug_list:
                if item['Bug_ID'] == key:
                    item['CaseName'] = result_dic[key]
                    item['Case_Num'] = len(item['CaseName'].split('<br/>'))

        Bug_list = []
        for item in bug_list:
            if item not in Bug_list:
                Bug_list.append(item)

        short_name = 'Rpt-' + report_name + '.json'
        json_file = os.path.join(cmdOpts.resultdir, short_name)
        with open(json_file, 'w') as fh:
            json.dump(Bug_list, fh)
        log.info("SUCCESS! Data (%s) is saved." % json_file)

        # pie chart
        global pieData
        pieData = status_dict
        piechart = PieChart()
        piechart.save(formats=['png'], outDir=cmdOpts.resultdir, fnRoot=None)

        # generate the report
        reportlab = Reportlab()
        reportlab.makeForm(Bug_list, No_bug_list, cmdOpts, report_name)

    except Exception as e:
        log.error(e)
        log.info(usage)
        exit()

if __name__ == "__main__":
    main(sys.argv[1:])
