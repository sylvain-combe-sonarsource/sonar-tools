#
# sonar-tools
# Copyright (C) 2022 Olivier Korach
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
"""
    Abstraction of the SonarQube setting concept
"""

import re
import json
from sonar import sqobject
import sonar.utilities as util

CATEGORIES = ('general', 'languages', 'scope', 'tests', 'linters', 'authentication', 'sast', 'thrid-party')

NEW_CODE = 'sonar_.newCodePeriod'

_SETTINGS = {}

_PRIVATE_SETTINGS = (
    'sonaranalyzer', 'sonar.updatecenter', 'sonar.plugins.risk.consent',
    'sonar.core.id', 'sonar.core.startTime', 'sonar.plsql.jdbc.driver.class'
)

_INLINE_SETTINGS = (
    r'^.*\.file\.suffixes$',
    r'^.*\.reportPaths$',
    r'^sonar\.[a-z]+\.exclusions$',
    r'^sonar\.javascript\.(globals|environments)$',
    r'^sonar\.dbcleaner\.branchesToKeepWhenInactive$',
    r'^sonar.rpg.suffixes$'
)

class Setting(sqobject.SqObject):

    def __init__(self, key, endpoint, project=None, branch=None, data=None):
        super().__init__(key, endpoint)
        self.project = project
        self.branch = branch
        self.value = None
        self.inherited = None
        if data is None:
            if key == NEW_CODE:
                params = {}
                if project:
                    params['project'] = project.key
                    if branch:
                        params['branch'] = branch
                resp = self.get(api='new_code_periods/show', params=params)
                data = json.loads(resp.text)
            else:
                params = {'keys': key}
                if project:
                    params['component'] = project.key
                resp = self.get('api/settings/values', params=params)
                data = json.loads(resp.text)['settings']
        self.__load(data)
        util.logger.debug("Created %s uuid %s value %s", str(self), self.uuid(), str(self.value))
        _SETTINGS[self.uuid()] = self

    def __load(self, data):
        if self.key == NEW_CODE:
            if data['type'] == 'NUMBER_OF_DAYS':
                self.value = int(data['value'])
            else:
                self.value = data['type']
        elif self.key.startswith('sonar.issue'):
            self.value = data.get('fieldValues', None)
        else:
            self.value = util.convert_string(data.get('value', data.get('values', data.get('defaultValue', ''))))
        if 'inherited' in data:
            self.inherited = data['inherited']
        elif self.key == NEW_CODE:
            util.json_dump_debug("NEW CODE", data)
            self.inherited = False
        elif 'parentValues' in data or 'parentValue' in data or 'parentFieldValues' in data:
            self.inherited = False
        elif 'category' in data:
            self.inherited = True
        else:
            self.inherited = True
        if self.project is None:
            self.inherited = True

    def uuid(self):
        return _uuid_p(self.key, self.project, self.branch)

    def __str__(self):
        if self.project is None:
            return f"setting '{self.key}'"
        else:
            return f"setting '{self.key}' of {str(self.project)}"

    def set(self, value):
        params = {}
        if self.project:
            params['component'] = self.project.key
        return self.post('api/settings/set', params=params)

    def to_json(self):
        val = self.value
        for reg in _INLINE_SETTINGS:
            if re.match(reg, self.key) and isinstance(self.value, list):
                val = ', '.join([v.strip() for v in self.value])
                break
        return {self.key: val}

    def category(self):
        m = re.match(r'^sonar\.(cpd\.)?(abap|apex|cloudformation|c|cpp|cfamily|cobol|cs|css|flex|go|html|java|'
                     r'javascript|json|jsp|kotlin|objc|php|pli|plsql|python|rpg|ruby|scala|swift|terraform|tsql|'
                     r'typescript|vb|vbnet|xml|yaml)\.', self.key)
        if m:
            lang = m.group(2)
            if lang in ('c', 'cpp', 'objc', 'cfamily'):
                lang = 'cfamily'
            return ('languages', lang)
        if re.match(r'^.*([lL]int|govet|flake8|checkstyle|pmd|spotbugs|phpstan|psalm|detekt|bandit|rubocop|scalastyle|scapegoat).*$', self.key):
            return ('linters', None)
        if re.match(r'^sonar\.security\.config\..+$', self.key):
            return ('sast', None)
        if re.match(r'^.*\.(exclusions$|inclusions$|issue\..+)$', self.key):
            return('scope', None)

        if re.match(r'^.*(\.reports?Paths?$|unit\..*$|cov.*$)', self.key):
            return ('tests', None)
        m = re.match(r'^sonar\.(auth\.|authenticator\.downcase).*$', self.key)
        if m:
            return ('authentication', None)
        m = re.match(r'^sonar\.forceAuthentication$', self.key)
        if m:
            return ('authentication', None)
        if self.key != NEW_CODE and not re.match(r'^(email|sonar\.core|sonar\.allowPermission|sonar\.builtInQualityProfiles|sonar\.core|'
                r'sonar\.cpd|sonar\.dbcleaner|sonar\.developerAggregatedInfo|sonar\.governance|sonar\.issues|sonar\.lf|sonar\.notifications|'
                r'sonar\.portfolios|sonar\.qualitygate|sonar\.scm\.disabled|sonar\.technicalDebt|sonar\.validateWebhooks).*$', self.key):
            return ('third-party', None)
        return ('general', None)


def get_object(key, endpoint=None, data=None, project=None, branch=None):
    uu = _uuid_p(key, project, branch)
    if uu not in _SETTINGS:
        _ = Setting(key=key, endpoint=endpoint, data=data, project=project, branch=branch)
    return _SETTINGS[uu]


def get_bulk(endpoint, settings_list=None, project=None, include_not_set=False):
    """Gets several settings as bulk (returns a dict)"""
    settings_dict = {}
    params = {}
    if project:
        params['component'] = project.key
    if include_not_set:
        resp = endpoint.get('api/settings/list_definitions', params=params)
        data = json.loads(resp.text)
        settings_dict = {}
        for s in data['definitions']:
            if s['key'].endswith('coverage.reportPath') or s['key'] == 'languageSpecificParameters':
                continue
            o = Setting(s['key'], endpoint=endpoint, data=s, project=project)
            settings_dict[o.uuid()] = o
    if settings_list is None:
        pass
    elif isinstance(settings_list, list):
        params['keys'] = util.list_to_csv(settings_list)
    else:
        params['keys'] = util.csv_normalize(settings_list)
    resp = endpoint.get('api/settings/values', params=params)
    data = json.loads(resp.text)
    for s in data['settings']:
        skip = False
        for priv in _PRIVATE_SETTINGS:
            if s['key'].startswith(priv):
                skip = True
                break
        if skip:
            util.logger.debug('Skipping private setting %s', s['key'])
            continue
        o = Setting(s['key'], endpoint=endpoint, data=s, project=project)
        settings_dict[o.key] = o

    return settings_dict


def get_all(endpoint, project=None):
    return get_bulk(endpoint, project=project, include_not_set=True)


def get_new_code_period(endpoint, project):
    return get_object(key=NEW_CODE, endpoint=endpoint, project=project)


def uuid(key, project_key=None, branch=None):
    """Computes uuid for a setting"""
    if project_key is None:
        return key
    elif branch is None:
        return f"{key}#{project_key}"
    else:
        return f"{key}#{project_key}#{branch}"


def _uuid_p(key, project, branch=None):
    """Computes uuid for a setting"""
    pk = None if project is None else project.key
    return uuid(key, pk, branch)
