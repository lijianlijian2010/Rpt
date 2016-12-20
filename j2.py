#!/usr/bin/python

import os
import glob
path='/mts/home4/lij/w/yy/bug_report/reporttool_v6.0'

for filename in glob.glob(os.path.join(path, '*.pdf')):
    print filename
