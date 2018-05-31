#!/usr/bin/python
# -*- coding: utf-8 -*-

import pychrome
import requests
import os
import platform
import sys
import time
import operator
import glob
import subprocess
import six
import psutil
from argparse import ArgumentParser
from sys import platform as _platform
from colorama import init as colorama_init, Fore, Style




SLACK_PLUGIN_CODE2 = """
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', function() {
        jQuery('body').bind('DOMSubtreeModified', function() {
            jQuery('.ql-editor, .c-message__body').attr('dir', 'auto').css('text-align', 'left');
        });
    }, false);

    jQuery('body').bind('DOMSubtreeModified', function() {
        jQuery('.ql-editor, .c-message__body').attr('dir', 'auto').css('text-align', 'left');
    });
}
"""

SLACK_PLUGIN_CODE = b"""
document.getElementById(\'msg_input\').dir = \'auto\';

function elementShouldBeRTL(element) {
    return /[\xd7\x90-\xd7\xaa]/.test(element.innerHTML);
}

function alreadyApplied(element) {
    return element.children.length == 1 && (
            element.children[0].tagName == "P" || element.children[0].tagName == "p");
}

function applyTo(element) {
    element.innerHTML = \'<p style="direction: rtl; text-align: left; margin: 0;">\' + element.innerHTML + \'</p>\';
    for (var i in element.children[0].children) {
        var child = element.children[0].children[i];
        if (!(child.style instanceof CSSStyleDeclaration))
            continue;
        child.style.textAlign = "initial";
    }
}

function setDirections() {
    var contents = document.getElementsByClassName(\'c-message__body\');
    for (var i in contents) {
        var element = contents[i];
        if (!elementShouldBeRTL(element))
            continue;
        if (alreadyApplied(element))
            continue;
        applyTo(element);
    }
}

function domModified() {
    document.body.removeEventListener(\'DOMSubtreeModified\', domModified);
    setTimeout(function() { // debouce modifications
        setDirections();
        document.body.addEventListener(\'DOMSubtreeModified\', domModified);
    }, 500);
}

document.body.addEventListener("DOMSubtreeModified", domModified);
""".decode('utf-8')
SLACK_CODES = {"old": SLACK_PLUGIN_CODE, "new" : SLACK_PLUGIN_CODE2} 

SCRIPT_HOTKEYS_F12_DEVTOOLS_F5_REFRESH = """document.addEventListener("keydown", function (e) {
    if (e.which === 123) {
        //F12
        require("electron").remote.BrowserWindow.getFocusedWindow().webContents.toggleDevTools();
        var nodeConsole = require('console');
        var myConsole = new nodeConsole.Console(process.stdout, process.stderr);
        myConsole.log('Injected code');
    } else if (e.which === 116) {
        //F5
        location.reload();
    }
});"""

def find_app_local_path(app):
    app_root = os.path.join(os.environ['LOCALAPPDATA'],app)
    if os.path.isdir(app_root): # Local install mode
        apps = os.path.join(app_root, "app-")
        candidates = [x for x in glob.glob(os.path.join(apps + "*")) if os.path.isdir(x)]

        versions = [[int(y) for y in x.rsplit('-',1)[-1].split('.')] for x in candidates]
        max_index, max_value = max(enumerate(versions), key=operator.itemgetter(1))
        return candidates[max_index]

