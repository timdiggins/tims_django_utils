"""
 Command for backup database
 based on http://djangosnippets.org/snippets/823/
"""

import os
import subprocess
import time
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    args = "(archivefile)"
    option_list = BaseCommand.option_list + (
        make_option('--restore', action='store_true', dest='do_restore', default=False,
            help='restores rather than backing up.'),
    )

    help = "Backup database to archivefile (or datestamped in .dbackups). Only Mysql and Postgresql engines are implemented"

    def handle(self, *args, **options):
        if len(args):
            archivefile = args[0]
        else:
            archivefile = None
        from django.conf import settings
        restore = options.get('do_restore', False)
        self.engine = settings.DATABASES['default']['ENGINE']
        self.engine_name = self.engine.split('.')[-1]
        self.db = settings.DATABASES['default']['NAME']
        self.user = settings.DATABASES['default']['USER']
        self.passwd = settings.DATABASES['default']['PASSWORD']
        self.host = settings.DATABASES['default']['HOST']
        self.port = settings.DATABASES['default']['PORT']
        self.backup_dir = getattr(settings, 'DB_BACKUP_DIR', None) or os.path.join(settings.ROOT_DIR, '.dbbackups')
        
        if archivefile and not restore and archivefile.endswith(".gz"): 
            archivefile = archivefile[:-3]
            gzip=True
        else:
            gzip=False
            
        if not archivefile:
            if restore:
                archivefile = self.find_most_recent_backup()
            else:
                archivefile = 'backup_%s.sql' % time.strftime('%y%m%d%H%M%S')
                if not os.path.exists(self.backup_dir): os.makedirs(self.backup_dir)
                
        if not os.path.dirname(archivefile):
            archivefile = os.path.join(self.backup_dir, archivefile)
        
        if 'postgresql' in self.engine_name:
            restore_cmd = self.do_postgresql_restore
            backup_cmd = self.do_postgresql_backup
        elif 'mysql' in self.engine_name:
            restore_cmd = self.do_mysql_restore
            backup_cmd = self.do_mysql_backup
        else:
            print 'Backup in %s engine (%s) not implemented' % (self.engine_name, self.engine)
            
        if restore:
            self.gunzipped_wrapper(archivefile, restore_cmd)
        else:
            backup_cmd(archivefile)
            if gzip: 
                self.gzip(archivefile)

    def find_most_recent_backup(self):
        if not os.path.exists(self.backup_dir): 
            raise CommandError("Doesn't exist: %s" % self.backup_dir)
        # find most recent
        latest_mtime = 0
        for f in os.listdir(self.backup_dir):
            fp = os.path.join(self.backup_dir, f)
            if os.path.isfile(fp):
                mtime = os.path.getmtime(fp)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    archivefile = fp
        if not archivefile:
            raise CommandError("Didn't find backup in %s" % self.backup_dir)
        return archivefile
    
    def postgresql_args(self):
        args = []
        if self.user:
            args += ["--username=%s" % self.user]
        if self.passwd:
            print "Sorry - can't do postrgres non-interactively with a password (look it up)."
            args += ["--password"]
        if self.host:
            args += ["--host=%s" % self.host]
        if self.port:
            args += ["--port=%s" % self.port]
        if self.db:
            args += [self.db]
        return args
    
    def mysql_args(self):
        args = []
        if self.user:
            args += ["--user=%s" % self.user]
        if self.passwd:
            args += ["--password=%s" % self.passwd]
        if self.host:
            args += ["--host=%s" % self.host]
        if self.port:
            args += ["--port=%s" % self.port]
        if self.db:
            args += [self.db]
        return args

    def do_postgresql_backup(self, archivefile):
        print 'Doing Postgresql backup of database %s into %s' % (self.db, archivefile)
        cmd = ['pg_dump','-c'] +self.postgresql_args()
        print cmd
        with open(archivefile, 'wb') as stdout:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=stdout, close_fds=True)
            process.wait()

    def do_mysql_backup(self, archivefile):
        print 'Doing mysql backup of database %s into %s' % (self.db, archivefile)
        cmd = ['mysqldump','--add-drop-table'] +self.mysql_args()
        print cmd
        with open(archivefile, 'wb') as stdout:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=stdout, close_fds=True)
            process.wait()
            
            
    def gzip(self, archivefile):
        print "gzipping"
        gzipped = "%s.gz" % archivefile
        if os.path.exists(gzipped):
            os.unlink(gzipped)
        cmd = 'gzip "%s"' % archivefile
        process = subprocess.Popen(cmd, shell=True)
        process.wait()
        
    def gunzipped_wrapper(self, archivefile, restore_cmd):
        if archivefile.endswith(".gz"):
            tmpfile = os.path.join(os.path.dirname(archivefile),'tmp.gz')
            os.system("cp -p %s %s" % (archivefile, tmpfile))
            os.system("gunzip %s" % (tmpfile))
            archivefile = tmpfile[:-3]
            temporary = True
        else:
            temporary = False
        restore_cmd(archivefile)
        if temporary:
            os.unlink(archivefile)

    def do_postgresql_restore(self, archivefile):
        print 'Doing Postgresql restore to database %s from %s' % (self.db, archivefile)
        cmd = ['psql','-q','--file=%s' % archivefile] +self.postgresql_args()
        print cmd
        process = subprocess.Popen(cmd)
        process.wait()
            
    def do_mysql_restore(self, archivefile):
        print 'Doing mysql restore to database %s from %s' % (self.db, archivefile)
        cmd = ['mysql'] +self.mysql_args()
        print cmd
        with file(archivefile) as f:
            process = subprocess.Popen(cmd, stdin=f)
            process.wait()