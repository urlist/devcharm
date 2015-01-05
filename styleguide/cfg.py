"""A simple CFG generator from
http://www.decontextualize.com/teaching/rwet/recursion-and-context-free-grammars/

# clauses
S -> NP VP
S -> Interj NP VP
NP -> Det N
NP -> Det N that VP
NP -> Det Adj N
VP -> Vtrans NP   # transitive verbs have direct objects
VP -> Vintr       # intransitive verbs have no direct object

# terminals
Interj -> oh, | my, | wow, | damn,
Det -> this | that | the
N -> amoeba | dichotomy | seagull | trombone | corsage | restaurant | suburb
Adj -> bald | smug | important | tame | overstaffed | luxurious | blue
Vtrans -> computes | examines | foregrounds | prefers | interprets | spins
Vintr -> coughs | daydreams | whines | slobbers | vocalizes | sneezes
"""

import re
from random import choice

class ContextFree(object):
    def __init__(self):
        self.rules = dict()
        self.expansion = list()

    # rules are stored in self.rules, a dictionary; the rules themselves are
    # lists of expansions (which themselves are lists)
    def add_rule(self, rule, expansions):
        self.rules[rule] = expansions

    def expand(self, start):
        # if the starting rule was in our set of rules, then we can expand it
        keys = re.findall('\$\w+', start)
        if not keys:
            return start

        template = re.sub('\$\w+', '{}', start)
        vals = []
        for key in keys:
            vals.append(choice(self.rules.get(key, [''])))

        final = template.format(*vals).replace('\\n', '\n')
        return self.expand(final)

    # utility method to run the expand method and return the results
    def generate(self, axiom):
        return u''.join(self.expand(axiom))


# if __name__ == '__main__':
#     cfree = ContextFree()
#     cfree.add_rule('S', ['NP', 'VP'])
#     cfree.add_rule('NP', ['the', 'N'])
#     cfree.add_rule('N', ['cat'])
#     cfree.add_rule('N', ['dog'])
#     cfree.add_rule('N', ['weinermobile'])
#     cfree.add_rule('N', ['duchess'])
#     cfree.add_rule('VP', ['V', 'the', 'N'])
#     cfree.add_rule('V', ['sees'])
#     cfree.add_rule('V', ['chases'])
#     cfree.add_rule('V', ['lusts after'])
#     cfree.add_rule('V', ['blames'])
#
#     expansion = cfree.get_expansion('S')
#     print ' '.join(expansion)


def parse(rules):
    # rules are stored in the given file in the following format:
    # Rule -> a | a b c | b c d
    # ... which will be translated to:
    # self.add_rule('Rule', ['a'])
    # self.add_rule('Rule', ['a', 'b', 'c'])
    # self.add_rule('Rule', ['b', 'c', 'd'])
    cfree = ContextFree()
    for line in rules.split('\n'):
        line = re.sub(r"^#.*$", "", line)  # get rid of comments
        line = line.strip()  # strip any remaining white space
        match_obj = re.search(r"(\$\w+) *-> *(.*)", line)
        if match_obj:
            rule = match_obj.group(1)
            expansions = re.split(r"\s*\|\s*", match_obj.group(2))
            cfree.add_rule(rule, expansions)

    return cfree


