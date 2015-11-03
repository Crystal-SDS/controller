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

"""

# def parse(input_string):
# condition_list = Forward()
services = "slowdown througput"
services_options = oneOf(services)
operand =  oneOf("< > == != <= >=")
number = Regex(r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?")
action = Word(alphas)
when = Suppress(Literal("WHEN"))
do = Suppress(Literal("DO"))
for_tenant = Suppress(Literal("FOR"))
tenant_id = Word(alphanums)
condition = Group(services_options("services_options") + operand("operand") + number("limit_value"))
boolean_condition = oneOf("AND OR")

# condition_list << ( condition ^ ( condition + boolean_condition + OneOrMore(condition_list)) )
condition_list = operatorPrecedence(condition,[
                            ("AND", 2, opAssoc.LEFT, ),
                            ("OR", 2, opAssoc.LEFT, ),
                            ])
rule_parse = for_tenant + tenant_id("tenant_id") + when + condition_list + do + action("action")


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
rules = """\
    FOR 2312 WHEN slowdown > 3 DO action
    FOR 2312 WHEN slowdown > 3 OR slowdown > 3 AND slowdown == 5 OR slowdown <= 6 DO action
    FOR 2312 WHEN slowdown > 3 AND slowdown > 50 DO action""".splitlines()

# for rule in rules:
#     try:
#         stats = rule_parse.parseString(rule)
#     except:
#         print 'This rule ***'+rule+'  *** could not be parsed'
#     else:
#         print stats.asList()

for rule in rules:

    stats = rule_parse.parseString(rule)
    print stats
    print "WHEN %s %s %s DO %s" % (stats.services_options, stats.operand, stats.number, stats.action)
    print "*************"

    print "condition", stats.condition, "condition2", stats.condition_list
    print "*************"
    print "*************"
    print "*************"

    print "*************"
