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

import os.path

## A data object holding information from a config file about a server.
#
# Used as a variable and data holder by Server::Server. Also has getters for
# "complex" path operations.
class ServerData():
    ## The constructor.
    #
    # @param self The object pointer.
    # @param _name The string name of the server.
    # @param dictionary The dictionary containing initial information about the
    # server object, directly from the configuration file.
    #
    # @throws ValueError In case of a missing or bad argument.
    def __init__(self, _name, dictionary):
        if not _name:
            raise ValueError("SERVER DATA: No name provided.")
        ## The unique name for the server. For ID purposes.
        self.name = _name

        if not dictionary["game-path"]:
            raise ValueError("SERVER {0}: No game path provided.".format(self.name))
        ## The path for the symlinked .dmb
        self.game_path = dictionary["game-path"]

        ## Determines whether or not installation is required or not.
        self.server_ready = os.path.isfile(self.game_path + "\\baystation12.dmb")

        if not dictionary["git-path"]:
            raise ValueError("SERVER {0}: No git path provided.".format(self.name))
        ## The path for the project root.
        self.git_path = dictionary["git-path"]

        if not dictionary["git-branch"]:
            raise ValueError("SERVER {0}: No git branch name provided.".format(self.name))
        ## The name of the git branch this server will be pulling and syncing with.
        self.git_branch = dictionary["git-branch"]

        ## Determines whether or not the code is present and ready for compile/install.
        self.compile_ready = os.path.isfile(self.git_path + "\\baystation12.dme")

        if not dictionary["byond-path"]:
            raise ValueError("SERVER {0}: No DreamDaemon path provided.".format(self.name))
        ## The path to the BYOND executable used for this server.
        self.byond_path = dictionary["byond-path"]

        if not dictionary["port"]:
            raise ValueError("SERVER {0}: No port provided.".format(self.name))
        ## Server port.
        self.port = dictionary["port"]

        if dictionary["visibility"] not in ["-public", "-invisible", "-private"]:
            raise ValueError("SERVER {0}: Invalid visibility variable provided.".format(self.name))
        ## Server visibility.
        #
        # Valid values: "-public", "-invisible", "-private".
        self.visibility = dictionary["visibility"]

        ## Do we want to start immediately or not?
        self.start = dictionary["start"]

        # Sanity checks for days.
        if not os.path.isfile(self.byond_path + "\\dreamdaemon.exe") or not\
            os.path.isfile(self.byond_path + "\\dreammaker.exe"):
            raise ValueError("SERVER {0}: Assigned DreamDaemon path does not contain the required .exes.".format(self.name))

        if not os.path.isdir(self.git_path):
            raise ValueError("SERVER {0}: Git path does not exist.".format(self.name))

        ## The object for the Server::Server we're going to have.
        self.server_thread = None

        ## The Task::Task which is currently tending to this server.
        self.server_task = None

        ## The string names of the perms that can control this server.
        self.auths = {}
        if dictionary["auths"]:
            self.auths = dictionary["auths"]

    ## Getter for the DreamDaemon.exe used to run this server.
    def get_dd_path(self):
        return os.path.join(self.byond_path, "\\dreamdaemon.exe")

    ## Getter for the DreamMaker.exe used to compile this server's code.
    def get_dm_path(self):
        return os.path.join(self.byond_path, "\\dreammaker.exe")

    ## Getter for the .dme file of the server.
    def get_dme_path(self):
        return os.path.join(self.git_path, "\\baystation12.dme")

    ## Getter for the .dmb file of the server.
    def get_dmb_path(self):
        return os.path.join(self.game_path, "\\baystation12.dmb")

    ## Getter for the changelog tool (python program) of the server.
    def get_changelog_tool(self):
        return os.path.join(self.git_path, "tools\\GenerateChangelog\\ss13_genchangelog.py")
