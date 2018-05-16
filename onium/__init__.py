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

def find_slack_local_path():
    slack_root = os.path.join(os.environ['LOCALAPPDATA'],'slack')
    if os.path.isdir(slack_root): # Local install mode
        apps = os.path.join(slack_root, "app-")
        candidates = [x for x in glob.glob(os.path.join(apps + "*")) if os.path.isdir(x)]

        versions = [[int(y) for y in x.rsplit('-',1)[-1].split('.')] for x in candidates]
        max_index, max_value = max(enumerate(versions), key=operator.itemgetter(1))
        return candidates[max_index]

def find_slack_store_path():
    try:
        slack_root = subprocess.check_output(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", '(Get-AppxPackage | where {$_.Name -match \"slack\"} ).InstallLocation'])
        slack_root = slack_root.decode('utf-8').strip()
        if not os.path.isdir(slack_root): return None
        return os.path.join(slack_root, "app")
    except subprocess.CalledProcessError:
        pass



def find_slack_path(version):
    if _platform == 'darwin':
        p = '/Applications/Slack.app/Contents/MacOS'
        if not os.path.isdir(p) or not os.path.isfile(os.path.join(p,"slack")):
            raise Exception("%s is not a valid slack directory" % p)
        return p

    elif _platform == 'win32' or _platform == 'win64':
        if version == "store":
            p = find_slack_store_path()
        elif version == "local":
            p = find_slack_local_path()
        elif version == "auto":
            p = find_slack_local_path()
            if p is None: return find_slack_store_path()
        else:
            p = version

        if p is None:
            raise Exception("Cannot find a valid slack path in %s" % version)
        if not os.path.isdir(p) or not os.path.isfile(os.path.join(p,"slack.exe")):
            raise Exception("%s is not a valid slack directory" % p)
        return p

def run_slack(path, port):
    DETACHED_PROCESS = 0x00000008

    if _platform == 'darwin':
        subprocess.Popen([os.path.join('/Applications/Slack.app/Contents/MacOS/slack --remote-debugging-port=%d' % port)], shell=True)
    elif _platform == 'win32' or _platform == 'win64':
        subprocess.Popen([os.path.join(path, 'slack.exe'), "--remote-debugging-port=%d" % port], creationflags=DETACHED_PROCESS, shell=True)



def inject_script(tab, script):
    tab.Runtime.evaluate(expression = script)

def kill_existing_slack():
    for i in psutil.process_iter():               
        name = os.path.splitext(i.name())[0]         
        if name.lower() == "slack":               
            six.print_("Killing slack process Pid:%s%s%s." % (Fore.GREEN, i.pid, Style.RESET_ALL), end='\n', flush=True)
            try:
                i.terminate()                         
            except:
                pass



def get_browser_connection(timeout, port):
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
            six.print_("Establishing connection with slack. Timeout %s%s%s seconds." % (Fore.GREEN, timeout - i, Style.RESET_ALL), end='\r', flush=True)
            time.sleep(1)
        raise ConnectionError("Can't connect to slack at %s" % url)
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
        raise ConnectionError("Couldn't find slack window")
    finally:
        six.print_("\033[K" , end='\r', flush=True)




def main():
    parser = ArgumentParser(description=""" 
    Inject hebrew support plugin into Slack's electron app.

    This program injects the Chrome's hebrew_slack plugin into the electron (desktop) version of the slack app
    """)
    parser.add_argument("-l", "--location",
                      action="store", dest="location", default="auto",
                      help="Location of slack to run, or local, store, auto [default: auto]")

    parser.add_argument("-t", "--time",
                      default=15,
                      type=int,
                      help="Wait for Slack to load for timeout seconds before injecting [default: %(default)d]")

    parser.add_argument("-d","--debug", 
                      default=False,
                      action="store_true",
                      help="Additionally attempt to inject dev tools code [default: %(default)r]")

    parser.add_argument("-p", "--port",
                      type=int,
                      default=9222,
                      help="Port on which Slack is listening to debug interface [default: %(default)d]")

    # parse args
    args  = parser.parse_args()

    slack_path = find_slack_path(args.location)

    colorama_init(autoreset=True)
    kill_existing_slack()


    six.print_("Running slack from %s %s" % (Fore.GREEN, slack_path))
    run_slack(slack_path,args.port)

    six.print_("Giving Slack time to load. ")
    browser, args.time = get_browser_connection(args.time, args.port)

    six.print_("Looking for the slack windows. ")
    tab, args.time = find_slack_tab(browser, 'msg_input', args.time)
    time.sleep(min(1, args.time)) #Giving it an extra second

    inject_script(tab, SLACK_PLUGIN_CODE)
    if args.debug:
        inject_script(tab, SCRIPT_HOTKEYS_F12_DEVTOOLS_F5_REFRESH)

    try: 
        tab.stop()
    except:
        pass

    six.print_("Done")


if __name__ == "__main__":
    main()
