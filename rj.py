# -*- coding: utf-8 -*-
# ! /usr/bin/python
from __future__ import division
import requests
import xml.etree.ElementTree as ET
import json
import logging
import os
import os.path
import sys
import getpass
import optparse
import re
import time

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, LongTable, TableStyle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin
from reportlab.lib.colors import Color, PCMYKColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.units import inch
ParagraphStyle.defaults['wordWrap'] = "CJK"

DEFAULT_DOMAIN = 'vsphere'
DEFAULT_PROJECT = 'esx'
DEFAULT_USER = 'yileiz'

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

    (options, args) = parser.parse_args(args)
    return (options, args)


def setup_logging(logdir):
    global log
    logfile = logdir + os.sep + 'reporttool.log'
    log = logging.getLogger('reporttool')
    logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)-8s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
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
        self.__work = self.__base + '/rest/domains/' + domain + '/projects/' + project

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
                              "Cookie": None}  # "Authorization":"Basic " + base64.b64encode(user + ':' + password)}
            self.__user_pass = (user, password)
        except:
            log.error("Exception while creating ALMSession", self.__headers, self.__h)

    def parse_xml(self, obj, dict):
        almxml = ET.fromstring(obj)
        if almxml.__dict__.has_key("TotalResults") and almxml.attrib["TotalResults"] == 0:
            return

        one_dict = {}
        for fields in almxml.findall('.//Fields'):
            one_dict.clear()
            for field in fields:
                curval = field.find("Value")
                if curval is not None and curval.text is not None:
                    one_dict[field.get('Name').decode('utf-8')] = curval.text  # field.find("Value").text
                    if isinstance(one_dict[field.get('Name')], str):
                        one_dict[field.get('Name').decode('utf-8')] = one_dict[field.get('Name')].decode('utf-8')
            dict.append(one_dict.copy())
        return

    def parse_json(self, obj):
        obj = json.loads(obj)
        return obj

    def is_authed(self, ALMUrl):
        r = requests.get(ALMUrl.get_isauth(),auth=self.__user_pass)
        if r.status_code == 200:
            log.info("Already authenticated, is_AUTH URL:%s\n" % ALMUrl.get_isauth())
            return 0
        elif r.status_code == 401:
            log.info("Not authenticated, is_AUTH URL:%s\n" % ALMUrl.get_isauth())
            return 1
        else:
            log.error("Open ALM session:%s,%s\n" % (
                r.status_code, r.reason) + 'is_AUTH URL:%s\n' % ALMUrl.ge_isauth())
            return int(r.status_code)

    def Open(self, ALMUrl):
        r = requests.get(ALMUrl.get_auth(), auth=self.__user_pass)
        if r.status_code is 200:
            mach = re.match(r'LWSSO_COOKIE_KEY=.*?;', r.headers['set-cookie'])
            self.__headers["Cookie"] = mach.group(0)
            log.info("Open ALM session success, AUTH URL:%s\n" % ALMUrl.get_auth() + 'HEADERS:%s\n' % self.__headers)
            return 0
        else:
            log.error("Open ALM session:%s,%s\n" % (
                r.status_code, r.reason) + 'AUTH URL:%s\n' % ALMUrl.ge_auth() + 'HEADERS:%s\n' % self.__headers)
            return int(r.status_code)

    def SessionManage(self, ALMUrl):
        if self.__headers["Cookie"] is not None:
            r = requests.post(ALMUrl.get_session(), headers=self.__headers, auth=self.__user_pass)
            if r.status_code == 201:
                pattern = re.compile('QCSession=.*?;')
                result = pattern.findall(r.headers['set-cookie'])
                self.__headers["Cookie"] += result[0]
                log.info("[ALMSession] Get session success, URL:%s\n" % ALMUrl.get_session() + 'HEADERS:%s\n' % self.__headers)
                return 0
            else:
                log.error("[ALMSession] Get session failed, URL:%s\n" % ALMUrl.get_session() + "HEADERS:%s\n" % self.__headers)
                return int(r.status_code), None

    def Close(self, ALMUrl):
        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.get_logout(), headers=self.__headers, auth=self.__user_pass)
            if r.status_code is 200:
                log.info(
                    "Close ALM session success. LOGOUT URL:%s\n" % ALMUrl.get_logout())
                return 0
            else:
                log.error("Close ALM session:%s, %s\n" % (
                    r.status_code,
                    r.reason) + 'LOGOUT URL:%s\n' % ALMUrl.get_logout() + 'HEADERS:%s\n' % self.__headers)
                return int(r.status_code)
        else:
            log.error("Close ALM session.  httplib2.Http was not initialized")
            return 1

    def RawGet(self, url):
        if self.__headers["Cookie"] is not None:
            r = requests.get(url, headers=self.__headers)
            if r.status_code == 200:
                log.info(
                    "[ALMSession] Get success, URL:%s\n" % ALMUrl.__getattr__(*args))
                data = self.parse_json(r.content)
                return 0, data
            else:
                log.error("[ALMSession] Get ALM function with errors:%s,%s\n" % (
                    r.status_code, r.reason) + "PATH:%s\n" % ALMUrl.__getattr__(
                    *args) + "HEADERS:%s\n" % self.__headers)
                return int(r.status_code), None
        else:
            log.error("[ALMSession] Get ALM function with errors.  httplib2.Http not initialized")
            return 1, None

    def Get(self, ALMUrl, *args):
        if self.__headers["Cookie"] is not None:
            r = requests.get(ALMUrl.__getattr__(*args), headers=self.__headers)
            if r.status_code == 200:
                log.info(
                    "[ALMSession] Get success, URL:%s\n" % ALMUrl.__getattr__(*args))
                # res = []
                # self.parse_xml(r.content, res)
                data = self.parse_json(r.content)
                return 0, data
            # elif r.status_code == 500:
            #     try:
            #         if isinstance(r.text, unicode):
            #             exceptionxml = ET.fromstring(r.text.encode('utf8', 'ignore'))
            #         else:
            #             exceptionxml = ET.fromstring(r.text)
            #         log.error("[ALMSession] Get ALM function with errors:%s, %s\n" % (
            #             exceptionxml[0].text, exceptionxml[1].text) + "PATH:%s\n" % ALMUrl.__getattr__(
            #             *args) + "HEADERS:%s\n" % self.__headers)
            #     except ET.ParseError:
            #         log.error(
            #             "[ALMSession] Get ALM function with errors, returned message is not XML.\nPATH:%s\n" % ALMUrl.__getattr__(
            #                 *args) + "HEADERS:%s %s\n" % (self.__headers, ET.ParseError.message))
            #     return int(r.status_code), None
            else:
                log.error("[ALMSession] Get ALM function with errors:%s,%s\n" % (
                    r.status_code, r.reason) + "PATH:%s\n" % ALMUrl.__getattr__(
                    *args) + "HEADERS:%s\n" % self.__headers)
                return int(r.status_code), None
        else:
            log.error("[ALMSession] Get ALM function with errors.  httplib2.Http not initialized")
            return 1, None


