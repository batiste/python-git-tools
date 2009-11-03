#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from glob import glob
from inspect import getargspec


class NoSuchCommandError(Exception):
    """The command does not exist."""


class ArgumentError(Exception):
    """Error parsing command arguments."""


def shell_quote(arguments):

    def quote(string):
        return "\\'".join("'" + p + "'" for p in string.split("'"))

    return " ".join(map(quote, arguments))


def system(*arguments):
    return os.system(shell_quote(arguments))


def validate_arguments(fun, args, name=None):
    name = name or fun.__name__
    argspec = getargspec(fun)[0]
    if len(args) < len(argspec):
        raise ArgumentError("Missing arguments for %s: %s" % (
                name, ", ".join(argspec[len(args):])))


def with_dir(dirname, fun):
    cwd = os.getcwd()
    try:
        print("--- In directory: %s" % dirname)
        os.chdir(dirname)
        fun()
    finally:
        os.chdir(cwd)


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


def list_repos():
    """List repository urls for all repositories."""
    def _get_repo_url_from_config(filename):
        fh = open(filename, 'r')
        urls = [line.split("=")[1].strip()
                        for line in fh
                            if line.strip().startswith("url")]
        print("\n".join(urls))

    [_get_repo_url_from_config(filename)
        for filename in glob('*/.git/config')]


def find_distmeta_file(app):
    for p in os.listdir(app):
        if p not in ('testproj', 'example'):
            filename = os.path.join(app, p, 'distmeta.py')
            if os.path.exists(filename):
                return filename
            filename = os.path.join(app, p, '__init__.py')
            if os.path.exists(filename):
                return filename


def new_package(repo_name):
    """Bump version and upload new package to chishop."""
    import re

    filename = find_distmeta_file(app)
    if not filename:
        raise RuntimeError("__init__.py or distmeta.py file not found")

    fh = open(filename, 'r')
    content = fh.read()
    fh.close()
    version = r'VERSION = \((\d+), (\d+), (\d+)\)'
    search_result = re.search(version, content)
    if not search_result:
        raise RuntimeError("Regexp %s didn't match anything in file %s" % (
                version, filename))
    minor_version_number = int(search_result.group(3)) + 1
    new_version = 'VERSION = (%d, %d, %d)' % (
        int(search_result.group(1)),
        int(search_result.group(2)),
        minor_version_number
    )
    new_content = re.sub(version, new_version, content)
    fh = open(filename, 'w')
    fh.write(new_content)
    fh.close()
    print("Version number bumped; commiting changes")
    def commit_and_tag():
        system("git", "commit", "-a", "-m", "New version %s" % (
            new_version.lower()))
        system("git", "tag", new_version.lower().replace(' ', ''))
    with_dir(app, commit_and_tag)

    print("Uploading new package")
    def upload_package():
        system("python", "setup.py", "sdist", "upload", "-r", "chishop")
    with_dir(app, upload_package)


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


def help(command_name):
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
