from django.core.management.base import BaseCommand, CommandError
from tims_django_utils.management.commands import dbbackup
import os
import time
import subprocess

class Command(BaseCommand):
    help = "Will drop and recreate db (wipe out totally). please be sure this is what you want!"

    def handle(self, *args, **options):
        from django.conf import settings
        self.engine = settings.DATABASES['default']['ENGINE']
        self.engine_name = self.engine.split('.')[-1]
        self.db = settings.DATABASES['default']['NAME']
        self.user = settings.DATABASES['default']['USER']
        self.passwd = settings.DATABASES['default']['PASSWORD']
        self.host = settings.DATABASES['default']['HOST']
        self.port = settings.DATABASES['default']['PORT']
        
        if 'postgresql' not in self.engine_name:
            raise CommandError("Can only support postgres at present")
        
        self.drop_db()
        self.recreate_db()
        
    def drop_db(self):
        try:
            check_call("dropdb -e --username %s %s" % (self.user, self.db))
        except subprocess.CalledProcessError:
            print "dropdb unsuccessful but carrying on"
        
    def recreate_db(self):
        check_call("createdb -e -T template0 --username %s %s" % (self.user, self.db))
        
def check_call(cmd):
    print "$", cmd
    subprocess.check_call(cmd, shell=True)
        