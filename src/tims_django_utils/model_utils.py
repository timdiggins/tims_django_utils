'''

'''
from django.db import models

class UneditableForeignKey(models.ForeignKey):
    def save_form_data(self, instance, data):
        if instance.id and data is None:
            return
        super(models.ForeignKey, self).save_form_data(instance, data)

import south.modelsinspector #@UnresolvedImport
south.modelsinspector.add_introspection_rules([], ["^tims_django_utils\.model_utils\.UneditableForeignKey"])
