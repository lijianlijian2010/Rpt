# -*- coding: utf-8 -*-
# ! /usr/bin/python
import requests
import json
import logging
import os
import glob
import sys
import getpass
import optparse
import re
import time

from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, \
        Image, Table, LongTable, TableStyle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin
from reportlab.lib.colors import Color, PCMYKColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.flowables import KeepTogether

DEFAULT_DOMAIN = 'vsphere'
DEFAULT_PROJECT = 'esx'

log = logging.getLogger(__name__)
loglevel = os.environ.get('LOGLEVEL', 'DEBUG')
log.setLevel(loglevel)

pieData = {}
bug_list = []
No_bug_list = []
status_dict = {'Passed': 0, 'Failed': 0, 'No Run': 0}

def process_args(args):
    usage = "usage: python HP_ALM_REST_API_CLENT.py [domain] -d [top k]"
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
    parser.add_option("-t", "--topn", dest="topn", action="store",
                      type="string", help="cases or features or bugs")

    (options, args) = parser.parse_args(args)
    return (options, args)


def setup_logging(logdir):
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
    def __init__(self, domain, project):
        self.__base = 'https://quality.eng.vmware.com/qcbin'
        self.__isauth = self.__base + '/rest/is-authenticated'
        self.__auth = self.__base + '/authentication-point/authenticate'
        self.__session = self.__base + '/rest/site-session'
        self.__logout = self.__base + '/authentication-point/logout'
        self.__work = self.__base + '/rest/domains/' + domain \
                                  + '/projects/' + project

    def get_isauth(self):
        return self.__isauth

    def get_auth(self):
        return self.__auth

    def get_session(self):
        return self.__session

    def get_logout(self):
        return self.__logout

    def __getattr__(self, *args):
        result = self.__work
        for arg in args:
            result += '/' + arg
        return result


class ALMSession:
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

    def parse_xml(self, obj, dict):
        almxml = ET.fromstring(obj)
        if almxml.__dict__.has_key("TotalResults") \
                and almxml.attrib["TotalResults"] == 0:
            return

        one_dict = {}
        for fields in almxml.findall('.//Fields'):
            one_dict.clear()
            for field in fields:
                curval = field.find("Value")
                if curval is not None and curval.text is not None:
                    one_dict[field.get('Name').decode('utf-8')] = curval.text
                    if isinstance(one_dict[field.get('Name')], str):
                        one_dict[field.get('Name').decode('utf-8')] \
                                = one_dict[field.get('Name')].decode('utf-8')
            dict.append(one_dict.copy())
        return

    def parse_json(self, obj):
        obj = json.loads(obj)
        return obj

    def is_authed(self, ALMUrl):
        r = requests.get(ALMUrl.get_isauth(),auth=self.__user_pass)
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
        if self.__headers["Cookie"] is not None:
            r = requests.post(ALMUrl.get_session(), headers=self.__headers,
                              auth=self.__user_pass)
            if r.status_code == 201:
                pattern = re.compile('QCSession=.*?;')
                result = pattern.findall(r.headers['set-cookie'])
                self.__headers["Cookie"] += result[0]
                log.info("[ALMSession] Get session success, URL:%s" \
                        % ALMUrl.get_session() + 'HEADERS:%s' % self.__headers)
                return 0
            else:
                log.error("[ALMSession] Get session failed, URL:%s" \
                        % ALMUrl.get_session() + "HEADERS:%s" % self.__headers)
                return int(r.status_code), None

    def Close(self, ALMUrl):
        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.get_logout(), headers=self.__headers,
                             auth=self.__user_pass)
            if r.status_code is 200:
                log.info(
                    "Logout ALM session success: %s" % ALMUrl.get_logout())
                return 0
            else:
                log.error("Failed to close ALM session:%s, %s" \
                        % (r.status_code, r.reason))
                log.error('LOGOUT URL:%s' % ALMUrl.get_logout())
                log.error('HEADERS:%s' % self.__headers)
                return int(r.status_code)
        else:
            log.error("Close ALM session.  httplib2.Http was not initialized")
            return 1

    def Get(self, ALMUrl, *args):
        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.__getattr__(*args), headers=self.__headers)
            if r.status_code == 200:
                log.info("[ALMSession] Get success, URL:%s" \
                        % ALMUrl.__getattr__(*args))
                data = self.parse_json(r.content)
                return 0, data
            else:
                log.error("[ALMSession] Error getting ALM function: %s,%s" \
                        % ( r.status_code, r.reason))
                log.error("PATH:%s" % ALMUrl.__getattr__(*args))
                log.error("HEADERS:%s" % self.__headers)
                return int(r.status_code), None
        else:
            log.error("[ALMSession] Error: httplib2.Http not initialized")
            return 1, None


