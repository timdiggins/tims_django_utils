"""
Provides utilities for testing within a django project
"""
import time
from lxml.html import FormElement
from django.utils.datastructures import SortedDict
import traceback
try:
    from django.utils import unittest
except ImportError:
    try:
        import unittest2 as unittest
    except ImportError:
        import unittest


import webbrowser
import os
import sys
import signal
import re
import types
import lxml.html
import lxml.etree

# from lxml.html import html5parser
#from lxml.html import soupparser
from lxml.cssselect import CSSSelector

#try: 
#    from BeautifulSoup import BeautifulSoup
#except ImportError:
#    BeautifulSoup = None

import django.test
from django.test.client import Client, MULTIPART_CONTENT
from django.conf import settings
from django.core import management
from django.test.simple import DjangoTestSuiteRunner

from . import colored_test_output #@UnusedImport
           
class DjangoTestRunner(unittest.TextTestRunner):

    def __init__(self, verbosity=0, failfast=False, **kwargs):
        super(DjangoTestRunner, self).__init__(verbosity=verbosity, **kwargs)
        self.failfast = failfast
        self.buffer = True
        self._keyboard_interrupt_intercepted = False

    def run(self, *args, **kwargs):
        """
        Runs the test suite after registering a custom signal handler
        that triggers a graceful exit when Ctrl-C is pressed.
        """
        self._default_keyboard_interrupt_handler = signal.signal(signal.SIGINT,
            self._keyboard_interrupt_handler)
        try:
            result = super(DjangoTestRunner, self).run(*args, **kwargs)
        finally:
            signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)
        return result

    def _keyboard_interrupt_handler(self, signal_number, stack_frame):
        """
        Handles Ctrl-C by setting a flag that will stop the test run when
        the currently running test completes.
        """
        self._keyboard_interrupt_intercepted = True
        sys.stderr.write(" <Test run halted by Ctrl-C> ")
        # Set the interrupt handler back to the default handler, so that
        # another Ctrl-C press will trigger immediate exit.
        signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)

    def _makeResult(self):
        result = super(DjangoTestRunner, self)._makeResult()
        failfast = self.failfast

        def stoptest_override(func):
            def stoptest(test):
                # If we were set to failfast and the unit test failed,
                # or if the user has typed Ctrl-C, report and quit
                if (failfast and not result.wasSuccessful()) or \
                    self._keyboard_interrupt_intercepted:
                    result.stop()
                try:
                    func(test)
                except Exception, e:
                    sys.stderr.write('\n%s:\n' % test)
                    sys.stderr.write('  Error occured during result.stopTest: %s\n' %str(e))
            return stoptest

        setattr(result, 'stopTest', stoptest_override(result.stopTest))
        return result

class BufferredDjangoTestSuiteRunner(DjangoTestSuiteRunner):
    """a version of DjangoTestSuiteRunner buffering output and only dumping it if there is an error
    """    
    def run_suite(self, suite, **kwargs):
        runner = DjangoTestRunner(verbosity=self.verbosity, failfast=self.failfast)
        try:
            return runner.run(suite)
        except UnicodeDecodeError, e:
            sys.stderr.write('\nError during run_suite: ')    
            sys.stderr.write(str(e)+'\n')
            class FakeResult(object):
                errors = range(10)
                failures = range(10)
            return FakeResult()


class TestCase(unittest.TestCase):
    longMessage = True
        
    def assertEquals(self, first, second, message=None):
        if not isinstance(first, basestring) or not isinstance(second, basestring) or len(first)<15:
            super(TestCase, self).assertEquals(first, second, message)
            return
        if first == second:
            return
        for index, (c1, c2) in enumerate(map(None, first, second)):
            if c1==c2: continue
            message = message or ""
            message += "first non-match at %s\n" % index
            message += "equal: %s\n" % first[:index]
            message += "not equal:\n"
            message += "\tfirst     : %s\n" % first[index:index+20]
            message += "\tsecond    : %s\n" % second[index:index+20]
            # print message
            super(TestCase, self).assertEquals(first, second, message)
            return
    #nice PEP08 versions
    assert_equal = assertEqual = assertEquals

    def assertHtmlEquals(self, first, second, message=None):
        first = lxml.etree.tostring(lxml.etree.fromstring(first), pretty_print=True) #@UndefinedVariable
        second = lxml.etree.tostring(lxml.etree.fromstring(second), pretty_print=True) #@UndefinedVariable
        if first == second: return
        first_file = save_html_to_file(first, "comparison-first")
        second_file = save_html_to_file(second, 'comparison-second')
        if hasattr(settings, 'DIFF_CLIENT'):
            os.system("%s %s %s" % (settings.DIFF_CLIENT, first_file, second_file))
        self.assertEquals(first, second, message)
    assertHtmlEqual = assertHtmlEquals
    assert_html_equal = assertHtmlEquals
    
    def viewHtmlInEditor(self, html, file_name="saved_html"):
        if not settings.HTML_EDITOR: return
        html_file = save_html_to_file(html, file_name)
        os.system("%s %s" % (settings.HTML_EDITOR, html_file))

