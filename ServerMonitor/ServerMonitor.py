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


## The main program class. Constructed in main.py.
#
# This construct combines every submodule into one piece. During initialization,
# it'll read the configuration file and produce ServerData objects, with which it'll
# populate its servers.
#
# Upon starting this object, with ServerMonitor.start, it'll enter the ServerMonitor::ServerMonitor::run
# function and block the main thread. All other servers, API, and auxiliary constructs
# execute in their own threads.
class ServerMonitor:
    ## The constructor.
    #
    # @param self The object pointer.
    # @param config_path The path to the configuration file which will be used
    # to initialize the Subsystems::Config::Config object.
    def __init__(self, config_path):
        ## Logger object.
        self.logger = self.get_logger()

        self.logger.info("MAIN: Server monitor initializing.")

        # Get the config file:
        try:
            ## The Subsystems::Config::Config object attached to this instance.
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
            ## Subsystems::API::API object for handling outside commands.
            self.api = API(self, self.logger, self.config)
        except ValueError as e:
            self.logger.error("MAIN: Value error during API creation. {0}".format(e))
            raise RuntimeError("Exception caught during creation. Ceasing.")
        except Exception as e2:
            self.logger.error("MAIN: Generic exception caught during API creation. {0}".format(e2))
            raise RuntimeError("Exception caught during creation. Ceasing.")

        ## Events queue.
        self.tasks = []

        ## Subsystems::ServerData::ServerData datum list
        self.servers = []

        # Server datum cache
        self.generate_servers()

        self.logger.debug("MAIN: Server monitor initilization completed.")

        ## The command dictionary for the API. May need refactoring.
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
            },
            "create_task": {
                "cmd": self.cmd_create_task,
                "args": ["server", "commands"],
                "auths": [],
                "needs_queue": True
            }
        }

    ## Getter for a new logger object.
    #
    # Should only be called in the cosntructor. Forces the logger to log into
    # "monitor.log" file.
    #
    # @param self The object pointer.
    #
    # @returns logging.logger object.
    def get_logger(self):
        _logger = logging.getLogger("monitor")
        _logger.setLevel(logging.DEBUG)

        _handler = logging.FileHandler(filename="monitor.log", encoding="utf-8", mode="w")
        _handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s: %(message)s"))

        _logger.addHandler(_handler)

        return _logger

    ## The thread main method.
    #
    # A blocking function. It runs the API thread and will also start all of
    # the servers whose ServerData::ServerData::start is set to True.
    #
    # @param self The object pointer.
    def run(self):
        # Start the API.
        self.api.start()

        # Cycle over servers that should be started. And start them.
        for server in self.servers:
            if server.start:
                self.start_server(server)

        # Sleep the main thread. Yaaay.
        while True:
            self.process_tasks()
            time.sleep(30)

    ## Populates the %ServerMonitor::ServerMonitor::servers list with ServerData::ServerData
    # objects.
    #
    # @param self The object pointer.
    def generate_servers(self):
        self.servers = []
        for key in self.config.get_value("servers"):
            dictionary = self.config.get_value("servers")[key]
            try:
                data = ServerData(key, dictionary)
                self.servers.append(data)
            except ValueError as e:
                self.logger.error("MAIN: Error adding a server to the pool: %s", e)
            except Exception as e1:
                self.logger.error(
                    "MAIN: Malformed data or other error adding server to pool: %s", e1)

        self.logger.debug("MAIN: Server list repopulated.")

    ## Processes the %tasks queue.
    #
    # Iterates over the worker queue, and checks whether their attached server
    # objects have tasks assigned. If not, we fill that gap.
    #
    # @param self The object pointer.
    def process_tasks(self):
        if not len(self.tasks):
            return

        for task in self.tasks:
            if not task.server.server_task:
                # Start the task.
                # Task::Task::run (invoked with start) attaches and later detaches
                # from the ServerData object properly.
                task.start()

                # Remove it from the queue.
                self.tasks.remove(task)

    ## Starts a server.
    #
    # If the server doesn't have an already attached Server::Server object,
    # it'll generate one, attach it, and start it. Thus effectively starting
    # the server.
    #
    # @param self The object pointer.
    # @param server The ServerData::ServerData object that we're starting.
    def start_server(self, server):
        if not server:
            return

        if not server.server_ready:
            return

        if server.server_thread:
            return

        server.server_thread = Server(server, self.logger)
        server.server_thread.start()

    ## Stops a server.
    #
    # If the server parametre has an attached server_thread, then it'll order it
    # to stop, via invoking Server::Server::stop_server, and detaching it from
    # server object itself. The stop_server method also joins the server overwatching
    # thread.
    #
    # @param self The object pointer.
    # @param server The ServerData::ServerData object that we'll be stopping.
    def stop_server(self, server):
        if not server:
            return

        if not server.server_thread:
            return

        server.server_thread.stop_server()
        server.server_thread = None

    ## Restarts a server.
    #
    # Calls Server::Server::force_restart on the server, in order to restart the
    # server.
    #
    # @param self The object pointer.
    # @param server The ServerData::ServerData object that we'll be restarting.
    def restart_server(self, server):
        if not server:
            return

        if not server.server_thread:
            return

        server.server_thread.force_restart()

    ## API command for getting a list of all servers.
    #
    # @param self The object pointer.
    # @param _data The dictionary containing information received from the API.
    # The dictionary is irrelevant for this command, and only used to maintain
    # the same command structure for all API commands.
    #
    # @returns A dictionary with the following keys:
    # "error" - A boolean describing the success of the operation.
    # "msg" - A generic feedback message. Usually describes the error, can be None.
    # "data" - A dictionary containing the server names, their current status, and
    # whether or not they can be started.
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

    ## API command for starting, restarting, and stopping a server.
    #
    # @param self The object pointer.
    # @param _data The dictionary containing information received from the API.
    # The dictionary should contain a key called "args", which has fields for
    # "server" and "control". "control" can be one of three values: "stop", "start",
    # "restart".
    #
    # @returns A dictionary with the following keys:
    # "error" - A boolean describing the success of the operation.
    # "msg" - A generic feedback message. Usually describes the error, can be None.
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

                return {"error": False,
                        "msg": "Server shut down initiated. It should close within 3 minutes."}
            else:
                return {"error": True, "msg": "Server is not running. Shut down impossible."}
        else:
            return {"error": True, "msg": "Invalid command requested."}

    ## API command for queueing a task.
    #
    # It creates a Task::Task object and appends it to the %tasks list, waiting
    # execution in the main thread.
    #
    # @param self The object pointer.
    # @param _data The dictionary containing information received from the API.
    # The dictionary should contain a key called "args", which has fields for
    # "server" and "commands". "commands" should be a list of numbers.
    # Can optionally include "pr_num", if the API request is related to a PR being
    # merged.
    #
    # @returns A dictionary with the following keys:
    # "error" - A boolean describing the success of the operation.
    # "msg" - A generic feedback message. Usually describes the error, can be None.
    def cmd_create_task(self, _data):
        server = None

        for obj in self.servers:
            if obj.name == _data["args"]["server"]:
                server = obj
                break

        if not server:
            return {"error": True, "msg": "Invalid server name."}

        if not len(_data["args"]["commands"]):
            return {"error": True, "msg": "Empty command list sent."}

        commands = _data["args"]["commands"]

        pr_num = 0
        if _data["args"]["pr_num"]:
            pr_num = _data["args"]["pr_num"]

        task = Task(commands, server, pr_num)

        self.tasks.append(task)

        return {"error": False, "msg": "Command successfully queued."}
