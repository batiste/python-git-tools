#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import sys
import os
syntax = """Syntax: python git.py [commit|push|pull|status|new_package|list_repos] \"[your message|package name]\""""

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print syntax
    exit(0)

if sys.argv[1] not in ("commit", "push", "pull", "status", "diff", "list_repos", "new_package"):
    print syntax

dir_msg = "--- In directory : %s"

if sys.argv[1] == 'commit':
    if len(sys.argv) < 3:
        print "You need to provide a message for your commit"
        print syntax
        exit(0)
    commit_cmd = "cd %s; git commit -a -m \"%s\"; cd .. "
    for dirname in glob.glob('*'):
        print dir_msg % dirname
        os.system(commit_cmd % (dirname, sys.argv[2]))

if sys.argv[1] == 'pull':
    commit_cmd = "cd %s; git pull; cd .. "
    for dirname in glob.glob('*'):
        print dir_msg % dirname
        os.system(commit_cmd % (dirname))

if sys.argv[1] == 'push':
    commit_cmd = "cd %s; git push; cd .. "
    for dirname in glob.glob('*'):
        print dir_msg % dirname
        os.system(commit_cmd % (dirname))

if sys.argv[1] == 'status':
    commit_cmd = "cd %s; git status; cd .. "
    for dirname in glob.glob('*'):
        print dir_msg % dirname
        os.system(commit_cmd % (dirname))


if sys.argv[1] == 'diff':
    commit_cmd = "cd %s; git diff; cd .. "
    for dirname in glob.glob('*'):
        if dirname.find('.') == -1:
            print dir_msg % dirname
            os.system(commit_cmd % (dirname))

if sys.argv[1] == 'list_repos':
    for dirname in glob.glob('*'):
        filename = os.path.join(dirname, '.git/config')
        if os.path.exists(filename):
            fh = open(filename, 'r')
            for line in fh:
                if line.strip().startswith('url'):
                    print line.split('=')[1].strip()

if sys.argv[1] == 'new_package':
    import re
    app = sys.argv[2]
    found = False
    for p in glob.os.listdir(app):
        filename = os.path.join(app, p, 'distmeta.py')
        if os.path.exists(filename):
            found = filename
            break
        filename = os.path.join(app, p, '__init__.py')
        if os.path.exists(filename):
            found = filename
            break

    if not found:
        print "__init__.py or distmeta.py file not found"
        exit(0)

    fh = open(filename, 'r')
    content = fh.read()
    fh.close()
    import re
    version = r'VERSION = \((\d+), (\d+), (\d+)\)'
    search_result = re.search(version, content)
    if not search_result:
        print "Regexp %s didn't match anything in file %s" % (version, filename)
        exit(0)
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
    print "Version number increased; commit changes"
    commit_cmd = "cd %s; git commit -a -m \"New %s\"; git tag \"%s\"; git push; cd .." % (
        app, new_version.lower(), new_version.lower().replace(' ', ''),
    )
    os.system(commit_cmd)
    print "Upload the new package"
    upload_cmd = "cd %s; python setup.py sdist upload -r chishop; cd .." % (app)
    os.system(upload_cmd)
