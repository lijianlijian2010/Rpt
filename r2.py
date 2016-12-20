# -*- coding: utf-8 -*-
# ! /usr/bin/python
from __future__ import division
import requests
#import xml.etree.ElementTree as ET
import json
import logging
import os
import glob
import sys
import getpass
import optparse
import re
import time
from json2html import *

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
    #print "================================================="
    #print error_cases
    #print "================================================="
    sorted_cases = sorted(error_cases, key=lambda x: error_cases[x]['bug_nums'])
    sorted_cases.reverse()
    #print "---------------------------------------------------------"
    #print sorted_cases
    #print "---------------------------------------------------------"
    html_data = ["<center><h1>TopN Error Cases of All %s</h1></center>" % file_filter]
    for entry in sorted_cases:
        print "================================================="
        print entry
        print "================================================="
        #for bug_id in error_cases[entry]['bugIDs']:
        bug_detail_list = [ all_bug[bug_id] for bug_id in sorted(error_cases[entry]['bugIDs']) ]
        print "---------------------------------------------------------"
        print bug_detail_list
        print "================================================="

        html_data.append(json2html.convert(json={
           entry: error_cases[entry]['bug_nums'],
           'Bug list': bug_detail_list
           }))

    html_file = "TopN-%s.html" % file_filter
    all_str = '\n<br/>'.join(html_data)

    html_fh = open(os.path.join(resultdir, html_file), 'w')
    html_fh.write(all_str)
    html_fh.close()


def main(args):

    collect_topn('/home/jian/tr', 'iteration')


if __name__ == "__main__":
    main(sys.argv[1:])
