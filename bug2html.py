import json

class bug2html:
    def __init__(self):
        self.developer = 'lij'

    @classmethod
    def convert(self, json, order_list, bug_list_name='Bug List'):
        bug_list = json.pop(bug_list_name)
        case_name = json.keys()[0]
        bug_num = json[case_name]

        case_data = '<center><b> %s : %d </b></center>\n' % (case_name, bug_num)
        html_data = '<center><table border="1" style="width:100%%">'
        copy_list = order_list[:]
        last_one = copy_list.pop()
        bug_table_head = [ '<th style="width:7%%">%s</th>\n' % field for field in copy_list ]
        bug_table_head.append('<th>%s</th>\n' % last_one)
        title = '<tr>%s</tr>' % ''.join(bug_table_head)

        all_line = []
        for bug in bug_list:
            all_str = [ '<td>%s</td>' % bug[field] for field in order_list ]
            #print all_str
            one_line = '<tr>%s</tr>' % '\n'.join(all_str)
            all_line.append(one_line)
        all_bug_str = '\n'.join(all_line)
        #print all_bug_str
        html_data = '%s<center><table border="1" style="width:100%%">%s %s </table></center>' % (case_data, title, all_bug_str)
        return html_data
        
