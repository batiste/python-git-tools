#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from glob import glob
from inspect import getargspec
from subprocess import Popen, PIPE

class NoSuchCommandError(Exception):
    """The command does not exist."""


class ArgumentError(Exception):
    """Error parsing command arguments."""


def shell_quote(arguments):

    def quote(string):
        return "\\'".join("'" + p + "'" for p in string.split("'"))

    return " ".join(map(quote, arguments))


def system(*arguments):
    proc = Popen(arguments, stdout=PIPE, stderr=PIPE)
    return_code = proc.wait()
    if return_code == 0:
        return proc.stdout.read()
    else:
        raise RuntimeError('System command returned an error: ' % str(arguments))



def validate_arguments(fun, args, name=None):
    name = name or fun.__name__
    argspec = getargspec(fun)[0]
    defaults = getargspec(fun)[3]
    if len(args) < (len(argspec) - len(defaults)):
        raise ArgumentError("Missing arguments for %s: %s" % (
                name, ", ".join(argspec[len(args):])))


def with_dir(dirname, fun):
    cwd = os.getcwd()
    result = None
    try:
        print("--- In directory: %s" % dirname)
        os.chdir(dirname)
        result = fun()
    finally:
        os.chdir(cwd)
    return result


def with_all_dirs(fun):
    [with_dir(dirname, lambda: fun(dirname))
        for dirname in glob("*")
            if os.path.isdir(dirname)]


def with_repos(*shell_eval):
    """Execute an arbitrary shell command for all reposistories."""
    with_all_dirs(lambda dirname: system(*shell_eval))


def create_simple_git_command(command):
    def _git_x():
        with_all_dirs(lambda dirname: system("git", command))
    _git_x.__name__ = command
    _git_x.__doc__ = "Run git %s for all repositories" % command
    return _git_x


def get_repo_url_from_config(filename):
    fh = open(filename, 'r')
    urls = [line.split("=")[1].strip()
                    for line in fh
                        if line.strip().startswith("url")]
    return urls

def list_repos():
    """List repository urls for all repositories."""
    for filename in glob('*/.git/config'):
        print("\n".join(get_repo_url_from_config(filename)))



def find_distmeta_files(app):
    files = []
    for p in os.listdir(app):
        if p not in ('testproj', 'example', 'tests', 'test'):
            filename = os.path.join(app, p, 'distmeta.py')
            if os.path.exists(filename):
                files.append(filename)
            filename = os.path.join(app, p, '__init__.py')
            if os.path.exists(filename):
                files.append(filename)
    return files


def new_package(repo_name, server='chishop'):
    """Bump version and upload new package to chishop."""
    
    import re
    version = r'VERSION = \((\d+), (\d+), (\d+)\)'
    
    filenames = find_distmeta_files(repo_name)
    if not filenames:
        raise RuntimeError("__init__.py or distmeta.py files not found")

    filename = None
    for filename in filenames:
        fh = open(filename, 'r')
        content = fh.read()
        fh.close()
        search_result = re.search(version, content)
        if search_result:
            break
    else:
        raise RuntimeError("Regexp %s didn't match anything in files %s" % (
                version, str(filenames)))

    minor_version_number = int(search_result.group(3)) + 1
    new_version = 'VERSION = (%d, %d, %d)' % (
        int(search_result.group(1)),
        int(search_result.group(2)),
        minor_version_number
    )
    tag_name = 'v%d.%d.%d' % (
        int(search_result.group(1)),
        int(search_result.group(2)),
        minor_version_number
    )
    new_content = re.sub(version, new_version, content)
    fh = open(filename, 'w')
    fh.write(new_content)
    fh.close()
    print("Version number bumped; commiting changes (%s)" % tag_name)
    def commit_and_tag():
        system("git", "commit", "-a", "-m", "New version %s" % (
            new_version.lower()))
        system("git", "push")
        system("git", "tag", tag_name)
        system("git", "push", '--tags')
    with_dir(repo_name, commit_and_tag)

    urls = get_repo_url_from_config(os.path.join(repo_name, '.git/config'))
    def clone_package():
        print("Checkout the repository in /tmp/")
        system("git", "clone", urls[0], 'new_package')
        def upload_package():
            print("Uploading new package to %s" % server)
            system("python", "setup.py", "sdist", "upload", "-r", server)
        with_dir("new_package", upload_package)
        system("rm", "-Rf", "new_package")
    with_dir("/tmp/", clone_package)
    print("Done.")

def commit(message):
    """Commit changes in all repositories."""
    commit_cmd = """git commit -a -m "%s" """
    with_all_dirs(lambda dirname: os.system(commit_cmd % message))


commands = {
    "commit": commit,
    "pull": create_simple_git_command("pull"),
    "push": create_simple_git_command("push"),
    "status": create_simple_git_command("status"),
    "diff": create_simple_git_command("diff"),
    "with_repos": with_repos,
    "list_repos": list_repos,
    "new_package": new_package,
}

def usage(syntax):
    sys.stderr.write(syntax + "\n")
    exit(0)


def help(command_name=None):
    if command_name:
        command = commands[command_name]
        sys.stderr.write("Usage: %s %s\n\n%s\n" % (
            command_name,
            " ".join("<%s>" % arg
                        for arg in getargspec(command)[0]),
            command.__doc__))
commands["help"] = help


def main(*args):
    syntax = """Syntax: %s [%s] [command arguments]""" % (
        os.path.basename(args[0]), "|".join(commands.keys()))
    len(args) < 2 and usage(syntax)

    program_name, command_name = args[:2]
    arguments = args[2:]

    try:
        fun = commands[command_name]
    except KeyError:
        raise NoSuchCommandError("No such command: %s" % command_name)

    validate_arguments(fun, arguments, name=command_name)

    result = fun(*arguments)


if __name__ == "__main__":
    main(*sys.argv)
