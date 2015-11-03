from pyparsing import *
import metric
# By default, PyParsing treats \n as whitespace and ignores it
# In our grammer, \n is significant, so tell PyParsing not to ignore it
# ParserElement.setDefaultWhitespaceChars(" \t")
"""
rule ::= "FOR Tenant WHEN"+property +"[< > = <= >=]+X+"DO"+action

condition ::= property +"[< > = <= >=]+X
condition_list ::= condition
                    | condition_list AND condition
                    | condition_list OR condition
FOR Tenant WHEN"+ condition_list +"DO"+action

FOR Tenant WHEN"+ condition AND condition AND condition OR condition etc.+"DO"+action

TODO: Parse = TRUE or = False or condicion number. Check to convert to float or convert to boolean.
"""

def parse(input_string):
# tenant_list = Forward()
    action = oneOf("SET DELETE")
    param = Word(alphanums)+ Suppress(Literal("=")) + Word(alphanums)
    services = "slowdown througput"
    services_options = oneOf(services)
    operand =  oneOf("< > == != <= >=")
    number = Regex(r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?")
    word = Word(alphas)
    action = word
    sfilter = Word(alphanums)
    when = Suppress(Literal("WHEN"))
    with_params = Suppress(Literal("WITH"))
    do = Suppress(Literal("DO"))
    for_tenant = Suppress(Literal("FOR"))
    tenant_id = Word(alphanums)
    condition = Group(services_options("services_options") + operand("operand") + number("limit_value"))
    boolean_condition = oneOf("AND OR")
    tenant_list = tenant_id + ZeroOrMore(Suppress("AND")+tenant_id)
    params_list = delimitedList(param)
    # tenant_list << (tenant_id ^ (tenant_id + "AND" + OneOrMore(tenant_list)))
    # condition_list << ( condition ^ ( condition + boolean_condition + OneOrMore(condition_list)) )
    condition_list = operatorPrecedence(condition,[
                                ("AND", 2, opAssoc.LEFT, ),
                                ("OR", 2, opAssoc.LEFT, ),
                                ])
    # joinTokens = lambda tokens : "".join(tokens)
    # stripCommas = lambda tokens : tokens[0].replace("=", ",")
    convertToDict = lambda tokens : dict(zip(*[iter(tokens)]*2))
    # param.setParseAction(joinTokens)
    # param.setParseAction(stripCommas)
    params_list.setParseAction(convertToDict)
    # map(None, *[iter(l)]*2)
    rule_parse = for_tenant + Group(tenant_list)("tenants") + when +\
                condition_list("condition_list") + do + Group(action("action") + \
                sfilter("filter") + Optional(with_params + params_list("params")))("action_list")

    return rule_parse.parseString(input_string)

# alphaword = Word(alphas)
# integer = Word(nums)
# sexp = Forward()
# LPAREN = Suppress("(")
# RPAREN = Suppress(")")
# sexp << ( alphaword | integer | ( LPAREN + ZeroOrMore(sexp) + RPAREN ) )
#
# services = "slowdown througput"
# services_options = oneOf(services)
# operand =  oneOf("< > == <= >=")
# and_operand = Keyword("AND")
# limit_value = Word(nums)
# pk = Forward()
# condition = services_options("services_options") + operand("operand") + limit_value("limit_value")
# pk << ( condition ^ ( condition + and_operand + OneOrMore(pk)) )
#
# tests = """\
#     slowdown > 3 AND slowdown > 5""".splitlines()
#
# for t in tests:
#     print t
#     print pk.parseString(t)
#     print
#
# w = Word(alphas)
# e = Forward()
# e << (w ^ (w + e))
# print e.parseString('das fas dos')


# Return Rule object ?? or return parseString and create rule in other side
    # return rule_parse.parseString(input_string)
#
# rules = """\
#     FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET 1 WITH param1=2
#     FOR 2312 WHEN slowdown > 3 OR slowdown > 3 AND slowdown == 5 OR slowdown <= 6 DO SET storlet WITH param1=2, param2=3
#     FOR 2312 WHEN slowdown > 3 AND slowdown > 50 DO SET storlet""".splitlines()

# for rule in rules:
#     try:
#         stats = rule_parse.parseString(rule)
#     except:
#         print 'This rule ***'+rule+'  *** could not be parsed'
#     else:
#         print stats.asList()

# for rule in rules:
#
#     stats = rule_parse.parseString(rule)
#     print stats.asList()
#     print stats.action_list.params


    # print 'action: ', stats.action_list.action
    # print "WHEN %s %s %s DO %s" % (stats.services_options, stats.operand, stats.number, stats.action_list)
    # print "*************"
    #
    # print "condition", stats.condition, "condition2", stats.condition_list
    # print "*************"
    # print "*************"
    # print "*************"
# "FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET 1 WITH param1=2"
    # print "*************"
