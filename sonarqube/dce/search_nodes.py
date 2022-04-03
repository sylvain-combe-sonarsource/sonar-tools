#
# sonar-tools
# Copyright (C) 2019-2022 Olivier Korach
# mailto:olivier.korach AT gmail DOT com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
'''

    Abstraction of the Search Node concept

'''

import sonarqube.utilities as util
import sonarqube.audit_rules as rules
import sonarqube.audit_problem as pb
import sonarqube.dce.nodes as dce_nodes

_STORE_SIZE = 'Store Size'
_ES_STATE = 'Search State'

class SearchNode(dce_nodes.DceNode):

    def __str__(self):
        return f"Search Node '{self.name()}'"

    def store_size(self):
        return util.int_memory(self.json[_ES_STATE][_STORE_SIZE])

    def name(self):
        return self.json['Name']

    def node_type(self):
        return 'SEARCH'

    def audit(self):
        util.logger.info("Auditing %s", str(self))
        return self.__audit_store_size()

    def __audit_store_size(self):
        es_heap = util.jvm_heap(self.sif.search_jvm_cmdline())
        index_size = self.store_size()

        if es_heap is None:
            rule = rules.get_rule(rules.RuleId.SETTING_ES_NO_HEAP)
            return [pb.Problem(rule.type, rule.severity, rule.msg)]
        elif index_size is None:
            util.logger.debug("Search server index size missing, audit of ES index vs heap skipped...")
            return []
        elif index_size == 0:
            rule = rules.get_rule(rules.RuleId.DCE_ES_INDEX_EMPTY)
            return [pb.Problem(rule.type, rule.severity, rule.msg.format(str(self)))]
        elif es_heap < 2 * index_size and es_heap < index_size + 1000:
            rule = rules.get_rule(rules.RuleId.SETTING_ES_HEAP)
            return [pb.Problem(rule.type, rule.severity, rule.msg.format(es_heap, index_size))]
        else:
            util.logger.debug("Search server memory %d MB is correct wrt to index size of %d MB", es_heap, index_size)
            return []

def audit(sub_sif, sif):
    nodes = []
    problems = []
    for n in sub_sif:
        nodes.append(SearchNode(n, sif))
    if len(nodes) < 3:
        rule = rules.get_rule(rules.RuleId.DCE_ES_CLUSTER_NOT_HA)
        problems.append(pb.Problem(rule.type, rule.severity, rule.msg.format()))
    for i in range(len(nodes)):
        problems += nodes[i].audit()
        size_i = nodes[i].store_size()
        if size_i is None:
            continue
        for j in range(i+1, len(nodes)):
            size_j = nodes[j].store_size()
            if size_j is None or size_j == 0:
                continue
            store_ratio = size_i / size_j
            if store_ratio < 0.5 or store_ratio > 2:
                rule = rules.get_rule(rules.RuleId.DCE_ES_UNBALANCED_INDEX)
                problems.append(pb.Problem(rule.type, rule.severity, rule.msg.format(str(nodes[i]), str(nodes[j]))))
    return problems