class Reportlab:
    def makeForm(self, bug_list, No_bug_list, cmdOpts):
        story = []
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']

        print "Jian: 1"
        # report title
        rpt_title = '<para autoLeading="off" fontSize=15 align=center><b>Report for TestSet %s</b><br/><br/><br/></para>' % (
            cmdOpts.cycleid)
        story.append(Paragraph(rpt_title, normalStyle))

        print "Jian: 2"
        # test pie chart img
        text = '<para autoLeading="off" fontSize=9 align=center><br/><b>1.Test Result</b><br/></para>'
        story.append(Paragraph(text, normalStyle))
        img = Image(cmdOpts.resultdir + 'PieChart000.png')
        img.drawHeight = 150
        img.drawWidth = 300
        story.append(img)

        print "Jian: 3"
        # bug list table
        text = '<para autoLeading="off" fontSize=9 align=center><br/><br/><br/><br/><b>2.Bug List</b><br/></para><br/>'
        text = '<para autoLeading="off" fontSize=9 align=center><br/><b>2.Bug List</b></para><br/>'
        text = 'sakdfjkajkfjaskjfkajskdfjkjafdjsafsa;flksajdfsjadklfjksla'
        print "Jian: 3.1"
        print text
        print "Jian: 3.2"
        aaaa = Paragraph(text,normalStyle)
        print "Jian: 3.3"
        print aaaa
        print "Jian: 3.4"
        story.append(Paragraph(text,normalStyle))
        print "Jian: 3.2"
        component_data = [['TestsetID','BugID', 'Summary', 'Status', 'Priority', 'Reporter', 'Assign_to', 'Case_num', 'Case_name']]
        print "Jian: 3.3"
        for item in bug_list:
            Cycle_ID = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Cycle_ID"]),
                                normalStyle)
            Bug_ID = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Bug_ID"]),
                                normalStyle)
            Summary = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Summary"]),
                               normalStyle)
            Status = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Status"]),
                                normalStyle)
            Priority = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Priority"]),
                                normalStyle)
            Reporter = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Reporter"]),
                                normalStyle)
            Assigned_to = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Assigned_to"]),
                                normalStyle)
            Case_num = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Case_num"]),
                                normalStyle)
            Case_name = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Case_name"]),
                                normalStyle)
            component_data.append([Cycle_ID, Bug_ID, Summary, Status, Priority, Reporter, Assigned_to, Case_num, Case_name])

        print "Jian: 4"
        component_table = LongTable(component_data, colWidths=[35, 35, 160, 35, 30, 48, 48, 30, 150])
        component_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (0, 0), (0, -1), 0.1, colors.grey),
            ('TEXTCOLOR', (0, 1), (-2, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ]))
        story.append(component_table)

        print "Jian: 5"
        # no bug list table
        text = '<para autoLeading="off" fontSize=9 align=center><br/><br/><br/><br/><b>3.Failed cases with no Bug Linked</b><br/></para><br/>'
        text = '3.Failed cases with no Bug Linked'
        # story.append(Paragraph(text, normalStyle))
        component_data = [['TestsetID','Case_num', 'Case_name']]
        for item in No_bug_list:
            Cycle_ID = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Cycle_ID"]),
                                 normalStyle)
            Case_num = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Case_num"]),
                                 normalStyle)
            Case_name = Paragraph('<para autoLeading="off" fontSize=5.5 align=left>%s</para>' % (item["Case_name"]),
                                  normalStyle)
            component_data.append([Cycle_ID, Case_num, Case_name])

        print "Jian: 6"
        component_table = LongTable(component_data, colWidths=[35, 35, 500])
        component_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (0, 0), (0, -1), 0.1, colors.grey),
            ('TEXTCOLOR', (0, 1), (-2, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ]))
        story.append(KeepTogether([Paragraph(text, normalStyle), component_table]))

        print "Jian: 7"
        date = time.strftime('%Y.%m.%d', time.localtime(time.time()))
        doc = SimpleDocTemplate(cmdOpts.resultdir + 'Report-%s.pdf' % date)
        doc.build(story)

