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

import threading
import subprocess
import time

## A class responsible for running and monitoring a server.
class Server(threading.Thread):
    ## The constructor
    #
    # @param self The object pointer.
    # @param _data A %ServerData object which contains all of the information
    # necessary for operation of this server.
    # @param _logger A logger object.
    #
    # @throws ValueError In case of _data or _logger missing.
    def __init__(self, _data, _logger):
        threading.Thread.__init__(self)

        if not _data:
            raise ValueError("SERVER NULL: Wasn't handed a server data object.")

        # The server data object.
        self.data = _data

        # The name for the server.
        self.name = self.data.name

        # The logger.
        if not _logger:
            raise ValueError("SERVER {0}: Wasn't handed a logger.".format(self.name))

        self.logger = _logger

        # The process object.
        self.process = None

        # The running indicator
        self.running = False

    ## Starts the server and the thread.
    #
    # Will run into a while (self.running) loop which keeps the server going
    # until the boolean is set to false. Automatic restarts are included in this
    # loop.
    #
    # Since run exits once the server is told to stop, the thread will also then
    # close and terminate.
    #
    # @param self The object pointer.
    #
    # @throw RuntimeError In case a server that's already running is given a second
    # start by an external source.
    def run(self):
        if self.process is None:
            self.running = True

            while self.running:
                self.logger.info("SERVER {0}: Started.".format(self.name))

                # This blocks.
                self.start_server()
                self.logger.warning("SERVER {0}: DreamDaemon closed. Waiting.".format(self.name))
                time.sleep(30)

        else:
            raise RuntimeError("SERVER {0}: Attempted to run a second time"
                               " while already running.".format(self.name))

    ## Will start the server and waits for it to exit.
    #
    # @param self The object pointer.
    #
    # @throws RuntimeException In case of any errors from the subprocess.
    def start_server(self):
        args = [self.data.get_dd_path(), self.data.get_dmb_path(),
                '-port {0}'.format(self.data.port), '-trusted',
                self.data.visibility, '-close']

        try:
            self.process = subprocess.Popen(args)
        except Exception as e:
            raise RuntimeError(
                "SERVER {0}: Runtimed while attempting to start: {1}".format(self.name, e))

        self.process.wait()

        self.logger.info("SERVER {0}: Dreamdaemon stopped.".format(self.name))

    ## Will forcefully terminate the server.
    #
    # If self.running is left as True, this will act as a forced restart command.
    #
    # @param self The object pointer.
    def force_restart(self):
        if self.running and self.process:
            self.logger.warning("SERVER {0}: Force restart initiated.".format(self.name))

            self.process.terminate()

    ## Will permanently stop the server and join it.
    #
    # Unlike %force_restart, this will close the server permanently and then join
    # the thread.
    #
    # @param self The object pointer.
    #
    # @throws RuntimeError In case a shutdown command is issued to a server that's
    # not running.
    def stop_server(self):
        if self.running:
            self.running = False

            # Stop the server.
            self.process.terminate()

            self.logger.warning("SERVER {0}: Force shut down initiated.".format(self.name))

            # RIP the thread at the end.
            self.join()
        else:
            raise RuntimeError(
                "SERVER {0}: Attempted to shut down, but was found not running.".format(self.name))
