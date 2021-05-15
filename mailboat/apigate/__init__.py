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
"""API Gates for Mailboat.

These gates could help applications accessing features of Mailboat.
"""
from .g204 import Generating204Handler
from typing import List, Optional, Tuple
from tornado.web import Application
from tornado.httpserver import HTTPServer
from mailboat.storagehub import StorageHub
from httpx import AsyncClient


class HTTPAPIGateway(object):
    """The HTTP API Gateway for Mailboat.

    Current handlers:

    - `/generate204`: `g204.Generating204Handler`

    Related:

    - [Tornado documentation](https://www.tornadoweb.org)
    """

    def __init__(
        self,
        storage_hub: StorageHub,
        http_binds: List[Tuple[Optional[str], int]],
        debug: bool = False,
    ) -> None:
        self._application = Application(
            [(r"/generate204", Generating204Handler)],
            storage_hub=storage_hub,
            debug=debug,
        )
        self._http_server: Optional[HTTPServer] = None
        self._http_binds = http_binds
        super().__init__()

    @property
    def http_binds(self) -> List[Tuple[Optional[str], int]]:
        """The tcp binds for HTTP server.
        Each element in the list is a tuple of (binding address/hostname/None, port).

        For example:

        - `("127.0.0.1", 1989)` binds the port 1989 on address 127.0.0.1.
        - `("::0", 525)` binds the port 525 on address ::0.
        - `("mycomputer.local", 604)` binds the port 604 on hostname mycomputer.local.
        - `(None, 8080)` binds port 8080 on all network interfaces.

        Related:

        - `HTTPAPIGateway.start` the method will automatically binds a random port on 127.0.0.1 if this list is empty.
        """
        return self._http_binds

    @property
    def application(self) -> Application:
        """Application instance for HTTP server."""
        return self._application

    async def start(self) -> None:
        """Listen to the address-port pairs given in `HTTPAPIGateway.http_binds`.

        This method will bind a random port on 127.0.0.1 and put it into `HTTPAPIGateway.http_binds` list if the list is empty.
        """
        self._http_server = HTTPServer(self.application)
        for addr, port in self.http_binds:
            self._http_server.listen(port, addr if addr else "")
        else:
            # feed server a socket with a random free port
            import socket

            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            free_port = sock.getsockname()[1]
            self.http_binds.append(("127.0.0.1", free_port))
            self._http_server.listen(free_port)
            sock.close()

    async def stop(self) -> None:
        """Prevent new incoming request and wait for all existing connections closed."""
        assert self._http_server
        self._http_server.stop()
        await self._http_server.close_all_connections()
        self._http_server = None

    def http_client(self) -> AsyncClient:
        """Return a http client from httpx which uses the first bind from `HTTPAPIGateway.http_binds` as base url.

        Related:

        - [httpx documentation](https://www.python-httpx.org/)
        """
        assert self._http_server
        address, port = self.http_binds[0]
        if not address:
            address = "localhost"
        base_url = "http://{}:{}".format(address, port)
        return AsyncClient(base_url=base_url)
