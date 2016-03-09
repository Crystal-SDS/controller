from pyparsing import *

"""
This calss define the parser functions needed to read the metrics results. Each
metric can need different parsers, so here we can define all the parsers.
"""

#change to class
class SwiftMetricsParse():
    def __init__(self):
        word = Word(alphas,alphanums+'_'+"-")
        number = Regex(r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?")

        container =Combine(Word(alphanums) + Literal("/") + Word(alphanums+"_-"))
        obj = Combine(Word(alphanums)+Literal("/")+ Word(alphanums+"_-")+Literal("/")+ Word(alphanums+"_-."))
        tenant = Combine(Word(alphanums))

        target = (tenant ^ container ^ obj)

        PUTVAL = Suppress(Literal("PUTVAL"))
        name = word + Suppress("/") + word + Suppress("*") + target("target") + Suppress("*") + word("operation") + Suppress("/")+ word("type")
        interval = Suppress(Literal("interval")) + Suppress("=") + number("interval")
        metric_value = number("timestamp") + Suppress(":") + number("value")

        self.rule_parse = PUTVAL + name + interval + metric_value

    def parse(self, input_string):
        """
        Structure
        PUTVAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9/container*get_ops_tenant/counter
        interval=5.000 1448970311.983:510
        """

        # Grammar definition
        return self.rule_parse.parseString(input_string)



# pepito = "PUTVAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_ops_tenant/counter interval=5.000 1448970311.983:510"
# pepito2 = "FPRswift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_ops_tenant/counter"
# # p = parse(pepito)
# rule_parsed = parse(pepito)
# print rule_parsed.asList()
# print "tenant_id", rule_parsed.tenant_id
# print "timestamp", rule_parsed.timestamp
# print "value", rule_parsed.value
