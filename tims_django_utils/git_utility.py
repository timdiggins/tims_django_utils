import subprocess
import traceback
from datetime import datetime
from django.conf import settings
import os
import json

GIT_TAG_FILENAME = '.git_info.json'

def _get_git_info(tag_name=None):
    """If tag_name is not given, it will get the HEAD state"""
    def git(git_cmd, extractor=None, default='unknown'):
        cmd = 'git %s' % git_cmd
        try:
            proc = subprocess.Popen(cmd,
             shell=True, cwd=settings.ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE
             )
            output = proc.communicate()[0]
            if extractor is None: return output
            return extractor(output)
        except:
            traceback.print_exc()
            return default
    git_description = dict()
    timestamp_cmd = 'log --pretty=format:"%ad" -1 --date=raw'
    describe_cmd = 'describe --always'
    if tag_name:
        timestamp_cmd += " " + tag_name
        describe_cmd += " " + tag_name
    git_description['TIMESTAMP'] = git(timestamp_cmd, lambda x: int(x.split(' ')[0]), default=0)
    git_description['DESCRIBE'] = git(describe_cmd, default="unknown")
    return git_description

def _null_git_info(describe="unknown"):
    return {'TIMESTAMP': 0, 'DESCRIBE': describe}

def _get_git_info_from_file():
    try:
        with open(git_tag_f) as f:
            return json.loads(f.read())
    except Exception, e:
        print "problem trying to decode %s" % git_tag_f
        print e

def write_out_git_info(tag_name, path=settings.ROOT_DIR, filename=GIT_TAG_FILENAME):
    with open(os.path.join(path, GIT_TAG_FILENAME), 'w') as f:
        f.write(json.dumps(_get_git_info(tag_name)))

GIT = None

git_tag_f = os.path.join(settings.ROOT_DIR, GIT_TAG_FILENAME)
if os.path.exists(git_tag_f):
    GIT = _get_git_info_from_file()
if not GIT:
    GIT = _get_git_info()

# add DATETIME (it doesn't serialize easily)
GIT['DATETIME'] = datetime.fromtimestamp(GIT['TIMESTAMP'])
