1. Function: Show the bug lists and the test results from HPQC for the specific testsets as a PDF file
(sample result: see Report-2016.08.24.pdf and Report-2016.08.24(1).pdf)

2. Third party Lib needed: requests, reportlab, pfbfer

3. Usage: python reporttool_v5.0.py [-l|--logdir] [-r|--resultdir] [-d|--domain] [-j|--project] [-c|--cycleid]
-l --logdir		:Storage path of file log
-r --resultdir	:Storage path of report
-d --domain	:Domain to search eg:VSPHERE
-j --project	:Project to search eg:ESX
--cycleid1		:testset_id

    e.g.1 python reporttool_v6.0.py -l /home/yileiz/test/ -r /home/yileiz/test/ -d VSPHERE -j ESX --c 67288-67290,67299-67317
    e.g.2 python reporttool_v6.0.py -l /home/yileiz/test/ -r /home/yileiz/test/ -d  SOLUTIONS  -j CINS  --c 12002-12004,11357,11408  

During the execution of the script, the user will be prompted to enter a username and password.

notice: logdir is optional.
            1. If not input logdir, then logdir == resultdir
            2. The cycleid  format is 67288-67290 or single cycleid 67299 splited by ','

4. Launcher which ca run this scripts: 10.116.252.137
The scripts path is /home/yileiz/test


------------------
Fix bugs:
2. Error of path
3. HTML tag error

Improvement
1. PDF naming schema
4. Start faster
5. TopN feature
