python reporttool_v6.0.py -r /home/jian/tr/ -d VSPHERE -j ESX -c 62579
python rpt.py -r /home/jian/tr/  -d VSPHERE -j ESX -c 71548
python rpt.py -r /home/jian/tr -d VSPHERE -j ESX -c 71548 -n vSphere2017_HPTC_iteration3
python topn.py -r /home/jian/tr -t LPTC_Iteration
python rpt.py -r ~/public_html/report -d VSPHERE -j ESX -c 63066 -n vSphere2017_HPTC_iteration3
python topn.py -r ~/public_html/report -t vSphere2017_HPTC_iteration3 
python /home/jian/health/vdnet/automation/main/../scripts/hpqc/hpqctool.py --testsetid 81692 --vdnetdir /tmp/vdnet/20170112-214159 --logdir /tmp/vdnet/20170112-214159  --domain VSPHERE --project ESX