class Reportlab:
    def makeForm(self, bug_list, No_bug_list, cmdOpts, report_name):
        story = []
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']

        # report title
        data_format = '<para autoLeading="off" fontSize=15 align=center>' \
                + '<b>Report for Cycle %s</b><br/><br/><br/></para>'
        rpt_title = data_format % (report_name)
        story.append(Paragraph(rpt_title, normalStyle))

        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
                + '<br/><b>1. Test Set ID: %s </b><br/></para>'
        text = data_format %cmdOpts.cycleid
        story.append(Paragraph(text, normalStyle))
        # test pie chart img
        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
                + '<br/><b>2. Test Result</b><br/></para>'
        text = data_format
        story.append(Paragraph(text, normalStyle))
        img = Image(os.path.join(cmdOpts.resultdir, 'PieChart000.png'))
        img.drawHeight = 150
        img.drawWidth = 300
        story.append(img)

        # bug list table
        data_format = '<para autoLeading="off" fontSize=9 align=center>' \
                + '<b>3. Bug List</b><br/></para>'
        text = data_format
        story.append(Paragraph(text,normalStyle))

        mylist = ['TestSet', 'Bug_ID', 'Summary', 'Status', \
            'Priority', 'Reporter', 'Assignee', 'Case_Num', 'CaseName']
        component_data = [ mylist ]
        th_fmt = '<para autoLeading="off" fontSize=5.5 align=left>%s</para>'
        for item in bug_list:
            x = [ Paragraph(th_fmt % (item[entry]), normalStyle) \
                    for entry in mylist ]
            component_data.append(x)

        component_table = LongTable(component_data, \
                colWidths=[35, 35, 160, 35, 30, 48, 48, 30, 150])
        table_style = TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (0, 0), (0, -1), 0.1, colors.grey),
            ('TEXTCOLOR', (0, 1), (-2, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ])
        component_table.setStyle(table_style)
        story.append(component_table)

        # no bug list table
        text = '<para autoLeading="off" fontSize=9 align=center><br/><b>' \
                + '4.Failed cases with no Bug Linked</b><br/></para>'
        my2list = ['TestsetID','Case_Num', 'CaseName']
        component_data = [ my2list ]
        for item in No_bug_list:
            x = [ Paragraph(th_fmt % (item[entry]), normalStyle) \
                    for entry in my2list ]
            component_data.append(x)

        component_table = LongTable(component_data, colWidths=[35, 35, 500])
        component_table.setStyle(table_style)
        para_no_bug = Paragraph(text, normalStyle)
        story.append(KeepTogether([para_no_bug, component_table]))

        doc = SimpleDocTemplate(os.path.join(cmdOpts.resultdir, \
                'Rpt-' + report_name + '.pdf'))
        doc.build(story)


class PieChart(_DrawingEditorMixin,Drawing):
    '''
        pie chart with a basic legend.
    '''
    def __init__(self,width=400,height=200,*args, **kw):
        Drawing.__init__(self,width,height,*args, **kw)
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
            #pie
            self._add(self, Pie(), name='pie', validate=None, desc=None)
            self.pie.strokeWidth = 1
            self.pie.slices.strokeColor = PCMYKColor(0,0,0,0)
            self.pie.slices.strokeWidth = 1
            self.pie.data = [num_pass, num_fail, num_norun]
            for i in range(len(self.pie.data)):
                self.pie.slices[i].fillColor = mycolor[i]
            self.pie.strokeColor = PCMYKColor(0, 0, 0, 0, alpha=100)
            self.pie.width = 150
            self.pie.height = 150
            self.pie.y = 25
            self.pie.x = 25
        #legend
        self._add(self,Legend(),name='legend',validate=None,desc=None)
        self.legend.columnMaximum = 99
        self.legend.alignment='right'
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



