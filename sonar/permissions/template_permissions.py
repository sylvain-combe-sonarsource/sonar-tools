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

from sonar import utilities
from sonar.permissions import permissions

class TemplatePermissions(permissions.Permissions):
    API_GET = {"users": "permissions/template_users", "groups": "permissions/template_groups"}
    API_SET = {"users": "permissions/add_user_to_template", "groups": "permissions/add_group_to_template"}
    API_REMOVE = {"users": "permissions/remove_user_from_template", "groups": "permissions/remove_group_from_template"}
    API_GET_FIELD = {"users": "login", "groups": "name"}
    API_SET_FIELD = {"users": "login", "groups": "groupName"}

    def __init__(self, concerned_object):
        self.concerned_object = concerned_object
        super().__init__(concerned_object.endpoint)

    def __str__(self):
        return f"permissions of {str(self.concerned_object)}"

    def read(self, perm_type=None):
        self.permissions = permissions.NO_PERMISSIONS
        for p in permissions.normalize(perm_type):
            self.permissions[p] = self._get_api(
                TemplatePermissions.API_GET[p],
                p,
                TemplatePermissions.API_GET_FIELD[p],
                templateId=self.concerned_object.key,
                ps=permissions.MAX_PERMS,
            )
        self._remove_aggregations_creator()
        return self

    def set(self, new_perms):
        utilities.logger.debug("Setting %s with %s", str(self), str(new_perms))
        if self.permissions is None:
            self.read()
        for p in permissions.PERMISSION_TYPES:
            if new_perms is None or p not in new_perms:
                continue
            decoded_perms = {k: permissions.decode(v) for k, v in new_perms[p].items()}
            to_remove = permissions.diff(self.permissions[p], decoded_perms)
            self._post_api(TemplatePermissions.API_REMOVE[p], TemplatePermissions.API_SET_FIELD[p], to_remove, templateId=self.concerned_object.key)
            to_add = permissions.diff(decoded_perms, self.permissions[p])
            self._post_api(TemplatePermissions.API_SET[p], TemplatePermissions.API_SET_FIELD[p], to_add, templateId=self.concerned_object.key)
        return self.read()