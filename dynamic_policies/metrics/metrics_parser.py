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

        tenant = Combine(Word(alphanums))
        container =Combine(Word(alphanums) + Literal(".") + Word(alphanums+"_-"))
        obj = Combine(Word(alphanums)+Literal(".")+ Word(alphanums+"_-")+Literal(".")+ Word(alphanums+"_-."))


        target = (tenant ^ container ^ obj)
        #This function change all the dots to slash found in the target field.
        #TODO: If the swift object accepts dots, this function shouldn't be executed.
        target.setParseAction(lambda t:  t[0].replace(".", "/") )

        PUTVAL = Suppress(Literal("PUTVAL"))
        name = word + Suppress("/") + word + Suppress("*") + target("target") + Suppress("*") + word("operation") + Suppress("/")+ word("type")
        interval = Suppress(Literal("interval")) + Suppress("=") + number("interval")
        metric_value = number("timestamp") + Suppress(":") + number("value")

        #Functions post-parsed
        replace_dots = lambda tokens : tokens
        # remove_repeted_elements = lambda tokens : [list(set(tokens[0]))]

        self.rule_parse = PUTVAL + name + interval + metric_value

    def parse(self, input_string):
        """
        Structure
        PUTVAL swift_mdw/groupingtail-tm*4f0279da74ef4584a29dc72c835fe2c9*get_sent/bytes interval=5.000 1457720927.886:1010
        interval=5.000 1448970311.983:510
        """
        
        # Grammar definition
        return self.rule_parse.parseString(input_string)



# pepito = "PUTVAL swift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9.c1.o1*get_ops_tenant/counter interval=5.000 1448970311.983:510"
# pepito2 = "FPRswift_mdw/groupingtail-swift_metrics*4f0279da74ef4584a29dc72c835fe2c9*get_ops_tenant/counter"
# # p = parse(pepito)
# p = SwiftMetricsParse()
# rule_parsed = p.parse(pepito)
# print rule_parsed.asList()
# print "tenant_id", rule_parsed.tenant_id
# print "timestamp", rule_parsed.timestamp
# print "value", rule_parsed.value
