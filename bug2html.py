#!/usr/bin/env python
#
# Copyright (C) 2017 VMware, Inc.
# All Rights Reserved
#


class bug2html:
    def __init__(self):
        self.developer = 'lij'

    @classmethod
    def convert(self, json, order_list, bug_list_name='Bug List'):
        '''
        Convert json string to html format
        @type json: str
        @param json: bug information in JSON format
        @type order_list: list of str
        @param order_list: list of bug field such as reporter, priority
        @type bug_list_name: str
        @param bug_list_name: name of the key, whose value is all bugs
            related to this case
        @rtype: string
        @return: html table data
        '''

        bug_list = json.pop(bug_list_name)
        case_name = list(json.keys())[0]
        bug_num = json[case_name]

        header = '<center><b> %s : %d </b></center>\n' % (case_name, bug_num)
        html_data = '<center><table border="1" style="width:100%%">'
        copy_list = order_list[:]
        last_one = copy_list.pop()
        th_format = '<th style="width:7%%">%s</th>\n'
        bug_table_head = [th_format % field for field in copy_list]
        bug_table_head.append('<th>%s</th>\n' % last_one)
        title = '<tr>%s</tr>' % ''.join(bug_table_head)

        all_line = []
        for bug in bug_list:
            all_str = ['<td>%s</td>' % bug[field] for field in order_list]
            one_line = '<tr>%s</tr>' % '\n'.join(all_str)
            all_line.append(one_line)
        all_bug_str = '\n'.join(all_line)
        html_frame = '%s<center><table border="1" style="width:100%%">' \
            + '%s %s </table></center>'
        html_data = html_frame % (header, title, all_bug_str)
        return html_data