class PieChart(_DrawingEditorMixin,Drawing):
    '''
        pie chart with a basic legend.
    '''
    def __init__(self,width=400,height=200,*args, **kw):
        Drawing.__init__(self,width,height,*args, **kw)
        global pieData
        colors = [PCMYKColor(100, 0, 90, 50, alpha=100), PCMYKColor(0, 100, 100, 40, alpha=100),
                  PCMYKColor(66, 13, 0, 22, alpha=100)]
        total = pieData['Passed'] + pieData['Failed'] + pieData['No Run']
        passed, failed, norun = '0', '0', '0'
        if total != 0:
            passed = str(round(float(pieData['Passed'] / total) * 100, 2)) + '%'
            failed = str(round(float(pieData['Failed'] / total) * 100, 2)) + '%'
            norun = str(round(float(pieData['No Run'] / total) * 100, 2)) + '%'
            #pie
            self._add(self, Pie(), name='pie', validate=None, desc=None)
            self.pie.strokeWidth = 1
            self.pie.slices.strokeColor = PCMYKColor(0,0,0,0)
            self.pie.slices.strokeWidth = 1
            self.pie.data = [pieData['Passed'], pieData['Failed'], pieData['No Run']]
            for i in range(len(self.pie.data)):
                self.pie.slices[i].fillColor = colors[i]
            self.pie.strokeColor = PCMYKColor(0, 0, 0, 0, alpha=100)
            self.pie.slices[1].fillColor = PCMYKColor(0, 100, 100, 40, alpha=100)
            self.pie.slices[2].fillColor = PCMYKColor(66, 13, 0, 22, alpha=100)
            self.pie.slices[0].fillColor = PCMYKColor(100, 0, 90, 50, alpha=100)
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

        self.legend.colorNamePairs = [(PCMYKColor(100, 0, 90, 50, alpha=100), ('Passed', passed)),
                                      (PCMYKColor(0, 100, 100, 40, alpha=100), ('Failed', failed)),
                                      (PCMYKColor(66, 13, 0, 22, alpha=100), ('No Run', norun))]
        self.width = 400
        self.legend.x = 350



