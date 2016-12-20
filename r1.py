# -*- coding: utf-8 -*-
# ! /usr/bin/python
from __future__ import division
import requests
import xml.etree.ElementTree as ET
import json
import logging
import os
import os.path
import glob
import sys
import getpass
import optparse
import re
import time

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
    parser.add_option("-t", "--topn", dest="topn", action="store",
                      type="string", help="cases or features or bugs")

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


def collect_topn(resultdir):
    error_cases = {}
    files = '*10_7.json'
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
                pass
                #error_cases[casename] = 23
                #{'bug_nums': 1, 'bugs': [entry}
    print error_cases

def main(args):
    try:
        cmdOpts, _ = process_args(args)
        if not cmdOpts.logdir:
            cmdOpts.logdir = cmdOpts.resultdir
        setup_logging(cmdOpts.logdir)
        log.info("reporttool cmdOpts are %s" % cmdOpts)
        if cmdOpts.topn:
            if not cmdOpts.resultdir:
                log.error('Must provide "resultdir" to generate topN')
                raise Exception('resultdir is missing!')
            else:
                collect_topn(cmdOpts.resultdir)
                exit(0)

        if not cmdOpts.domain or not cmdOpts.project:
            log.error('domain or project is missing!')
            raise Exception('domain or project is missing!')
        if not cmdOpts.resultdir:
            log.error('resultdir is missing!')
            raise Exception('resultdir is missing!')
        if not cmdOpts.cycleid:
            log.error('At lease 1 cycleid!')
            raise Exception('cycleid is missing!')
        print "Jian: SUCCESS"

    except Exception as e:
        log.error(e)
        log.info("usage: python reporttool_v5.0.py [-l|--logdir] [-r|--resultdir] [-d|--domain] [-j|--project] [-c|--cycleid]")
        exit()

if __name__ == "__main__":
    main(sys.argv[1:])