def find_app_store_path(app):
    try:
        app_root = subprocess.check_output(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", '(Get-AppxPackage | where {$_.Name -match \"'+app+'\"} ).InstallLocation'])
        app_root = app_root.decode('utf-8').strip()
        if not os.path.isdir(app_root): return None
        return os.path.join(app_root, app)
    except subprocess.CalledProcessError:
        pass



def find_app_path(location, app):
    if _platform == 'darwin':
        if location == "auto":
            p = '/Applications/' + app + '.app/Contents/MacOS'
        else: 
            p = location
        if not os.path.isdir(p) or not os.path.isfile(os.path.join(p, app)):
            raise Exception("%s is not a valid slack directory" % p)
        return os.path.join(p, app)

    elif _platform == 'win32' or _platform == 'win64':
        if location == "store":
            p = find_app_store_path(app)
        elif location == "local":
            p = find_app_local_path(app)
        elif location == "auto":
            p = find_app_local_path(app)
            if p is None: p = find_app_store_path(app)
        else:
            p = location

        if p is None:
            raise Exception("Cannot find a valid {} path in {}".format(app, location))
        if not os.path.isdir(p) or not os.path.isfile(os.path.join(p, app + ".exe")):
            raise Exception("{} find a valid {} directory".format(p, app))
        return os.path.join(p, app + ".exe")

    elif _platform.startswith('linux'):
        p = None
        if location == "auto":
            p = '/Applications/' + app + '.app/Contents/MacOS'
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                p = os.path.join(path, app)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    break
        if p is None:
            raise Exception("Could not find %s in path" % app)

        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
        else:
            raise Exception("{} find a valid {} path".format(p, app))
    else:
        raise Exception ("%s is not a supported platform" % _platfom)




def run_app(path, port):
    DETACHED_PROCESS = 0x00000008

    if _platform == 'darwin':
        subprocess.Popen([path + ' --remote-debugging-port=%d' % port], shell=True)

    elif _platform == 'win32' or _platform == 'win64':
        subprocess.Popen([path, "--remote-debugging-port=%d" % port], creationflags=DETACHED_PROCESS, shell=True)

    elif _platform.startswith('linux'):
        subprocess.Popen([path + " --remote-debugging-port=%d" % port], shell=False)

    else:
        raise Exception("%s is not a supported platform" % _platfom)



def inject_script(tab, script):
    r = tab.Runtime.evaluate(expression = script)

def kill_existing_app(app):
    for i in psutil.process_iter():               
        try:
            name = os.path.splitext(i.name())[0]
            if name.lower() == app:
                six.print_("Killing %s process Pid:%s%s%s." % (app, Fore.GREEN, i.pid, Style.RESET_ALL), end='\n', flush=True)
                try:
                    i.terminate()
                except:
                    pass
        except psutil.AccessDenied:
            pass



def get_browser_connection(timeout, port, app):
    try:
        url = "http://127.0.0.1:%d" % port
        for i in range(timeout):
            try:
                browser = pychrome.Browser(url)
                browser.list_tab()
                return (browser, timeout - i)
            except requests.exceptions.ConnectionError:
                pass
            except: 
                six.print_(sys.exc_info()[0])
            six.print_("Establishing connection with %s. Timeout %s%s%s seconds." % (app, Fore.GREEN, timeout - i, Style.RESET_ALL), end='\r', flush=True)
            time.sleep(1)
        raise IOError("Can't connect to {} at {}".format(app, url))
    finally:
        six.print_("\033[K" , end='\r', flush=True)


def find_slack_tab(browser, div, timeout):
    try: 
        for i in range(timeout):
            for tab in browser.list_tab():
                tab.start()
                res = tab.Runtime.evaluate(expression = "document.getElementById('%s')" % div)
                if res.get('result',{}).get('objectId',None) is not None: # Found element with that name, screen is loaded
                    return (tab, timeout - i)
                tab.stop()
            six.print_("Waiting for target window to load. Timeout %s%s%s seconds." % (Fore.GREEN, timeout - i , Style.RESET_ALL), end='\r', flush=True)
            time.sleep(1)
        raise IOError("Couldn't find slack window")
    finally:
        six.print_("\033[K" , end='\r', flush=True)

def update_slack_plugin():
    url = r'https://raw.githubusercontent.com/shlomimatichin/slack-hebrew/master/source/slack-hebrew.js'
    six.print_("Downloading slack plugin from %s%s%s." % (Fore.GREEN, url, Style.RESET_ALL), end='\n', flush=True)
    r = requets.get(url)
    if r.status_code == 200:
        return r.content.decode('utf-8')
    else:
        six.print_("Couldn't download plugin. Error was %s%s%s." % (Fore.RED, r.status_code , Style.RESET_ALL), end='\n', flush=True)
        raise Exception("Can't download")


def main():
    parser = ArgumentParser(description=""" 
    Inject hebrew support plugin into Slack's tab inside an electron app.

    This program injects the Chrome's hebrew_slack plugin into any electron (desktop) version of the slack app
    """)
    parser.add_argument("-l", "--location",
                      action="store", dest="location", default="auto",
                      help="Location of application to run, or auto, local (Windows only), store (Windows only) [default: auto]")

    parser.add_argument("-a", "--app",
                      default='slack',
                      help="application to launch and inject code into [default: %(default)s]")

    parser.add_argument("-t", "--time",
                      default=15,
                      type=int,
                      help="Wait for application to load for timeout seconds before injecting [default: %(default)d]")

    parser.add_argument("-d","--debug",
                      default=False,
                      action="store_true",
                      help="Additionally attempt to inject dev tools code [default: %(default)r]")

    parser.add_argument("-p", "--port",
                      type=int,
                      default=9222,
                      help="Port on which application is listening to debug interface [default: %(default)d]")

    parser.add_argument("--no-kill", dest="kill", action='store_false',
                        help="Do not attempt to kill original application before starting",
                        default=True
                        )

    parser.add_argument("--no-start", dest="start", action='store_false',
                        help="Do not attempt to start application (assume already running)",
                        default=True
                        )

    parser.add_argument("-m", "--method", dest="method", action='store', choices = SLACK_CODES.keys(),
                        help="Which script to inject to Slack [default: $(default)d]",
                        default="old"
                        )

    update_parser = parser.add_mutually_exclusive_group(required=False)
    update_parser.add_argument('--update', dest='update', action='store_true', 
            help="Update the slack plugin from slack_hebrew github page"
            )
    update_parser.add_argument('--no-update', dest='update', action='store_false',
            help="Do not update the slack plugin"
            )
    parser.set_defaults(update=False)

    # parse args
    args  = parser.parse_args()

    app_path = find_app_path(args.location, args.app)

    colorama_init(autoreset=True)
    six.print_(args.app)
    if args.update:
        if args.method != "old":
            six.print_("Update only supported with method %sold%s" % (Fore.GREEN, Style.RESET_ALL))
            sys.exit(-1)
        try:
            global SLACK_PLUGIN_CODE
            SLACK_PLUGIN_CODE = update_slack_plugin()
        except:
            pass #continue with existing script

    if args.kill:
        kill_existing_app(args.app)


    if args.start:
        six.print_("Running %s from %s %s." % (args.app, Fore.GREEN, app_path))
        run_app(app_path,args.port)

    six.print_("Connecting to %s." % args.app)
    browser, args.time = get_browser_connection(args.time, args.port, args.app)

    six.print_("Looking for the slack windows.")
    tab, args.time = find_slack_tab(browser, 'msg_input', args.time)
    time.sleep(min(1, args.time)) #Giving it an extra second

    six.print_("Injecting code into slack. Method %s%s%s." % (Fore.GREEN, args.method, Style.RESET_ALL))
    inject_script(tab, SLACK_CODES[args.method])
    if args.debug:
        inject_script(tab, SCRIPT_HOTKEYS_F12_DEVTOOLS_F5_REFRESH)

    try: 
        tab.stop()
    except:
        pass

    six.print_("Done")


if __name__ == "__main__":
    main()