def save_html_to_file(html, file_name):
    file_path = os.path.join(settings.TMP_DIR, '%s.html' % file_name)
    with open(file_path, 'w') as f: f.write(html)
    return file_path

class DjangoTestCase(django.test.TestCase, TestCase):
    longMessage = True

RegexObject = type(re.compile('something'))

class SelectAssertionTestCase(TestCase):
    """a version of TestCase that allows for useful viewing of content, and selection by tag.
    must ensure a last_response with a content
    """ 
    LXML_HTML_PARSER = "lxml.html"
    # HTML5LIB_PARSER = "html5lib"
#    SOUP_PARSER = "soup"
    parser = LXML_HTML_PARSER #default
    def setUp(self):
        super(SelectAssertionTestCase, self).setUp()
        self.last_response = None
    
    def get_select(self, tag):
        self.ensure_parsed_html()
        sel = CSSSelector(tag)
        return list(sel(self.last_response._parsed_html))
        
    def assert_select(self, tag, count=None, skip_assertions=False, text=None, message=None):
        f = self.get_select(tag)
        if not skip_assertions:
            if message is None: 
                message = ""
            else:
                message = "%s\n" % message
            if count is None:
                self.assertTrue(len(f), "%sExpecting at least one '%s'" %  (message,tag))
            else:
                self.assertEqual(len(f), count, "%sLooking for '%s'" % (message,tag))
            if text is not None:
                if isinstance(text, basestring):
                    found_count = len([e for e in f if e.text == text])
                elif isinstance(text, RegexObject):
                    found_count = len([e for e in f if text.search(e.text)])
                else:
                    raise ValueError("assert_select, text must be string or regexp")
                message = "%sExpecting %%s '%s' with text '%s'" %  (message,tag, text)
                if count is None:
                    self.assertTrue(found_count, message % "at least one")
                else:
                    self.assert_equal(count, found_count, message % count)
        return f
        
    def ensure_parsed_html(self):
        assert self.last_response is not None, "no last response???"
        if getattr(self.last_response, '_parsed_html', None) is not None: return
        self.last_response._parsed_html = self.parse_html(self.last_response.content)
    
    def parse_html(self, content):
        if self.parser == self.LXML_HTML_PARSER:
            return lxml.html.document_fromstring(content)
#        if self.parser == self.SOUP_PARSER:
#            return soupparser.fromstring(content)
        # if self.parser == self.HTML5LIB_PARSER:
        #     return html5parser.fromstring(content)
        raise Exception("don't recognize parser: %s"%self.parser)

    def assert_should_have_link(self, href, should_have_link=True, msg=''):
        last_response_should_have_link = href in [a.get('href') for a in self.assert_select('a[href]')]
        if bool(last_response_should_have_link) != bool(should_have_link):
            msg = "%s%s%s link to %s" % (
                msg, 
                msg and " - " or "", 
                should_have_link and "expecting" or "not expecting", 
                href)
            self.fail(msg)

    assert_has_link = assert_should_have_link
    
_FILE_ROOT_FOR_VIEWING = None

def _get_static_url_root():
    if hasattr(settings, "SITE_MEDIA_ROOT"):
        return "site_media"
    else:
        return "static"
    
def _file_root_for_viewing():
    global _FILE_ROOT_FOR_VIEWING
    if not _FILE_ROOT_FOR_VIEWING:
        _FILE_ROOT_FOR_VIEWING = _calculate_file_root_for_viewing()
    return _FILE_ROOT_FOR_VIEWING
        


