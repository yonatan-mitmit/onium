#!/usr/bin/python
# -*- coding: utf-8 -*-

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
import json
import shutil
import posixpath
from argparse import ArgumentParser,_SubParsersAction
from sys import platform as _platform
from colorama import init as colorama_init, Fore, Style
from .asar import Asar
from string import Template


SLACK_PLUGIN_CODE = """
const { app } = require('electron')
const { BrowserWindow } = require('electron')

payload = `
function changeStyle() { 
    document.getElementsByTagName('body')[0].removeEventListener('DOMSubtreeModified', changeStyle)

    // MITMIT The following, per element edit is disabled as we now edit the CSS directly, and do so only once.

    // var classes = ['ql-editor', 'c-message__body', 'message_body', 'c-message_attachment__text', 'msg_inline_attachment_row', 'c-mrkdwn__pre', 'p-rich_text_section', 'p-rich_text_block'];

    // classes.forEach((cls) => {
    //   for (let item of document.getElementsByClassName(cls))
    //   { 
    //     item.setAttribute('dir','auto');
    //     item.style.textAlign = 'start';
    //   }
    // });
    
    var classes = ['c-message_kit__text'];
    classes.forEach((cls) => {
       for (let item of document.getElementsByClassName(cls))
       { 
         item.setAttribute('dir','auto');
       }
    });


    // var classes = ['c-message_kit__text'];

    // classes.forEach((cls) => {
    //   for (let item of document.getElementsByClassName(cls))
    //   { 
    //     n = document.createElement('div')
    //     //n.innerHTML = item.innerHTML;
    //     n.setAttribute('dir','auto');
    //     n.style.textAlign = 'start';
    //     item.replaceWith(n)
    //     n.appendChild(item)
    //   }
    // });

    // classes = ['c-message__edited_label'];
    //
    // classes.forEach((cls) => {
    //   for (let item of document.getElementsByClassName(cls))
    //   { 
    //     item.style.display = 'inline-block';
    //   }
    // });

    // for (let sheet of document.styleSheets) {
    //   for (let rule of sheet.cssRules) {
    //       if (rule.selectorText != null && rule.selectorText.indexOf('.p-rich_text_list li::before') != -1) {
    //           rule.style['margin-left'] = 0
    //       }
    //   }
    // }


    document.getElementsByTagName('body')[0].addEventListener('DOMSubtreeModified', changeStyle)
}

function editStyle(selector, style, value) {
  for (let sheet of document.styleSheets) {
    for (let rule of sheet.cssRules) {
      if (rule.selectorText != null && rule.selectorText.indexOf(selector) != -1) {
          rule.style[style] = value;
      }
    }
  }
}

function addStyle() {
	// Create the <style> tag
	var style = document.createElement("style");

	// Add a media (and/or media query) here if you'd like!
	// style.setAttribute("media", "screen")
	// style.setAttribute("media", "only screen and (max-width : 1024px)")

	// WebKit hack :(
	style.appendChild(document.createTextNode(""));

	// Add the <style> element to the page
	document.head.appendChild(style);

	return style.sheet;
}

function doIt() {
  sheet = addStyle()
  sheet.insertRule('.p-rich_text_list li::before {margin-left : 0 ; } ');
  sheet.insertRule('.p-rich_text_list li  {margin-left : 0 ; } ');

  sheet.insertRule('.ql-editor ol > li::before { margin-left : 0; }' );
  sheet.insertRule('.ql-editor ol > li { margin-left : 0; }');
  sheet.insertRule('.c-texty_input .ql-editor ol > li::before { margin-left : 0; }' );
  sheet.insertRule('.c-texty_input .ql-editor ol > li { margin-left : 0; }');
  sheet.insertRule('.c-texty_input .ql-editor ul:not([data-checked])>li { margin-left: 0; }');

  sheet.insertRule('.ql-editor ul > li::before { margin-left : 0; }' );
  sheet.insertRule('.ql-editor ul > li { margin-left : 0; }');
  sheet.insertRule('.c-texty_input .ql-editor ul > li::before { margin-left : 0; }' );
  sheet.insertRule('.c-texty_input .ql-editor ul > li { margin-left : 0; }');
  sheet.insertRule('.c-texty_input_unstyled__container .ql-editor ol>li:before, .c-texty_input_unstyled__container .ql-editor ul>li:before { margin-left : 0; }');



  var classes = ['.ql-editor', '.c-message__body', '.message_body', '.c-message_attachment__text', '.msg_inline_attachment_row', '.c-mrkdwn__pre', '.p-rich_text_section', '.p-rich_text_block'];

  classes.forEach((cls) => {
    sheet.insertRule(cls + ' { text-align : start; direction : auto; }');
  });

  classes = ['.c-message__edited_label'];
  classes.forEach((cls) => {
    sheet.insertRule(cls + ' { display: block; }');
  });

  classes = ['.c-message_kit__text'];
  classes.forEach((cls) => {
    sheet.insertRule(cls + ' { text-align : start; direction : auto; display : block; }');
  });

  document.getElementsByTagName('body')[0].addEventListener('DOMSubtreeModified', changeStyle)
}

doIt();
`
$debug_script

app.on('web-contents-created', (evt, webContents) => {
     webContents.on('did-finish-load', function() {
        webContents.executeJavaScript(payload); 
     });
});
"""

