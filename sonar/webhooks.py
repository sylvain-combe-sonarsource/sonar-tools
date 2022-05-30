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

    Abstraction of the SonarQube "webhook" concept

"""

import json
import sonar.utilities as util
import sonar.sqobject as sq

_WEBHOOKS = {}


class WebHook(sq.SqObject):
    def __init__(self, name, endpoint, url=None, secret=None, project=None, data=None):
        super().__init__(name, endpoint)
        if data is None:
            params = util.remove_nones({"name": name, "url": url, "secret": secret, "project": project})
            data = json.loads(self.post("webhooks/create", params=params).text)["webhook"]
        self._json = data
        self.name = data["name"]
        self.key = data["key"]
        self.url = data["url"]
        self.secret = data.get("secret", None)
        self.project = project
        self.last_delivery = data.get("latestDelivery", None)
        _WEBHOOKS[self.uuid()] = self

    def __str__(self):
        return f"webhook '{self.name}'"

    def uuid(self):
        return _uuid(self.name, self.project)

    def update(self, **kwargs):
        params = util.remove_nones(kwargs)
        params.update({"name":  self.name, "webhook": self.key})
        self.post("webhooks/update", params=params)

    def to_json(self):
        json_data = {
            "name": self.name,
            "key": self.key,
            "url": self.url,
            "secret": self.secret,
        }
        if self.last_delivery is not None:
            json_data.update(
                {
                    "lastDeliveryDate": self.last_delivery.get("at", None),
                    "lastDeliverySuccess": self.last_delivery.get("success", None),
                    "lastDeliveryHttpStatus": self.last_delivery.get("httpStatus", None),
                    "lastDeliveryDuration": self.last_delivery.get("durationMs", None),
                }
            )
        return json_data


def search(endpoint, params=None):
    return sq.search_objects(api="webhooks/list", params=params, returned_field="webhooks", key_field="key", object_class=WebHook, endpoint=endpoint)


def get_list(endpoint, project_key=None):
    util.logger.debug("Getting webhooks for project key %s", str(project_key))
    params = None
    if project_key is not None:
        params = {"project": project_key}
    return search(endpoint, params)


def export(endpoint, project_key=None):
    json_data = {}
    for wb in get_list(endpoint, project_key).values():
        j = wb.to_json()
        for k in j.copy().keys():
            if k.startswith("lastDelivery") or k in ("name", "key"):
                j.pop(k)
        json_data[wb.name] = util.remove_nones(j)
    return json_data if len(json_data) > 0 else None


def create(endpoint, name, url, secret=None, project=None):
    return WebHook(name, endpoint, url=url, secret=secret, project=project)


def update(endpoint, name, **kwargs):
    project_key = kwargs.pop("project", None)
    get_list(endpoint, project_key)
    if _uuid(name, project_key) not in _WEBHOOKS:
        create(endpoint, name, kwargs["url"], kwargs["secret"], project=project_key)
    else:
        get_object(name, endpoint, project_key=project_key, data=kwargs).update(**kwargs)


def get_object(name, endpoint, project_key=None, data=None):
    util.logger.debug("Getting webhook name %s project key %s data = %s", name, str(project_key), str(data))
    u = _uuid(name, project_key)
    if u not in _WEBHOOKS:
        _ = WebHook(name=name, endpoint=endpoint, data=data)
    return _WEBHOOKS[u]


def _uuid(name, project_key):
    p = "" if project_key is None else f":PROJECT:{project_key}"
    return f"{name}{p}"