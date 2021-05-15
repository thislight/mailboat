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
from .g204 import Generating204Handler
from typing import List, Optional, Tuple
from tornado.web import Application
from tornado.httpserver import HTTPServer
from mailboat.storagehub import StorageHub
from httpx import AsyncClient


class HTTPAPIGateway(object):
    def __init__(
        self,
        storage_hub: StorageHub,
        http_binds: List[Tuple[Optional[str], int]],
        debug: bool = False,
    ) -> None:
        self.application = Application(
            [(r"/generate204", Generating204Handler)],
            storage_hub=storage_hub,
            debug=debug,
        )
        self.http_server: Optional[HTTPServer] = None
        self.http_binds = http_binds
        super().__init__()

    async def start(self) -> None:
        self.http_server = HTTPServer(self.application)
        for addr, port in self.http_binds:
            self.http_server.listen(port, addr if addr else "")
        else:
            # feed server a socket with a random free port
            import socket

            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            free_port = sock.getsockname()[1]
            self.http_binds.append(("127.0.0.1", free_port))
            self.http_server.listen(free_port)
            sock.close()

    async def stop(self) -> None:
        assert self.http_server
        self.http_server.stop()
        await self.http_server.close_all_connections()
        self.http_server = None

    def http_client(self) -> AsyncClient:
        assert self.http_server
        address, port = self.http_binds[0]
        if not address:
            address = "localhost"
        base_url = "http://{}:{}".format(address, port)
        return AsyncClient(base_url=base_url)
