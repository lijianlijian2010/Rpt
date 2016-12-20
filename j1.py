#!/usr/bin/python

import json
from pprint import pprint

with open('data.json') as data_file:    
        data = json.load(data_file)
        pprint(data)

print data['maps'][0]['id']
print data['masks']['id']
