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
import json

class APIRequestHandler(socketserver.BaseRequestHandler):
    ## The class variable for the API object.
    _API = None

    def handle(self):
        # Don't process shit if we have no API object.
        if not APIRequestHandler._API:
            return

        self.API = APIRequestHandler._API

        # Request user is not whitelisted.
        if self.client_address[0] not in self.API.config["allowed_hosts"]:
            self.send_return_data({"error": True, "msg": "Address not whitelisted."})
            self.API.logger.debug(
                "API: Request address not whitelisted. Address: {0}.".format(
                    self.client_address[0]))
            return

        # The data!
        self.data = b''

        # Make sure you get all the data.
        while True:
            buffer = self.request.recv(1024)
            self.data += buffer
            if len(buffer) < 1024:
                break

        self.data = self.data.decode("utf-8")

        # No data.
        if not self.data:
            self.API.logger.debug("API: No data received from a request.")
            return

        # Catch bad data and return information.
        try:
            self.data = json.loads(self.data)
        except Exception as e:
            self.API.logger.error("API: Request error: bad JSON data. Address: {0}. Error {1}. Data: {2}".format(self.client_address[0], e, self.data))
            self.send_return_data({"error": True, "msg": "Unable to unpackage data."})
            return

        # More bad data catching.
        if "cmd" not in self.data or "auths" not in self.data or "args" not in self.data:
            self.send_return_data({"error": True, "msg": "Malformed data received."})
            self.API.logger.info(
                "API: Malformed data received. Address: {0}. Data: {1}".format(
                    self.client_address[0], self.data))
            return

        # Actually do the thing now!
        try:
            self.send_return_data(self.API.handle_command(self.data))
        except Exception as e:
            self.send_return_data(
                {"error": True, "msg": "Error caught while processing command."})
            self.API.logger.error(
                "API: Error caught while processing command: {0}. Data: {1}".format(
                    e, self.data))

        # And we're done.
        return

    def send_return_data(self, _data):
        if not _data:
            self.API.logger.debug("API: No _data sent to send_return_data.")
            return

        data = json.dumps(_data, separators=(',', ':'))
        self.request.sendall(data.encode("utf-8"))