def _calculate_file_root_for_viewing():
    if hasattr(settings, "SITE_MEDIA_ROOT"):
        return settings.SITE_MEDIA_ROOT
    # no, using tempoary path with static:
    
    view_dir = os.path.join(settings.ROOT_DIR, 'tmp', 'view_dir')
    if not os.path.exists(view_dir): os.makedirs(view_dir)
    _ensure_static_files_recent()
    return ensure_static_link(view_dir)

def ensure_static_link(view_dir):
    static_link = os.path.join(view_dir, _get_static_url_root())
    if not os.path.exists(static_link):
        static_files_dir = os.path.join(settings.ROOT_DIR, 'static')
        if not os.path.exists(static_files_dir):
            raise Exception("expecting static files to be in %s, but doesn't exist" % static_files_dir)
        os.symlink(static_files_dir, static_link)
    return static_link

def _static_files_dir():
    return os.path.join(settings.ROOT_DIR, 'static')

def _ensure_static_files_recent():
    static_files_dir = _static_files_dir() 
    if not os.path.exists(static_files_dir):
        _collectstatic('for first time')
        return
    if os.path.getmtime(static_files_dir) + 24*60*60 < time.time():
        collected = _collectstatic('because not done for at least 24 hours')
        if not collected:
            sys.stderr.write("Static looks old - refresh it or touch it? %s" % static_files_dir)

def _collectstatic(reason):
    if 'collectstatic' in management.get_commands():
        sys.stderr.write("Doing collectstatic, %s" % reason)
        try:
            management.call_command('collectstatic', interactive=False)
        except SystemExit:
            pass
        os.system('touch "%s"' % _static_files_dir())
        return True
    
class EmailTestCase(DjangoTestCase):
    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        # remove django-mailer to properly test for outbound e-mail
        if "mailer" in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS.remove("mailer")
    
    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps

class PageTestCase(DjangoTestCase, SelectAssertionTestCase):
    """a version of TestCase that allows for useful viewing of content, and selection by tag
    """    

    verbose = False
    RELATIVIZING_RE = re.compile(r"""(src|href)=(['"])/%s/""" % _get_static_url_root())
    __viewed = []
    __viewed_errors = []

    def setUp(self):
        super(PageTestCase, self).setUp()
        self.client = Client()
        self.last_response = None
        
    def preprocess_path(self, path):
        if path[0]!="/": path = "/"+path
        if self.verbose:
            print "GET", path
        return path
    
    def check_last_response(self, follow, expected_status, msg=None):
        if isinstance(expected_status, basestring):
            raise Exception('expected_status must be an int or tuple of ints')
        if isinstance(expected_status, types.IntType):
            expected_status = expected_status,
        if self.last_response.status_code not in expected_status:
            if 200 in expected_status and self.last_response.status_code in [302,303]:
                self.fail("%sunexpected redirect[%s] to %s, one of %s" % (
                    msg and "%s\n" % msg or '',
                    self.last_response.status_code, self.last_response["Location"], expected_status))
            else:
                self.fail("%sunexpected response code %s, expecting one of %s" % (
                    msg and "%s\n" % msg or '',
                    self.last_response.status_code, expected_status))
                self.assertIn(self.last_response.status_code, expected_status, '%sResponse.status_code' % (msg and "%s\n" % msg or '',))
        
    def get(self, path, data={}, follow=False, expected_status=(200,), msg=None, **kwargs):
        path = self.preprocess_path(path)
        self.last_response = self.client.get(path, data, follow, **kwargs)
        self.check_last_response(follow, expected_status, msg="%sget '%s'" % (msg and "%s\n" % msg or '', path))
        return self.last_response

    def post(self, path, data={}, content_type=MULTIPART_CONTENT, follow=False, expected_status=None, msg=None, **kwargs):
        if expected_status is None:
            if follow:
                expected_status = (200,)
            else:
                expected_status = (302,) # because posts should always redirect IMHO
        path = self.preprocess_path(path)
        self.last_response = self.client.post(path, data, content_type=content_type, follow=follow, **kwargs)
        self.check_last_response(follow, expected_status, msg=msg)
        return self.last_response
        
    def view(self, indicator='test-view', as_error=False):
        if not settings.VIEW_TEST_ERRORS_IN_BROWSER:
            print "not showing test error"
            return
        if not hasattr(self, "last_response"):
            return
        if not self.last_response: 
            if as_error: return
            raise Exception("no response got yet!")
        if as_error:
            indicator = "error%s" % (len(self.__viewed_errors)+1,)
            self.__viewed_errors.append(indicator)
        elif indicator in self.__viewed:
            print "Not viewing in browser -- already viewed"
            return
        if not len(self.last_response.content.strip()): return
        self.__viewed.append(self.__viewed)
        html = self.RELATIVIZING_RE.sub(r"""\1=\2""", self.last_response.content)
        view_file = os.path.join(_file_root_for_viewing(), '.tmp.%s.html' % indicator)
        if self.verbose:
            print "WRITING", view_file
        with open(view_file, 'w') as f:
            f.write(html)
        furl = "file://%s" % os.path.abspath(view_file)
        webbrowser.open(furl)            
            
    def failureException(self, *args, **kwargs):
        self.view(as_error=True)
        return AssertionError(*args, **kwargs)
    
    def form(self, selector="form"):
        return SubmittableForm(self, self.assert_select(selector, count=1)[0])

    def assert_response_at(self, path, path_at=True):
        request_path = self.last_response.request['PATH_INFO']
        self.assert_equal(path_at, request_path==path, "%s last response at %s, but was at %s" %(path_at and "Expecting" or "Not expecting", path, request_path))

    def assert_response_contains(self, text, contains=True):
        self.assertEqual(contains, text in self.last_response.content, '%s to find "%s"'% (contains and 'Expecting' or 'Not expecting', text))

    @property 
    def last_content_as_utf8(self):
        return self.last_response.content.decode('utf-8')
    
    
