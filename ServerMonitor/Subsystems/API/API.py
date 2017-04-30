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

import socketserver
import threading

from ServerMonitor.Subsystems.API.TCPHandler import APIRequestHandler


class API(threading.Thread):
    def __init__(self, _monitor, _logger, _config):
        threading.Thread.__init__(self)

        ## Object name as a string.
        self.name = "API"

        if not _monitor:
            raise ValueError("API: Wasn't handed a monitor object.")

        ## ServerMonitor::ServerMonitor object to interact with.
        self.monitor = _monitor

        if not _logger:
            raise ValueError("API: Wasn't handed a logger.")

        ## The logger.
        self.logger = _logger

        if not _config:
            raise ValueError("API: Wasn't handed a config object.")

        ## The config dictionary.
        self.config = _config.get_value("API")

        # Begin socket server setup.
        host, port = self.config["host"], self.config["port"]

        ## The TCP server object we're attaching ourselves to.
        self.server = socketserver.TCPServer((host, port), APIRequestHandler)

        self.server.RequestHandlerClass._API = self

    def run(self):
        while True:
            try:
                # Log the start.
                self.logger.info("API: Socket server opened.")

                # Aaaand run it forever.
                self.server.serve_forever()
            except Exception as e:
                self.logger.error("API: Error during socket operations: {0}".format(e))

    def handle_command(self, data):
        if not data:
            raise ValueError("No data sent to handle_command.")

        command = self.monitor.api_commands[data["cmd"]]

        if not command:
            raise ValueError("Command is not valid.")

        is_authed = False

        if len(command["auths"]):
            for auth in data["auths"]:
                if auth in command["auths"]:
                    is_authed = True
                    break
        else:
            is_authed = True

        if not is_authed:
            return {"error": True, "msg": "Not authorized to use this command."}

        if command["needs_queue"]:
            return {"error": True, "msg": "Queued commands not implemented yet."}

        if command["args"]:
            for arg in command["args"]:
                if arg not in command["args"]:
                    return {"error": True, "msg": "Not enough arguments sent."}

        return command["cmd"](data)