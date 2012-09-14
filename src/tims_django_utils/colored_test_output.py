"""Makes console output colored by success / failure.
"""
try:
    import unittest2 as unittest
except ImportError:
    try:
        from django.utils import unittest
    except ImportError:
        import unittest

if hasattr(unittest, 'runner'):
    from django.core.management.color import color_style, supports_color
    from django.utils.termcolors import make_style
    import new
    style = color_style()
    if supports_color():
        style.SUCCEEDING = make_style(fg='green')
        style.FAILING = make_style(fg='red')
        style.ERROR = make_style(opts=('bold',),fg='yellow', bg='black')
        style.FAILURE = make_style(opts=('bold',),fg='yellow', bg='black')
    
    def write(self, arg):
        if arg:
            if 'ERROR' in arg or arg=="E":
                self.stream.write(style.ERROR(arg))
                self.failed_before=True
            elif 'FAIL' in arg or arg=="F":
                self.stream.write(style.FAILURE(arg))
                self.failed_before=True
            elif self.failed_before:
                self.stream.write(style.FAILING(arg))            
            else:
                self.stream.write(style.SUCCEEDING(arg))
    unittest.runner._WritelnDecorator.write = new.instancemethod(
                write, 
                None, unittest.runner._WritelnDecorator) #@UndefinedVariable
    unittest.runner._WritelnDecorator.failed_before = False
