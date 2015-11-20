from pyparsing import *
import abstract_metric
import redis
import json
import ast

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
r = redis.StrictRedis(host='localhost', port=6379, db=0)

def parse_group_tenants(tokens):
    print 'tokens, ', tokens
    data = r.lrange(tokens[0], 0, -1)
    return data
    print 'data_parse_group_tenant', data


def parse(input_string):
    #TODO Add error control.
    #TODO Raise an exception if not metrics or not action registred
    #TODO Raise an exception if group of tenants don't exists.
    #TODO Add transcient option


    #Support words to construct the grammar.
    word = Word(alphas)
    when = Suppress(Literal("WHEN"))
    literal_for = Suppress(Literal("FOR"))
    boolean_condition = oneOf("AND OR")

    #Condition part
    param = Word(alphanums)+ Suppress(Literal("=")) + Word(alphanums)
    metrics_workload = r.keys("metric:*")
    services = map(lambda x: "".join(x.split(":")[1]), metrics_workload)
    services_options = oneOf(services)
    operand =  oneOf("< > == != <= >=")
    number = Regex(r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?")
    condition = Group(services_options + operand("operand") + number("limit_value"))
    condition_list = operatorPrecedence(condition,[
                                ("AND", 2, opAssoc.LEFT, ),
                                ("OR", 2, opAssoc.LEFT, ),
                                ])

    #For tenant or group of tenants
    tenant_id = Word(alphanums)
    group_id = Word(nums)
    tenant_group = Combine(Literal("G:") + group_id)
    tenant_group_list = tenant_group + ZeroOrMore(Suppress("AND")+tenant_group)
    tenant_list = tenant_id + ZeroOrMore(Suppress("AND")+tenant_id)
    subject = Group(tenant_list ^ tenant_group_list)

    #Action part
    action = oneOf("SET DELETE")
    sfilters_list = r.keys("filter:*")
    sfilter = map(lambda x: "".join(x.split(":")[1]), sfilters_list)

    with_params = Suppress(Literal("WITH"))
    do = Suppress(Literal("DO"))
    params_list = delimitedList(param)


    #Functions post-parsed
    convertToDict = lambda tokens : dict(zip(*[iter(tokens)]*2))
    remove_repeted_elements = lambda tokens : [list(set(tokens[0]))]

    params_list.setParseAction(convertToDict)
    subject.setParseAction(remove_repeted_elements)
    tenant_group.setParseAction(parse_group_tenants)

    #Final rule structure
    rule_parse = literal_for + subject("subject") + when +\
                condition_list("condition_list") + do + Group(action("action") + \
                oneOf(sfilter)("filter") + Optional(with_params + params_list("params")))("action_list")

    #Parse the rule
    parsed_rule = rule_parse.parseString(input_string)

    #Pos-parsed validation
    if parsed_rule.action_list.params:
        filter_info = r.hgetall("filter:"+str(parsed_rule.action_list.filter))

        params = eval(filter_info["params"])
        result = set(parsed_rule.action_list.params.keys()).intersection(params.keys())
        if len(result) == len(parsed_rule.action_list.params.keys()):
            #TODO Check params types.
            return parsed_rule
        else:
            raise Exception

    return parsed_rule



# rules = """\
#     FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET compression WITH param1=2
#     FOR G:4 WHEN slowdown > 3 OR slowdown > 3 AND slowdown == 5 OR slowdown <= 6 DO SET compression WITH param1=2, param2=3
#     FOR G:4 AND G:4 WHEN slowdown > 3 AND slowdown > 50 DO SET compression WITH""".splitlines()
#
# for rule in rules:
#     stats = parse(rule)
#     print 'as_list', stats.asList()
#     print stats
#     print 'subject', stats.subject
#     print "group", stats.subject.tenant_group_list
    # try:
    #     stats = parse(rule)
    # except:
    #     print 'This rule ***'+rule+'  *** could not be parsed'
    # else:
    #     print stats.asList()
