import unittest
import pyparsing
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

# import mymodule
# Assumes you named your module 'multiline.py'
from dsl_parser import parse
class PolicyDslParserTest(unittest.TestCase):

    def setUp(self):
        #TODO Add some filter and metric fakes in the redis
        print 'start unit_test'

    def test_one_simple_rule(self):
        results = []
        cases ="""\
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 OR get_ops_tenant == 1 AND get_ops_tenant == 5 OR get_ops_tenant == 6 DO SET compression WITH param1=2\
        """.splitlines()
        expected = [[['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', \
        ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2'}]]]
        for case in cases:
            results.append(parse(case).asList())
        i = 0
        for result in results:
            self.assertEqual(result, expected[i])
            i+=1


    def test_multiple_rules(self):
        """
        Three rules, the first one with one param, the second without params, and the third with two params.
        """
        results = []

        cases ="""\
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 OR get_ops_tenant == 1 AND get_ops_tenant == 5 OR get_ops_tenant == 6 DO SET compression WITH param1=2
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 OR get_ops_tenant == 1 AND get_ops_tenant == 5 OR get_ops_tenant == 6 DO SET compression
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 OR get_ops_tenant == 1 AND get_ops_tenant == 5 OR get_ops_tenant == 6 DO SET compression WITH param1=2, param2=0\
        """.splitlines()

        expected = [
        [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2'}]],
        [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression']],
        [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2', 'param2': '0'}]]
        ]

        for case in cases:
            results.append(parse(case).asList())
        i = 0
        for result in results:
            self.assertEqual(result, expected[i])
            i+=1

    def test_rule_metric_error(self):

        results = []

        cases ="""\
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN metric_not_exists < 3 DO SET compression WITH param1=2\
        """.splitlines()

        # expected = [
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2'}]],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression']],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2', 'param2': '0'}]]
        # ]
        # result = parse(cases)
        self.assertRaises(
            AttributeError,
            parse,
            cases
        )

    def test_rule_param_error(self):

        results = []

        cases ="""\
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 DO SET compression WITH param_no_exists=2\
        """.splitlines()

        # expected = [
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2'}]],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression']],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2', 'param2': '0'}]]
        # ]
        # result = parse(cases)
        self.assertRaises(
            AttributeError,
            parse,
            cases
        )

    def test_rule_action_error(self):

        results = []

        cases ="""\
        FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN get_ops_tenant < 3 DO SET action_not_exists WITH param1=2\
        """.splitlines()

        # expected = [
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2'}]],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression']],
        # [['4f0279da74ef4584a29dc72c835fe2c9'], [['get_ops_tenant', '<', '3'], 'OR', [['get_ops_tenant', '==', '1'], 'AND', ['get_ops_tenant', '==', '5']], 'OR', ['get_ops_tenant', '==', '6']], ['SET', 'compression', {'param1': '2', 'param2': '0'}]]
        # ]
        # result = parse(cases)
        self.assertRaises(
            AttributeError,
            parse,
            cases
        )


if __name__ == '__main__':
    unittest.main()