SLACK_DEBUGGER_CODE = """
app.commandLine.appendSwitch('remote-debugging-port', '9222');
"""


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
            p = '/Applications/' + app + '.app'
        else: 
            p = location
        if not os.path.isdir(p) or not os.path.isfile(os.path.join(p, "Contents/Macos/Slack")):
            raise Exception("%s is not a valid slack directory" % p)
        asar_path = os.path.join(p,"resources") 
        if len([name for name in os.listdir(p)]) == 1:
                asar_path = '/Applications/' + app + '.app/Contents/Resources' 
        return p, asar_path

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
        return os.path.join(p, app + ".exe"), os.path.join(p,"resources")

    elif _platform.startswith('linux'):
        p = None
        if location == "auto":
            for path in os.environ["PATH"].split(os.pathsep):
                p = os.path.join(path, app)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    p=os.path.realpath(p)
                    path=os.path.dirname(p)
                    break
        else:
            p = location
            path = os.path.split(location)

        if p is None:
            raise Exception("Could not find %s in path" % app)

        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p, os.path.join(path, "resources")
        else:
            raise Exception("{} find a valid {} path".format(p, app))
    else:
        raise Exception ("%s is not a supported platform" % _platfom)


def run_app(path, param):
    DETACHED_PROCESS = 0x00000008

    if _platform == 'darwin':
        cmd = path
        if param is not None:
            cmd = cmd + " " + param
        else:
            cmd = "open -a " + cmd
        subprocess.Popen([cmd], shell=True)

    elif _platform == 'win32' or _platform == 'win64':
        cmd = [path]
        if param is not None:
            cmd = cmd + [param]
        subprocess.Popen(cmd, creationflags=DETACHED_PROCESS, shell=True)

    elif _platform.startswith('linux'):
        if (param is not None):
            arg = [path, param]
        else:
            arg = path
        subprocess.Popen(arg, shell=False)

    else:
        raise Exception("%s is not a supported platform" % _platfom)

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
        except psutil.ZombieProcess:
            pass

def edit_file(content, script, prefix):
    COMMENT_PRE = "\n// ### INSERTED BELOW ### //\n".encode('utf-8')
    COMMENT_POST = "\n// ### INSERTED ABOVE ### //\n".encode('utf-8')
    loc_pre = content.rfind(COMMENT_PRE)
    loc_post = content.rfind(COMMENT_POST)
    if (loc_pre != -1): 
        if (loc_post == -1): 
            raise Exception("found prefix at %d but can't find postfix" % loc_pre)
        content = content[:loc_pre] + content[loc_post:]
    if prefix:
        return COMMENT_PRE + script + COMMENT_POST + content
    else:
        return content + COMMENT_PRE + script + COMMENT_POST

def find_target_file_in_asar(asar):
    # first we try to parse the package.json in the asar
    package = 'package.json'
    if package in asar:
        main = json.loads(asar[package])['main']
        main = main.replace(posixpath.sep, os.path.sep)
        if main in asar: 
            six.print_("Found entry point %s%s%s in %s." % (Fore.GREEN, main, Style.RESET_ALL, package), end='\n', flush=True)
            return main

    knowns = [
            os.path.join("dist","main.js"),
            os.path.join("dist","main.bundle.js")
    ]

    for f in knowns: 
        if f in asar: return f
    raise Exception("Can't find any of %s in asar file" % str(knowns))
    
def find_asar_file(asar_path):
    asar_file = os.path.join(asar_path, 'app.asar')
    asar_unpacked_path = os.path.join(asar_path, 'app.asar.unpacked')
    return (asar_file, asar_unpacked_path)

def check_edit_method(asar_path):
    asar_file, asar_unpacked_path = find_asar_file(asar_path)
    if not os.access(asar_path, os.W_OK):
        return False
    if not os.access(asar_file, os.W_OK):
        return False
    return True




