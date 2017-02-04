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

import yaml
import os.path

class Config:
    def __init__(self, _path, _logger):
        # Validate args.
        if _path is None:
            raise ValueError("No config path provided to Config.")

        if _logger is None:
            raise ValueError("No logger provided to Config.")

        # Assign logger.
        self.logger = _logger

        # Initialize config as a dictionary.
        self.config = {}

        if not os.path.isfile(_path):
            raise RuntimeError("Config is unable to open configuration file.")

        with open(_path, 'r') as f:
            try:
                self.config = yaml.load(f)
            except yaml.YAMLError as e:
                raise RuntimeError(e)

    def get_value(self, key):
        if key in self.config:
            return self.config[key]

        return None