class SubmittableForm(object):
    input_sel = CSSSelector('input')
    def __init__(self, page_test_case, form_element):
        self.page_test_case = page_test_case
        self.form_element = form_element
        self.submitted = False
        self.field_values = dict()
        for input in self.input_sel(self.form_element):
            if input.type=="submit":
                continue
            if input.name and input.value:
                    self.field_values[input.name] = input.value
        self.action = form_element.get('action') or self.page_test_case.last_response.request['PATH_INFO']
        self.method = form_element.get('method')

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print exc_type, type(exc_type)
            return False
        if not self.submitted:
            self.submit()
        return False #allow exception to propagate. doing this explicitly, though unnecessarily
    
    def fill_in(self, name=None, value=None, **kwargs):
        def usage(msg=""):
            msg = "You need to supply EITHER name and value OR kwargs to fill_in" 
            raise Exception(msg)
        if name is None and value is None and not kwargs:
            usage()
        if (name is None and value) or (name and value is None):
            usage()
        if (name is not None and value is not None and kwargs):
            usage()
        if name is not None and value is not None:
            self._fill_in_one(name, value)
        else:
            for name, value in kwargs.iteritems():
                self._fill_in_one(name, value)
                
    def _fill_in_one(self,name, value):
        f = self.page_test_case.get_select('input[name=%s]'% name)
        if not f:
            f=self.page_test_case.get_select('textarea[name=%s]'% name)
        if not f:
            f=self.page_test_case.get_select('select[name=%s]'% name)
        if not f:
            f=self.page_test_case.get_select('radio[name=%s]'% name)
        if not f:
            self.page_test_case.fail("Expecting input/select/radio with name=%s" % name)
        self.field_values[name] = value

    _dbid_to_formname = None
    
    def dbid_to_formname(self, dbid, fieldname=None):
        self._ensure_formset_dbid_to_formname()
        try:
            name = self._dbid_to_formname[u"%s" % dbid]
        except KeyError:
            self.page_test_case.fail("Don't have dbid %s in formset - have: %s" % (dbid, ", ".join(self._dbid_to_formname.keys())))
        if fieldname is None:
            return name
        return "%s-%s" % (name, fieldname)
    
    def _ensure_formset_dbid_to_formname(self):
        if self._dbid_to_formname is not None:
            return 
        self._dbid_to_formname = SortedDict()
        for i in self.page_test_case.get_select('input[type=hidden]'):
            m = re.match("(form-[0-9]+)", i.name)
            if m:
                formset = m.group(1)
                id = i.value
                self._dbid_to_formname[id] = formset
    
    def submit(self, selector=None):
        self.submitted = True
        if self.method.lower() == "post":
            self.page_test_case.post(self.action, self.field_values, follow=True)
            return
        raise Exception("can't handle %s method at present" % self.method)
        
def refetch(model_instance):
    return model_instance.__class__.objects.get(pk=model_instance.id)
    
