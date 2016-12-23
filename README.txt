1. Function: Show the bug lists and the test results from HPQC for the specific testsets as a PDF file
(sample result: see Report-2016.08.24.pdf and Report-2016.08.24(1).pdf)

2. Third party Lib needed: requests, reportlab, pfbfer

3. Usage: python reporttool_v5.0.py [-l|--logdir] [-r|--resultdir] [-d|--domain] [-j|--project] [-c|--cycleid] [-n|--cyclename]
-l --logdir		:Storage path of file log
-r --resultdir	:Storage path of report
-d --domain	:Domain to search eg:VSPHERE
-j --project	:Project to search eg:ESX
-c --cycleid    :Testset_id
-n --cyclename  :Identity to be a part of name of generated report PDF and JSON file

    e.g.1 python reporttool_v6.0.py -l /home/yileiz/test/ -r /home/yileiz/test/ -d VSPHERE -j ESX --c 67288-67290,67299-67317
    e.g.2 python reporttool_v6.0.py -l /home/yileiz/test/ -r /home/yileiz/test/ -d  SOLUTIONS  -j CINS  --c 12002-12004,11357,11408  

During the execution of the script, the user will be prompted to enter a username and password.

notice: logdir is optional.
            1. If not input logdir, then logdir == resultdir
            2. The cycleid  format is 67288-67290 or single cycleid 67299 splited by ','

4. Launcher which ca run this scripts: 10.116.252.137
The scripts path is /home/yileiz/test

---------------------------
Execution

python reporttool_v6.0.py -r /home/jian/tr/ -d VSPHERE -j ESX -c 62579
python rpt.py -r /home/jian/tr/  -d VSPHERE -j ESX -c 71548
python rpt.py -r /home/jian/tr -d VSPHERE -j ESX -c 71548 -n vSphere2017_HPTC_iteration3
python topn.py -r /home/jian/tr -t LPTC_Iteration

---------------------------
INSTALLATION NOTES

1. wget https://bootstrap.pypa.io/get-pip.py
2. python get-pip.py
3. pip install requests
4. apt-get install build-essential autoconf libtool pkg-config python-opengl python-imaging python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev
5. easy_install reportlab


------------------
Fix bugs:
2. Error of path
3. HTML tag error

Improvement
1. PDF naming schema
4. Start faster
5. TopN feature
