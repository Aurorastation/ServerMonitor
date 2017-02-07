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
import pygit2
import subprocess
import os
import shutil

class Task(threading.Thread):
    def __init__(self, _tasks, _server):
        threading.Thread.__init__(self)
        self.can_join = False

        if not _tasks:
            self.can_join = True
            raise ValueError("No task given.")
        self.tasks = _tasks

        if not _server:
            self.can_join = True
            raise ValueError("No serverData object given.")
        self.server = _server

    def run(self):
        pass

    def pull(self, remote_name = 'origin', branch = 'master'):
        """Pull new changes from a specific remote and branch."""
        repo = pygit2.Repository(self.server.git_path + "\\.git")

        # Snippet from MichaelBoselowitz/pygit2-examples/examples.py from Github.
        for remote in repo.remotes:
            if remote.name == remote_name:
                remote.fetch()
                remote_master_id = repo.lookup_reference('refs/remotes/origin/%s' % (branch)).target
                merge_result, _ = repo.merge_analysis(remote_master_id)
                # Up to date, do nothing
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return
                # We can just fastforward
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    repo.checkout_tree(repo.get(remote_master_id))
                    try:
                        master_ref = repo.lookup_reference('refs/heads/%s' % (branch))
                        master_ref.set_target(remote_master_id)
                    except KeyError:
                        repo.create_branch(branch, repo.get(remote_master_id))
                    repo.head.set_target(remote_master_id)
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    raise RuntimeError("Repo cannot be directly merged.")
                else:
                    raise AssertionError('Unknown merge analysis result')

                break

    def compile(self):
        """Compiles the code."""
        args = [self.server.get_dm_path(), self.server.get_dme_path()]

        proc = subprocess.Popen(args, stdout=subprocess.PIPE)

        proc.wait()

    def initialize_directory(self):
        """Creates the game directory as is necessary. To be called !after! the first compiling! And only when you're initing a server!"""
        if not os.path.isfile(self.server.byond_path + "\\baystation12.dmb"):
            raise RuntimeError("{0}: Game code not compiled, cannot link the .dmb.".format(self.name))

        if not os.path.exists(self.server.game_path):
            os.makedirs(self.server.game_path)

        # These are the directories we symlink to the game directory.
        dir_list = ["html", "ingame_manuals", "interface", "lib", "nano", "scripts", "sound", "tools", ".git"]
        # And these are the individual files.
        file_list = ["baystation12.dmb", "baystation12.rsc", "btime.dll", "ByondPOST.dll", "libcurl.dll", "libmysql.dll"]

        for dir in dir_list:
            src = os.path.join(self.server.git_path, dir)
            dst = os.path.join(self.server.game_path, dir)

            os.symlink(src, dst, target_is_directory=True)

        for file in file_list:
            src = os.path.join(self.server.git_path, file)
            dst = os.path.join(self.server.game_path, file)

            os.symlink(src, dst)

        shutil.copytree(os.path.join(self.server.git_path, "config\\example"),
                        os.path.join(self.server.game_path, "config"))
        shutil.copytree(os.path.join(self.server.git_path, "config\\names"),
                        os.path.join(self.server.game_path, "config\\names"))

    def generate_changelogs(self, pr_num, remote_name='origin', ref='refs/heads/master:refs/heads/master'):
        """Generates changelogs and commits them."""

        mypath = os.path.join(self.server.git_path, "html\\changelogs")
        files = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]

        # We have 3 static files. Any more, and we have new changelogs!
        if len(files) > 3:
            args = ["python",
                    self.server.get_changelog_tool(),
                    os.path.join(self.server.git_path, "html\\changelog.html"),
                    os.path.join(self.server.git_path, "html\\changelogs")]

            proc = subprocess.Popen(args, stdout=subprocess.PIPE)

            proc.wait()

            repo = pygit2.Repository(self.server.git_path + "\\.git")

            if repo.head_is_unborn:
                parent = []
            else:
                parent = [repo.head.target]

            repo.index.add("html\\changelogs")
            user = repo.default_signature
            tree = repo.index.write_tree()
            commit = repo.create_commit('HEAD',
                                        user,
                                        user,
                                        'Changelogs for PR {0}'.format(pr_num),
                                        tree,
                                        parent)

            repo.index.write()
            parent = [commit]

            for remote in repo.remotes:
                if remote.name == remote_name:
                    remote.push(ref)
                    break