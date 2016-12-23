# -*- coding: utf-8 -*-
# ! /usr/bin/python
from __future__ import division
import json
import logging
import os
import glob
import sys
import optparse
import re
import time
from bug2html import *

log = logging.getLogger(__name__)
loglevel = os.environ.get('LOGLEVEL', 'DEBUG')
log.setLevel(loglevel)
usage = 'usage: python topn.py <-r|--resultdir> <-t|--topn>'

def process_args(args):
    global usage
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-r", "--resultdir", dest="resultdir", action="store",
                      type="string", help=" result directory")
    parser.add_option("-t", "--topn", dest="topn", action="store",
                      type="string", help="cases or features or bugs")

    (options, args) = parser.parse_args(args)
    return options

def setup_logging(logdir):
    global log
    logfile = os.path.join(logdir, 'topn.log')
    log = logging.getLogger('ABCD')
    logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)-8s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG)
    log.setLevel(loglevel)

    fh = logging.FileHandler(logfile)
    fh.setLevel(loglevel)
    log.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    log.addHandler(ch)


def collect_topn(resultdir, file_filter):
    error_cases = {}
    all_bug = {}
    file_name = 'Rpt-'+file_filter+'*.json'
    for filename in glob.glob(os.path.join(resultdir, file_name)):
        print filename
        with open(filename, 'r') as json_data:
            bug_data = json.load(json_data)
        for old_bug in bug_data:
            #print old_bug
            Case_name = old_bug['Case_name']
            bug_id = old_bug['Bug_ID']
            print "Dealing with Bug: " + bug_id + " Case Name: " + Case_name
            old_bug.pop('Case_name')
            old_bug.pop('Case_num')
            all_bug[bug_id] = old_bug

            case_list = Case_name.split('<br/>')
            for case_name in case_list:
                if case_name in error_cases.keys():
                    that_bug_list = error_cases[case_name]['bugIDs']
                    if bug_id in that_bug_list:
                        print "bug_id (" + bug_id + ") is already been in the list."
                    else:
                        error_cases[case_name]['bugIDs'].append(bug_id)
                        error_cases[case_name]['bug_nums'] += 1
                else:
                    error_cases[case_name] = {'bug_nums': 1, 'bugIDs': [bug_id]}
                    print "=================== ERROR_CASES ======================"
                    print error_cases
                    print "================================================="
    sorted_cases = sorted(error_cases, key=lambda x: error_cases[x]['bug_nums'])
    sorted_cases.reverse()

    html_data = ["<center><h1>TopN Error Cases of All %s</h1></center>\n" % file_filter]

    cases_num = len(error_cases.keys())
    sum1_data = '<table border="0"><tr><th align=left>Failed Cases Number: %d</th></tr>' % cases_num
    sum2_data = '<tr><th align=left>Generated Bugs Number: %d</th></tr></table>' % len(all_bug.keys())

    html_data.append(sum1_data + sum2_data + '<br>\n')

    order = ['Bug_ID', 'Priority', 'Status', 'Reporter', 'Assigned_to', 'Cycle_ID', 'Summary']
    for entry in sorted_cases:
        print "================================================="
        print entry
        print "================================================="
        bug_detail_list = [ all_bug[bug_id] for bug_id in sorted(error_cases[entry]['bugIDs']) ]
        print "---------------------------------------------------------"
        print bug_detail_list
        print "================================================="

        aaa= bug2html.convert(json={
           entry: error_cases[entry]['bug_nums'],
           'Bug List': bug_detail_list
           },order_list=order)
        print "---------------------------------------------------------"
        print aaa
        print "---------------------------------------------------------"
        html_data.append(bug2html.convert(json={
           entry: error_cases[entry]['bug_nums'],
           'Bug List': bug_detail_list
           },order_list=order))

    html_file = "TopN-%s.html" % file_filter
    all_str = '\n<br/>'.join(html_data)

    html_fh = open(os.path.join(resultdir, html_file), 'w')
    html_fh.write(all_str)
    html_fh.close()

def main(args):
    global usage

    cmdOpts = process_args(args)
    if not cmdOpts.resultdir:
        print 'Must provide "resultdir" to generate topN'
        print usage
        exit()

    cmdOpts.logdir = cmdOpts.resultdir
    setup_logging(cmdOpts.logdir)
    log.info("TopN cmdOpts are %s" % cmdOpts)

    if not cmdOpts.topn:
        log.error('Please specifiy TopN option')
        log.error('It means the file filter you want to collect case info.')
        log.info(usage)
        exit()
    else:
        collect_topn(cmdOpts.resultdir, cmdOpts.topn)
        print "Jian: SUCCESS"

if __name__ == "__main__":
    main(sys.argv[1:])
