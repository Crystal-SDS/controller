from rules_parse import parse
import operator

mappings = {'>': operator.gt, '>=': operator.ge,
        '==': operator.eq, '<=': operator.le, '<': operator.lt,
        '!=':operator.ne, "OR":operator.or_, "AND":operator.and_}

class Rule(object):
    def __init__(self, rule_parsed):
        self.tenant = rule_parsed.tenant_id
        self.conditions = rule_parsed.condition_list.asList()
        self.action = rule_parsed.action
        self.observers = {}
        self.check_metrics(self.conditions)

    def add_metric(self, value):
        if value not in self.observers.keys():
            #TODO: Subscrive to metric observer
            self.observers[value] = None

    def check_metrics(self, condition_list):
        if not isinstance(condition_list[0], list):
            self.add_metric(condition_list[0].lower())
        else:
            for element in condition_list:
                if element is not "OR" and element is not "AND":
                    self.check_metrics(element)

    def update(self, metric, tenant_info):

        self.observers[metric]=tenant_info[metric]
        #TODO Check the last time updated the value
        if all(val!=None for val in self.observers.values()):
            result = self.check_conditions(self.conditions)
            if self.check_conditions(self.conditions):
                print self.do_action()
        else:
            print 'not all values setted', self.observers.values()

    def check_conditions(self, condition_list):
        if not isinstance(condition_list[0], list):
            result = mappings[condition_list[1]](float(self.observers[condition_list[0].lower()]), float(condition_list[2]))
        else:
            result = self.check_conditions(condition_list[0])
            for i in range(1, len(condition_list)-1, 2):
                result = mappings[condition_list[i]](result, self.check_conditions(condition_list[i+1]))

        return result

    def do_action(self):
        # TODO: Call SDS Controller API functions
        return 'hola que tal!! :D'