def getBugsByCycleID(almSession, almUrl, cycleid1, cycleid2):
    global bug_list
    global status_dict
    for cycleid in range(int(cycleid1), int(cycleid2) + 1):
        data = almSession.Get(almUrl, "test-instances?fields=id,name&query={cycle-id[%s];status[Failed]}" % cycleid)

        instance_list = []
        for i in range(0, int(data[1][u'TotalResults'])):
            instanceId = data[1][u'entities'][i][u'Fields'][0][u'values'][0][u'value']
            instanceName = data[1][u'entities'][i][u'Fields'][1][u'values'][0][u'value']
            instance_dict = {}
            instance_dict['instanceId'] = instanceId
            instance_dict['instanceName'] = instanceName[:-4]
            instance_list.append(instance_dict)

        # get defectId_linked
        caseName_NoBug = ''  # casename list for cases without bug linked
        No_bug_dict = {}
        for instance in instance_list:
            data = almSession.Get(almUrl,
                                  "defect-links?fields=first-endpoint-id&query={second-endpoint-type[test-instance];second-endpoint-id[%s]}" %
                                  instance['instanceId'])

            if data[1][u'TotalResults'] != 0:
                for i in range(0, int(data[1][u'TotalResults'])):
                    defectId = data[1][u'entities'][i][u'Fields'][1][u'values'][0][u'value']

                    # get bug_list
                    defect_data = almSession.Get(almUrl,
                                                 "defects?fields=user-template-01,name,status,priority,detected-by,owner&query={id[%s]}" % defectId)

                    bug_dict = {}
                    bug_dict['Cycle_ID'] = cycleid
                    bug_dict['Bug_ID'] = defect_data[1][u'entities'][0][u'Fields'][6][u'values'][0][u'value']
                    bug_dict['Status'] = defect_data[1][u'entities'][0][u'Fields'][2][u'values'][0][u'value']
                    bug_dict['Priority'] = defect_data[1][u'entities'][0][u'Fields'][3][u'values'][0][u'value']
                    bug_dict['Summary'] = defect_data[1][u'entities'][0][u'Fields'][4][u'values'][0][u'value']
                    bug_dict['Reporter'] = defect_data[1][u'entities'][0][u'Fields'][1][u'values'][0][u'value']
                    bug_dict['Assigned_to'] = defect_data[1][u'entities'][0][u'Fields'][5][u'values'][0][u'value']
                    bug_dict['Case_num'] = 1
                    bug_dict['Case_name'] = instance['instanceName']
                    if bug_dict not in bug_list:
                        bug_list.append(bug_dict)
                exit()

            else:
                caseName_NoBug = ''.join([caseName_NoBug, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;', instance['instanceName']])

        No_bug_dict['Cycle_ID'] = cycleid
        No_bug_dict['Case_num'] = len(caseName_NoBug.split('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')) - 1
        No_bug_dict['Case_name'] = caseName_NoBug.lstrip('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')

        if No_bug_dict not in No_bug_list and No_bug_dict['Case_name'] != '':
            No_bug_list.append(No_bug_dict)

        # get all the test istances
        data = almSession.Get(almUrl, "test-instances?fields=status&query={cycle-id[%s]}" % cycleid)
        for i in range(0, int(data[1][u'TotalResults'])):
            status = data[1][u'entities'][i][u'Fields'][1][u'values'][0][u'value']
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

        # innitial url and almsession
        almUrl = ALMUrl(cmdOpts.domain, cmdOpts.project)
        #user = raw_input('username:')
        #password = getpass.getpass('password:')
        user = 'lij'
        password = 'You5rong!'
        almSession = ALMSession(user, password)

        # authenticate
        if almSession.is_authed(almUrl) != 0:
            almSession.Open(almUrl)
        almSession.SessionManage(almUrl)

        global bug_list
        global No_bug_list
        global status_dict

#        print almSession.Get(almUrl,'vSphere2013')
#        print almSession.Get(almUrl,'TestLab')
#        print almSession.Get(almUrl,'Testing', 'TestLab')
#        print almSession.Get(almUrl,'Testing', 'Test Lab')
        print almSession.RawGet('https://quality.env.vmware.com/qcbin/api/domains/VSPHERE/projects/ESX/list-items')
        print almSession.Get(almUrl,'vSphere2013')
        print almSession.Get(almUrl,'vSphere2013')
        print almSession.Get(almUrl,'vSphere2013')
        print almSession.Get(almUrl,'vSphere2013')
        print almSession.Get(almUrl,'vSphere2013')
        print almSession.Get(almUrl,'vSphere2013')
        exit(0)

        #almUrl += '/qcbin/api/domains/DOMAIN_NAME/projects/PROJECT_NAME/list-items'
        print "Jian: ============== Do my own experiment ==============="
        #getTree(almSession, almUrl)
        print "Jian: ============== Do my own experiment ==============="
        exit(0)

        print "Jian: ============== Ready to get cycle range ==============="
        rangeList = cmdOpts.cycleid.split(',')
        for cycleRange in rangeList:
            if '-' in cycleRange:
                cycleid_list = cycleRange.split('-')
                getBugsByCycleID(almSession, almUrl, cycleid_list[0], cycleid_list[1])
            else:
                getBugsByCycleID(almSession, almUrl, cycleRange, cycleRange)

        print "Jian: ============== Ready to get result_dict ==============="
        result_dic = {}
        for item in bug_list:
            if (item['Bug_ID'] not in result_dic.keys()):
                result_dic[item['Bug_ID']] = item['Case_name']
            elif result_dic[item['Bug_ID']] != item['Case_name']:
                result_dic[item['Bug_ID']] = ''.join([result_dic[item['Bug_ID']], '<br/>', item['Case_name']])
        print "Jian: result dic"
        print result_dic

        print "Jian: ============== Ready to get item ==============="
        for key in result_dic.keys():
            for item in bug_list:
                if item['Bug_ID'] == key:
                    item['Case_name'] = result_dic[key]
                    item['Case_num'] = len(item['Case_name'].split('<br/>'))
        print "Jian: bug item"
        #print bug_list

        print "Jian: ============== Ready to get bug list ==============="
        Bug_list = []
        for item in bug_list:
            if item not in Bug_list:
                Bug_list.append(item)
        print "Jian: Bug_list"
        print Bug_list

        print "Jian: ============== Ready to generate pie chart ==============="
        # pie chart
        global pieData
        pieData = status_dict
        piechart = PieChart()
        piechart.save(formats=['png'], outDir=cmdOpts.resultdir, fnRoot=None)
        print "Jian: status_dict"
        print  status_dict

        # generate the report

        print "Jian: ============== Ready to generate report ==============="
        print "Jian: No_bug_list"
        print  No_bug_list
        reportlab = Reportlab()
        reportlab.makeForm(Bug_list, No_bug_list, cmdOpts)

        print "Jian: ============== Ready to exit session ==============="
        # close session
        almSession.Close(almUrl)

    except Exception as e:
        log.error(e)
        log.info("usage: python reporttool_v5.0.py [-l|--logdir] [-r|--resultdir] [-d|--domain] [-j|--project] [-c|--cycleid]")
        exit()

if __name__ == "__main__":
    main(sys.argv[1:])