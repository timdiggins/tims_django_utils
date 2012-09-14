'''
some helpful serialization routines
'''
import json
from django.utils.datastructures import SortedDict

def sorted_dict_to_string(sdict):
    if not sdict: return ''
    return json.dumps(sdict.items())

def string_to_sorted_dict(s):
    if not s: return SortedDict()
    return SortedDict(json.loads(s))

def list_to_string(l):
    if not l: return ''
    return json.dumps(l)

def string_to_list(s):
    if not s: return []
    return json.loads(s)