def getBugsByCycleID(almSession, almUrl, cycleid1, cycleid2):
    global bug_list
    global status_dict
    query = "test-instances?fields=id,name&query={cycle-id[%s];status[Failed]}"
    query2 = "defect-links?fields=first-endpoint-id&query={second-end" \
            + "point-type[test-instance];second-endpoint-id[%s]}"
    query3 = "defects?fields=user-template-01,name,status,priority," \
            + "detected-by,owner&query={id[%s]}"
    query4 = "test-instances?fields=status&query={cycle-id[%s]}"
    nbsp_str = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'

    for cycleid in range(int(cycleid1), int(cycleid2) + 1):
        data = almSession.Get(almUrl, query % cycleid)

        instance_list = []
        myentity = data[1][u'entities']
        for i in range(0, int(data[1][u'TotalResults'])):
            instanceId = myentity[i][u'Fields'][0][u'values'][0][u'value']
            instanceName = myentity[i][u'Fields'][1][u'values'][0][u'value']
            instance_dict = {}
            instance_dict['instanceId'] = instanceId
            instance_dict['instanceName'] = instanceName[:-4]
            instance_list.append(instance_dict)

        # get defectId_linked
        caseName_NoBug = ''  # casename list for cases without bug linked
        No_bug_dict = {}
        for instance in instance_list:
            data = almSession.Get(almUrl, query2 % instance['instanceId'])

            if data[1][u'TotalResults'] != 0:
                entity = data[1][u'entities']
                for i in range(0, int(data[1][u'TotalResults'])):
                    defectId = entity[i][u'Fields'][1][u'values'][0][u'value']

                    # get bug_list
                    defect_data = almSession.Get(almUrl, query3 % defectId)
                    bug_field = defect_data[1][u'entities'][0][u'Fields']
                    bug_dict = {}
                    bug_dict['TestSet'] = cycleid
                    bug_dict['Bug_ID'] = bug_field[6][u'values'][0][u'value']
                    bug_dict['Status'] = bug_field[2][u'values'][0][u'value']
                    bug_dict['Priority'] = bug_field[3][u'values'][0][u'value']
                    bug_dict['Summary'] = bug_field[4][u'values'][0][u'value']
                    bug_dict['Reporter'] = bug_field[1][u'values'][0][u'value']
                    bug_dict['Assignee'] = bug_field[5][u'values'][0][u'value']
                    bug_dict['Case_Num'] = 1
                    bug_dict['CaseName'] = instance['instanceName']
                    if bug_dict not in bug_list:
                        bug_list.append(bug_dict)
            else:
                caseName_NoBug = ''.join([caseName_NoBug, nbsp_str, \
                        instance['instanceName']])

        No_bug_dict['TestSet'] = cycleid
        No_bug_dict['Case_Num'] = len(caseName_NoBug.split(nbsp_str)) - 1
        No_bug_dict['CaseName'] = caseName_NoBug.lstrip(nbsp_str)

        if No_bug_dict not in No_bug_list and No_bug_dict['CaseName'] != '':
            No_bug_list.append(No_bug_dict)

        # get all the test istances
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


def main(args):
    try:
        cmdOpts, _ = process_args(args)
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
            report_name = time.strftime('%Y.%m.%d_%H.%M.%S', \
                    time.localtime(time.time()))

        # innitial url and almsession
        almUrl = ALMUrl(cmdOpts.domain, cmdOpts.project)
        user = raw_input('username:')
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
                getBugsByCycleID(almSession, almUrl, cycleid_list[0], \
                        cycleid_list[1])
            else:
                getBugsByCycleID(almSession, almUrl, cycleRange, cycleRange)

        result_dic = {}
        for item in bug_list:
            if (item['Bug_ID'] not in result_dic.keys()):
                result_dic[item['Bug_ID']] = item['CaseName']
            elif result_dic[item['Bug_ID']] != item['CaseName']:
                temp_bug_id = result_dic[item['Bug_ID']]
                result_dic[item['Bug_ID']] = ''.join(temp_bug_id, 
                        '<br/>', item['CaseName'])

        for key in result_dic.keys():
            for item in bug_list:
                if item['Bug_ID'] == key:
                    item['CaseName'] = result_dic[key]
                    item['Case_Num'] = len(item['CaseName'].split('<br/>'))

        Bug_list = []
        for item in bug_list:
            if item not in Bug_list:
                Bug_list.append(item)

        json_file = os.path.join(cmdOpts.resultdir, \
                'Rpt-' + report_name + '.json')
        with open(json_file, 'w') as fh:
            json.dump(Bug_list, fh)

        with open(json_file, 'r') as fh:
            b2 = json.load(fh)

        # pie chart
        global pieData
        pieData = status_dict
        piechart = PieChart()
        piechart.save(formats=['png'], outDir=cmdOpts.resultdir, fnRoot=None)

        # generate the report
        reportlab = Reportlab()
        reportlab.makeForm(Bug_list, No_bug_list, cmdOpts, report_name)

        # close session
        almSession.Close(almUrl)

    except Exception as e:
        usage = "usage: python rpt.py [-l|--logdir] [-r|--resultdir] " \
                + " [-d|--domain] [-j|--project] [-c|--cycleid]"
        log.error(e)
        log.info(usage)
        exit()

if __name__ == "__main__":
    main(sys.argv[1:])
