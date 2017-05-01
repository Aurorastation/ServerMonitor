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
import os
import shutil
import pygit2

## Enum for running the install task.
TASK_INSTALL = 0

## Enum for running the compile task.
TASK_COMPILE = 1

## Enum for running the pull task.
TASK_PULL = 2

## Enum for running the changelog generation task.
TASK_CHANGELOGS = 3

## A generic task runner class. Has all the tasks hardcoded currently.
#
# Exists to run tasks on a given Server::Server object. Can be used to queue a myriad
# of tasks in sequence, and it'll execute them all in one thread.
#
# @sa ServerData::ServerData
class Task(threading.Thread):

    ## A dictionary of task enums -> plain text descriptions.
    _task_descriptions = {
        TASK_INSTALL: "directory initialization",
        TASK_COMPILE: "code compilation",
        TASK_PULL: "pulling new code",
        TASK_CHANGELOGS: "generate and upload changelogs"
    }

    ## The constructor
    #
    # @param self The object pointer.
    # @param _logger A logger object from the main ServerMonitor::ServerMonitor class.
    # @param _tasks A dictionary of %TaskTypes constants which describe the sequence
    # of tasks to be executed.
    # @param _server A ServerData::ServerData object, on which we'll perform the described tasks.
    # @param _pr_num The # of the PR which was merged in reference to this task.
    # Used for changelog generation.
    # @param is_robust A boolean to control whether or not the Task should stop running
    # if it encounters any errors.
    #
    # @throws ValueError In case of a missing argument.
    def __init__(self, _logger, _tasks, _server, _pr_num=0, is_robust=False):
        ## A dictionary of task enums -> Task::Task functions. Used in Task::Task::run.
        self.tasks_dictionary = {
            TASK_INSTALL: self.initialize_directory,
            TASK_COMPILE: self.compile_dme,
            TASK_PULL: self.pull,
            TASK_CHANGELOGS: self.generate_changelogs
        }

        threading.Thread.__init__(self)

        if not _logger:
            raise ValueError("No logger provided.")

        ## A logger objective.
        self.logger = _logger

        if not _tasks:
            raise ValueError("No tasks set sent.")

        ## A list of tasks to be executed.
        self.tasks = _tasks

        if not _server:
            raise ValueError("No tasks set sent.")

        ## A ServerData::ServerData object that we're performing tasks on.
        self.server = _server

        ## Determines whether or not the object keeps executing its tasks after
        # encountering an error.
        self.robust = is_robust

        ## The PR # of the PR which is related to this task. Only concerns CI
        # tasks.
        self.pr_num = _pr_num

    ## Starts the thread.
    #
    # @param self The object pointer.
    def run(self):
        # Attach ourselves to the ServerData object.
        self.server.server_task = self

        # Start processing every task.
        while len(self.tasks):
            task_nr = self.tasks.pop()
            task = self.tasks_dictionary[task_nr]
            try:
                self.logger.info(
                    "SERVER {0}: Task executed: {1}".format(self.server.name,
                                                            self._task_descriptions[task_nr]))
                task()
            except RuntimeError as e:
                self.logger.error(
                    "SERVER {0}: Runtimed while processing task: {1}".format(self.server.name, e))
                if not self.robust:
                    break

        # Detach from the ServerData object.
        self.server.server_task = None

        # Thread will wrap itself up after exiting run.

    ## Pulls new code to local.
    #
    # Will only run pulls in case of fast forwards, as to not generate further
    # issues with local history being out of touch with origin history.
    #
    # @param self The object pointer.
    # @param remote_name The string name of the remote we're pulling from. Defaults
    # to 'origin'.
    # @param branch The string name of the branch we're syncing to in the remote.
    #
    # @throws RuntimeError In case of the merge being a fast forward or an unknown
    # merge analysis result.
    def pull(self):
        remote_name = "origin"
        branch = self.server.git_branch
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
                    raise RuntimeError("Unknown merge analysis result.")

                break

    ## Compiles the codebase.
    #
    # @param self The object pointer.
    #
    # @throws RuntimeError In case of complication failing.
    def compile_dme(self):
        args = [self.server.get_dm_path(), self.server.get_dme_path()]

        proc = subprocess.Popen(args, stdout=subprocess.PIPE)

        out = proc.communicate()[0]

        out_str = out.decode("utf-8")

        if out_str.find("0 errors, 0 warnings") == -1:
            raise RuntimeError("Compilation failed.")

    ## Creates the symlinks for the game directory.
    #
    # Should only be run if a server is initially installed. Can be skipped
    # entirely with a manual installation.
    #
    # @param self The object pointer.
    #
    # @throws RuntimeError In case of the game code not being compiled, the .dmb
    # file cannot be symlinked.
    def initialize_directory(self):
        if not os.path.isfile(self.server.byond_path + "\\baystation12.dmb"):
            raise RuntimeError(
                "{0}: Game code not compiled, cannot link the .dmb.".format(self.name))

        if not os.path.exists(self.server.game_path):
            os.makedirs(self.server.game_path)

        # These are the directories we symlink to the game directory.
        dir_list = ["html", "ingame_manuals", "interface", "lib", "nano",
                    "scripts", "sound", "tools", ".git"]
        # And these are the individual files.
        file_list = ["baystation12.dmb", "baystation12.rsc", "btime.dll",
                     "ByondPOST.dll", "libcurl.dll", "libmysql.dll"]

        for path in dir_list:
            src = os.path.join(self.server.git_path, path)
            dst = os.path.join(self.server.game_path, path)

            os.symlink(src, dst, target_is_directory=True)

        for file in file_list:
            src = os.path.join(self.server.git_path, file)
            dst = os.path.join(self.server.game_path, file)

            os.symlink(src, dst)

        shutil.copytree(os.path.join(self.server.git_path, "config\\example"),
                        os.path.join(self.server.game_path, "config"))
        shutil.copytree(os.path.join(self.server.git_path, "config\\names"),
                        os.path.join(self.server.game_path, "config\\names"))

    ## Generates changelogs, creates a commit for them, and pushes them up.
    #
    # @param self The object pointer.
    # @param pr_num The # of the PR that was merged and we're making changelogs of.
    # @param remote_name The string name of the remote we're targeting.
    # @param ref The reference name we're going to be pushing to. Should be left
    # untouched in most cases.
    def generate_changelogs(self):
        ref = "refs/heads/{0}:refs/heads/{0}".format(self.server.git_branch)
        remote_name = "origin"

        mypath = os.path.join(self.server.git_path, "html\\changelogs")
        files = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]

        # We have 3 static files. Any more, and we have new changelogs!
        if len(files) > 3:
            args = ["python",
                    self.server.get_changelog_tool(),
                    self.server.git_path + "\\html\\changelog.html",
                    self.server.git_path + "\\html\\changelogs"]

            proc = subprocess.Popen(args)

            proc.wait()

            repo = pygit2.Repository(self.server.git_path + "\\.git")

            if repo.head_is_unborn:
                parent = []
            else:
                parent = [repo.head.target]

            repo.index.add("html/changelogs/.all_changelog.yml")
            repo.index.add("html/changelog.html")

            for file in files:
                if file not in [".all_changelog.yml", "changelog.html", "example.yml",
                                "__CHANGELOG_README.txt"]:
                    repo.index.remove("html/changelogs/{0}".format(file))

            user = repo.default_signature
            tree = repo.index.write_tree()
            commit = repo.create_commit('HEAD',
                                        user,
                                        user,
                                        '[CI-Skip] Changelogs for PR {0}'.format(self.pr_num),
                                        tree,
                                        parent)

            repo.index.write()
            parent = [commit]

            for remote in repo.remotes:
                if remote.name == remote_name:
                    remote.push([ref])
                    break
