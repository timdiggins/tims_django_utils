'''

'''
from tims_django_utils.test_utils import TestCase, unittest
from django.utils.datastructures import SortedDict
from tims_django_utils.model_serialization_utils import sorted_dict_to_string, string_to_sorted_dict, list_to_string,\
    string_to_list

class TestSerializationUtils(TestCase):
    def test01_can_serialize_and_deserialize_sortedict(self):
        def test_serialization_loop(sd1, msg):
            s = sorted_dict_to_string(sd1)
            sd2 = string_to_sorted_dict(s)
            self.assertEqual(sd1, sd2, msg)
            self.assertEqual(sd1.__class__, sd2.__class__, msg)
            for (k1,v1), (k2,v2) in zip(sd1.items(), sd2.items()):
                self.assertEqual(k1, k2, msg)
        sd = SortedDict()
        sd['sierra'] =  1
        sd['oscar'] =  2
        sd['romeo'] =  3
        sd['tango'] =  4
        test_serialization_loop(sd, 'four items')
        test_serialization_loop(SortedDict(), 'empty')

    def test02_can_serialize_and_deserialize_empty_sorteddicts_correctly(self):
        self.assertEqual('', sorted_dict_to_string(SortedDict()))
        self.assertEqual(SortedDict(), string_to_sorted_dict(''))
        
    def test03_can_serialize_and_deserialize_list(self):
        def test_serialization_loop(list1, msg):
            s = list_to_string(list1)
            list2 = string_to_list(s)
            self.assertEqual(list1, list2, msg)
            self.assertEqual(list1.__class__, list2.__class__, msg)
            for v1,v2 in zip(list1, list2):
                self.assertEqual(v1, v2, msg)
        l = ['sierra', 'oscar','romeo','tango']
        test_serialization_loop(l, 'four items')
        test_serialization_loop([], 'empty')

    def test04_can_serialize_and_deserialize_empty_lists_correctly(self):
        self.assertEqual('', list_to_string([]))
        self.assertEqual([], string_to_list(''))

if __name__=="__main__":
    unittest.main()  