def do_edit_method(args, app_path, asar_path):
    backup_file = os.path.join(asar_path, args.backup)
    backup_unpacked_path = os.path.join(asar_path, args.backup + ".unpacked")
    asar_file, asar_unpacked_path = find_asar_file(asar_path)
    if os.path.exists(backup_file) or (os.path.exists(asar_unpacked_path) and os.path.exists(backup_unpacked_path)):
        if not args.force:
            raise Exception("Backup file already exists, consider using --force. Stopped" + backup_file)
    else:
        six.print_("Backup %s as %s%s%s." % ('app.asar', Fore.GREEN, backup_file, Style.RESET_ALL))
        shutil.copy(asar_file, backup_file)
        if os.path.exists(asar_unpacked_path):
            shutil.copytree(asar_unpacked_path, backup_unpacked_path)

    asar = Asar.open(asar_file)
    stat_file = find_target_file_in_asar(asar)

    template = Template(SLACK_PLUGIN_CODE)
    if args.debug:
        script = template.substitute(debug_script=SLACK_DEBUGGER_CODE)
    else:
        script = template.substitute(debug_script="")


    asar[stat_file] = edit_file(asar[stat_file], script.encode('utf-8'), True)
    six.print_("Marking %s%s%s in %s%s%s as unpacked file." % (Fore.GREEN, stat_file, Style.RESET_ALL, Fore.GREEN, asar_file, Style.RESET_ALL))
    asar.mark_packed(stat_file, True)
    header_sha256 = asar.save(asar_file)
    six.print_("Patching %s%s%s." % (Fore.GREEN, asar_file, Style.RESET_ALL))

    # Macos on Apple Silicone is set to run only signed applications 
    # Annoyingly, the app.asar header is now hashed and the hash is hard coded in the app's Info.Plist
    # Therefore, on Apple Sillicone we need to modify the Info.Plist and resign the app.
    # Luckily, we can still use self-signed certs here (also know as ad-hoc signature)
    # Although the asar actually contains hash for each file, in practice, the current version of Slack ignores this hash
    # The current version of slack doesn't verify the
    uname = os.uname()
    if uname.sysname == 'Darwin': #and uname.machine == 'arm64':
        import plistlib
        plistpath = os.path.join(app_path, 'Contents', 'Info.plist')
        plist = plistlib.load(open(plistpath,'rb'))
        plist['ElectronAsarIntegrity']['Resources/app.asar']['hash'] = header_sha256
        backup_file = plistpath + ".bak"
        if os.path.exists(backup_file):
            if not args.force:
                raise Exception("Backup file already exists, consider using --force. Stopped" + backup_file)
        else:
            six.print_("Backup %s as %s%s%s." % (plistpath, Fore.GREEN, backup_file, Style.RESET_ALL))
            shutil.copy(plistpath, backup_file)
        plistlib.dump(plist, open(plistpath,'wb'))

        out = subprocess.check_output(["/usr/bin/codesign --sign - --force --deep --preserve-metadata=entitlements %s" % app_path], shell=True, stderr=subprocess.STDOUT)
        six.print_("Code signing returned %s" % out);





def main():
    parser = ArgumentParser(description=""" 
    Inject hebrew support plugin into Slack's tab inside an electron app.

    This program injects the Chrome's hebrew_slack plugin into any electron (desktop) version of the slack app
    """)
    parser.add_argument("-l", "--location",
                      action="store", dest="location", default="auto",
                      help="Location of application to run, or auto, local (Windows only), store (Windows only) [default: auto]")

    parser.add_argument("--no-kill", dest="kill", action='store_false',
                        help="Do not attempt to kill original application before starting",
                        default=True
                        )

    parser.add_argument("--no-start", dest="start", action='store_false',
                        help="Do not attempt to start application (assume already running)",
                        default=True
                        )

    parser.add_argument("-b", "--backup", 
                         default = "app.asar.orig",
                         help = "Name to use save original slack app backup. This will never overwrite an existing backup file. Fails if file already exists and not used with -f [default: %(default)s]")
    parser.add_argument("-f", "--force", 
                         default = False,
                         action = "store_true",
                         help = "Proceed even if backup file already exists [default: %(default)s]")

    parser.add_argument("-d", "--debug",
                        default = False,
                        action = "store_true",
                        help = "Pass --remote-debugging-port=9222 to enable rendered debugger with chrome")

    # parse args
    args  = parser.parse_args()

    app_path, asar_path = find_app_path(args.location, 'Slack')

    colorama_init(autoreset=True)

    if not check_edit_method(asar_path):
        six.print_("Cannot write to %s%s%s. Run elevated." % (Fore.RED, asar_path, Style.RESET_ALL), end='\n', flush=True)
        return False

    if args.kill:
        kill_existing_app('slack')


    do_edit_method(args, app_path, asar_path)

    if args.start:
        six.print_("Running %s from %s %s." % ('slack', Fore.GREEN, app_path))
        run_app(app_path, None)

    six.print_("Done")
    return True
