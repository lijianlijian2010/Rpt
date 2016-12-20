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

def collect_topn(resultdir):
    error_cases = {}
    files = '*iteration*.json'
    print resultdir
    for filename in glob.glob(os.path.join(resultdir, files)):
        print filename
        with open(filename, 'r') as json_data:
            data = json.load(json_data)
        for entry in data:
            print entry
            casename = entry['Case_name']
            print error_cases.keys()

            if casename in error_cases.keys():
                error_cases[casename]['bug_nums'] += 1
                error_cases[casename]['bugs'].append(entry)
            else:
                error_cases[casename] = {'bug_nums': 1, 'bugs': [entry]}
                #23
                #['bug_nums'] = 1
                #error_cases[casename]['bugs'].append(entry)
    print "================================================="
    print error_cases
    print "================================================="
    sorted_cases = sorted(error_cases, key=lambda x: error_cases[x]['bug_nums'])
    print "---------------------------------------------------------"
    print sorted_cases
    print "---------------------------------------------------------"
    i = 0; data = []
    for entry in sorted_cases:
        print "================================================="
        print entry
        print "================================================="
        data[i] = json2html.convert(json=entry)
        i += 1
    html_fh = open(os.path.join(resultdir,"OK1.html"),'w')
    all_str = '\n'.join(data)
    html_fh.write(all_str)
    html_fh.close()



def main(args):

    collect_topn('/home/jian/tr')


if __name__ == "__main__":
    main(sys.argv[1:])
