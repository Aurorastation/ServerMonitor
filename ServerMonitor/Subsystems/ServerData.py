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

class ServerData():
    def __init__(self, _name, _game_path, _git_path, _byond_path, _port, _visibility, _start, _auths):

        # The unique name for the server. For ID purposes.
        if not _name:
            raise ValueError("SERVER DATA: No name provided.")
        self.name = _name

        # The path for the symlinked .dmb
        if not _game_path:
            raise ValueError("SERVER {0}: No game path provided.".format(self.name))
        self.game_path = _game_path

        # See if we're ready to boot up immediately.
        self.server_ready = os.path.isfile(self.game_path + "\\baystation12.dmb")

        # The path for the project root.
        if not _git_path:
            raise ValueError("SERVER {0}: No git path provided.".format(self.name))
        self.git_path = _git_path

        # Check if we have the code already downloaded.
        self.compile_ready = os.path.isfile(self.git_path + "\\baystation12.dme")

        # Check if we actually have a BYOND directory given.
        if not _byond_path:
            raise ValueError("SERVER {0}: No DreamDaemon path provided.".format(self.name))
        self.byond_path = _byond_path

        # Server port.
        if not _port:
            raise ValueError("SERVER {0}: No port provided.".format(self.name))
        self.port = _port

        # Server visibility.
        if _visibility not in ["-public", "-invisible", "-private"]:
            raise ValueError("SERVER {0}: Invalid visibility variable provided.".format(self.name))
        self.visibility = _visibility

        # Do we want to start immediately or not?
        self.start = _start

        # Sanity checks for days.
        if not os.path.isfile(self.byond_path + "\\dreamdaemon.exe") or not os.path.isfile(self.byond_path + "\\dreammaker.exe"):
            raise ValueError("SERVER {0}: Assigned DreamDaemon path does not contain the required .exes.".format(self.name))

        if not os.path.isdir(self.git_path):
            raise ValueError("SERVER {0}: Git path does not exist.".format(self.name))

        # The object for the Subsystems.Server we're going to have.
        self.server_thread = None

        # The string names of the perms that can control this server.
        self.auths = {}
        if _auths:
            self.auths = _auths

    def get_dd_path(self):
        return self.byond_path + "\\dreamdaemon.exe"

    def get_dm_path(self):
        return self.byond_path + "\\dreammaker.exe"

    def get_dme_path(self):
        return self.git_path + "\\baystation12.dme"

    def get_dmb_path(self):
        return self.game_path + "\\baystation12.dmb"