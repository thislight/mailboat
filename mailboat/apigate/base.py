# Copyright (C) 2021 The Mailboat Contributors
#
# This file is part of Mailboat.
#
# Mailboat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mailboat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mailboat.  If not, see <http://www.gnu.org/licenses/>.
"""`BaseRequestHandler`: the tools used in tornado handlers.
"""
from tornado.web import RequestHandler
from mailboat.storagehub import StorageHub


class BaseRequestHandler(RequestHandler):
    """The tools used while handling requests.

    Typical usage:
    Use it instead of `tornado.web.RequestHandler`.
    ````python
    class FooRequestHandler(BaseRequestHandler):
        ...
    ````
    """

    def initialize(self) -> None:
        settings = self.application.settings
        self._storage_hub: StorageHub = settings["storage_hub"]

    @property
    def storage_hub(self) -> StorageHub:
        """Storage hub of the instance."""
        return self._storage_hub
