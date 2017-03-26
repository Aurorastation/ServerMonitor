#    Aurora Server Monitor - a python monitor program created to manage an SS13 server.
#    Copyright (C) 2016 Skull132

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.

import logging
import time

from ServerMonitor.Subsystems import *

class ServerMonitor:
    def __init__(self, config_path):
        # Set up the logger:
        self.logger = self.get_logger()

        self.logger.info("MAIN: Server monitor initializing.")

        # Get the config file:
        try:
            self.config = Config(config_path, self.logger)
            self.logger.debug("MAIN: Creation: config created.")
        except ValueError as e:
            self.logger.error("MAIN: Value error during Config creation. {0}".format(e))
            raise RuntimeError("Exception caught during creation. Ceasing.")
        except RuntimeError as e2:
            self.logger.error("MAIN: Runtime error during Config creation. {0}".format(e2))
            raise RuntimeError("Exception caught during creation. Ceasing.")

        # Set up the API:
        try:
            self.API = API(self, self.logger, self.config)
            self.API.start()
        except ValueError as e:
            self.logger.error("MAIN: Value error during API creation. {0}".format(e))
            raise RuntimeError("Exception caught during creation. Ceasing.")
        except Exception as e2:
            self.logger.error("MAIN: Generic exception caught during API creation. {0}".format(e2))
            raise RuntimeError("Exception caught during creation. Ceasing.")

        # Events queue
        self.events = {}

        # Server datum list
        self.servers = []

        # Server datum cache
        self.generate_servers()

        self.logger.debug("MAIN: Server monitor initilization completed.")

        # The command dictionary for the API. May need refactoring.
        self.api_commands = {
            "server_control": {
                "cmd": self.cmd_control_server,
                "args": ["control", "server"],
                "auths": [],
                "needs_queue": False
            },
            "get_servers": {
                "cmd": self.cmd_get_servers,
                "args": [],
                "auths": ["R_ADMIN", "R_DEV"],
                "needs_queue": False
            }
        }

    def get_logger(self):
        _logger = logging.getLogger("monitor")
        _logger.setLevel(logging.DEBUG)

        _handler = logging.FileHandler(filename = "monitor.log", encoding = "utf-8", mode = "w")
        _handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s: %(message)s"))

        _logger.addHandler(_handler)

        return _logger

    def run(self):
        for i, server in enumerate(self.servers):
            if server.start:
                self.start_server(server)

        # Sleep the main thread. Yaaay.
        while True:
            time.sleep(360)

    def generate_servers(self):
        self.servers = []
        for key in self.config.get_value("servers"):
            dict = self.config.get_value("servers")[key]
            try:
                data = ServerData(key, dict["game-path"], dict["git-path"], dict["byond-path"], dict["port"], dict["visibility"], dict["start"], dict["auths"])
                self.servers.append(data)
            except ValueError as e:
                self.logger.error("MAIN: Error adding a server to the pool: {0}".format(e))
            except Exception as e1:
                self.logger.error("MAIN: Malformed data or other error adding server to pool: {0}".format(e1))

        self.logger.debug("MAIN: Server list repopulated.")

    def start_server(self, server):
        if not server:
            return

        if not server.server_ready:
            return

        if server.server_thread:
            return

        server.server_thread = Server(server, self.logger)
        server.server_thread.start()

    def stop_server(self, server):
        if not server:
            return

        if not server.server_thread:
            return

        server.server_thread.stop_server()
        server.server_thread = None

    def restart_server(self, server):
        if not server:
            return

        if not server.server_thread:
            return

        self.stop_server(server)
        self.start_server(server)

    def cmd_get_servers(self, _data):
        data = {"error": False, "msg": None, "data": {}}

        for server in self.servers:
            server_info = {}
            if server.server_thread:
                server_info["running"] = server.server_thread.running
            else:
                server_info["running"] = False

            server_info["can_run"] = server.server_ready

            data["data"][server.name] = server_info

        return data

    def cmd_control_server(self, _data):
        server = None

        for obj in self.servers:
            if obj.name == _data["args"]["server"]:
                server = obj
                break

        if not server:
            return {"error": True, "msg": "Invalid server name."}

        can_control = False
        for auth in _data["auths"]:
            if auth in server.auths:
                can_control = True
                break

        if not can_control:
            return {"error": True, "msg": "Not authorized to control this specific server."}

        if _data["args"]["control"] == "start":
            if server.server_thread and server.server_thread.running:
                return {"error": True, "msg": "Server is already running."}

            if not server.server_ready:
                return {"error": True, "msg": "Server is not compiled."}

            self.start_server(server)

            return {"error": False, "msg": "Server start event received. It should be up in 3 minutes."}
        elif _data["args"]["control"] == "restart":
            if server.server_thread:
                self.restart_server(server)

                return {"error": False, "msg": "Server restart event received. It should close and start back up within 6 minutes."}
            else:
                return {"error": True, "msg": "Server is not running. Restart impossible."}
        elif _data["args"]["control"] == "stop":
            if server.server_thread:
                if not server.server_thread.running:
                    return {"error": False, "msg": "Server is already shutting down. Please wait."}

                self.stop_server(server)

                return {"error": False, "msg": "Server shut down initiated. It should close within 3 minutes."}
            else:
                return {"error": True, "msg": "Server is not running. Shut down impossible."}
        else:
            return {"error": True, "msg": "Invalid command requested."}