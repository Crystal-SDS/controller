from rules_parse import parse
import operator
mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne}

class Rule(object):
    def __init__(self, rule_parsed):
        self.tenant = rule_parsed.tenant_id
        self.conditions = rule_parsed.condition_list
        self.action = rule_parsed.action

    def update(self, metric, tenant_info):

        self.conditions

        if self.condition( float(tenant_info["througput"]), float(self.limit_value)):

            print 'uiii'
            print self.do_action()

    def base_func(self, value, condition, limit_value):
        return mappings[condition](float(value), float(limit_value))

    def recursive_func(self, list):
        if type(list[0]) is not list and type(list[2]) is not list:
            return base_func(list[0], list[1], list[2])

        right = self.recursive_func(list[0])
        left = self.recursive_func(list[2])

        if list[1] == "OR":
            return (right or left)
        else:
            return (right and left)






    def do_action(self):
        # TODO: Call SDS Controller API functions
        return 'hola que tal!! :D'
