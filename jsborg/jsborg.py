#!/usr/bin/env python
"""
jsborg is a sprocketize-compatible javascript concatation script.
it explicitly ignores ERB style <%= %> tags in the code because
they collide with most js templating solutions out there.
"""
### TODO:
### - add wildcard / handling of directories support for "require"
### - if a sub module is changed, change only those up the hierarchy which depend on the module
import sys
import re
import os
import time

ROOT_PATHS = []

FILE_SEPARATOR = "/"
FILE_ENDING    = ".js"

DEFINES = {}

# directive regex
DIRECTIVE_START = re.compile("//=")
COMMAND = re.compile("\w+")

RELATIVE_REQUIRE_ARGS = re.compile(r'"([^"]*)"')
ROOT_REQUIRE_ARGS     = re.compile(r'<([^>]*)>')
REQUIRE_IF_PART       = re.compile(r'if\s+(\w+)')

def parseDefines(defines):
    defines = defines or []
    global DEFINES
    # FIXME: just assume boolean variables for now
    for d in defines:
        DEFINES[d] = True

# we want to track the already "required" files
REQUIRE_LOG = {} # fullpath -> True

def require_handler(context, content):
    # find the first newline. ignore everything after that
    try:
        newline_match = re.search("\n", content)
        newline = newline_match.start()
    except:
        raise Exception("No newline found")
    line = content[:newline].strip()
    # check if there's an if part
    ifmatch = REQUIRE_IF_PART.search(line)
    if ifmatch:
        var = ifmatch.group(1)
        # FIXME: only boolean check for now
        if not var in DEFINES or not DEFINES[var]:
            return len(line)+1, "" # bail out, because var is not set or it's False
    # continue with main file parsing
    # check whether we're dealing with relative or absolute file inclusion
    fullpath = None
    relative_match = RELATIVE_REQUIRE_ARGS.search(line)
    if relative_match:
        args = relative_match.group(1)
        fullpath = [context["relative_path"]] + args.split(FILE_SEPARATOR)
        fullpath = os.path.join(*fullpath) + FILE_ENDING
    else:
        absolute_match = ROOT_REQUIRE_ARGS.search(line)
        if absolute_match:
            args = absolute_match.group(1)
            fullpath = [context["root"]] + args.split(FILE_SEPARATOR)
            fullpath = os.path.join(*fullpath) + FILE_ENDING
    if not fullpath:
        print "line:", line
        print "start:", line[0]
        print "end:", line[-1]
        raise Exception("require action doesn't know how to handle: %s" % line)
    REQUIRE_LOG.setdefault(fullpath, False)
    if REQUIRE_LOG[fullpath]:
        return len(line)+1, ""
    else:
        REQUIRE_LOG[fullpath] = True
    f = open(os.path.join(fullpath), "r")
    content = f.read()
    f.close()

    newcontent = replaceDirectives(context["root"],
                                   fullpath,
                                   content)
    return len(line)+1, newcontent

def if_handler(context, content):
    return

ACTION_HANDLERS = {
    "require" : require_handler,
}

def replaceDirectives(root, filename, content):
    global ACTION_HANDLERS
    out = []
    context = dict(root=root, relative_path=os.path.dirname(filename))
    # match any directives
    content_start = 0
    lastindex = 0
    for directive_match in DIRECTIVE_START.finditer(content):
        s,e = directive_match.start(),directive_match.end()
        action_match = COMMAND.search(content[e:])
        contentsofar = content[content_start:s]
        content_start = e
        out.append(contentsofar)
        action = content[e:][action_match.start():action_match.end()]
        if not action in ACTION_HANDLERS:
            print "undefined action: %s" % action
            continue
        # the number of chars used to consume the action, this is our offset
        # for our real content
        arg_offset, action_result = ACTION_HANDLERS[action](
            context,
            content[e+action_match.end():]
        )
        out.append(action_result)
        content_start += action_match.end() + arg_offset
        lastindex = e+action_match.end()+arg_offset
    # add remaining content
    out.append(content[lastindex:])
    return "".join(out)

def jsborg(root, filename, outname, tostdout=False):
    global DEFINES, ROOT_PATHS, REQUIRE_LOG
    ROOT_PATHS.append(root)

    # reset global variables
    DEFINES = {}
    REQUIRE_LOG = {}

    # read in the content of the main file
    f = open(filename, "r")
    content = f.read()
    f.close()

    out = replaceDirectives(root, filename, content)

    if tostdout:
        print out
    else:
        f = open(outname, "w")
        f.write(out)
        f.close()

change_table = {}

def watch(base_root, filename, outname, callback):
    while 1:
        for root, dirs, file in os.walk(base_root):
            for f in file:
                try:
                    filetype = f.split(".")[1].lower()
                except:
                    continue
                if filetype == "js":
                    fullpath = os.path.join(root, f)
                    cur_time = os.stat(fullpath).st_mtime
                    if not fullpath in change_table:
                        change_table[fullpath] = os.stat(fullpath).st_mtime
                    if change_table[fullpath] != cur_time:
                        change_table[fullpath] = os.stat(fullpath).st_mtime
                        print "jsborg: change detected in '%s'. compiling to '%s'..." % (fullpath, outname)
                        callback(base_root, filename, outname)
        time.sleep(1)

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-I", "--include", action="append",      dest="include")
    parser.add_option("-D", "--define",  action="append",      dest="defines")
    parser.add_option("-W", "--watch",   action="store_true",  dest="watch",    default=False)
    parser.add_option("-S", "--stdout",  action="store_true", dest="tostdout", default=False)

    options, args = parser.parse_args()

    if options.tostdout:
        if len(args) < 2:
            print "Usage: jsborg.py <root directory> filename"
            sys.exit(0)
    else:
        if len(args) < 3:
            print "Usage: jsborg.py <root directory> filename outname"
            sys.exit(0)
    parseDefines(options.defines)
    if options.tostdout:
        jsborg(args[0], args[1], None, tostdout=options.tostdout)
        sys.exit(0)
    if not options.watch:
        jsborg(args[0], args[1], args[2], tostdout=options.tostdout)
    else:
        watch(args[0], args[1], args[2], jsborg)
