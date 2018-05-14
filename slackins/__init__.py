import pychrome
import os
import sys
import time
import operator
import glob
import subprocess
from argparse import ArgumentParser


SLACK_PLUGIN_CODE = """
    (function() {

      window.document.getElementById('msg_input').dir = 'auto';

      function elementShouldBeRTL(element) {
        return /[א-ת]/.test(element.innerHTML);
      }

      function alreadyApplied(element) {
        return element.children.length == 1 && (
          element.children[0].tagName == "P" || element.children[0].tagName == "p");
      }

      function applyTo(element) {
        element.innerHTML = '<p style="direction: rtl; text-align: left; margin: 0;">' + element.innerHTML + '</p>';
        for (var i in element.children[0].children) {
          var child = element.children[0].children[i];
          if (!(child.style instanceof CSSStyleDeclaration))
            continue;
          child.style.textAlign = "initial";
        }
      }

      function setDirections() {
        var contents = document.getElementsByClassName('c-message__body');
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
        document.body.removeEventListener('DOMSubtreeModified', domModified);
        setTimeout(function() { // debouce modifications
          setDirections();
          document.body.addEventListener('DOMSubtreeModified', domModified);
        }, 500);
      }

      document.body.addEventListener("DOMSubtreeModified", domModified);
    })();
"""

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

def find_slack_path(version):
    slack_root = os.path.join(os.environ['LOCALAPPDATA'],'slack') 
    apps = os.path.join(slack_root, "app-")
    candidates = [x for x in glob.glob(os.path.join(apps + "*")) if os.path.isdir(x)]

    if version == "auto":
        versions = [[int(y) for y in x.rsplit('-',1)[-1].split('.')] for x in candidates]
        max_index, max_value = max(enumerate(versions), key=operator.itemgetter(1))
        return candidates[max_index]
    p = os.path.join(apps,version)
    if not os.path.isdir(p) or not os.path.isfile(os.path.join(p,"slack.exe")):
        raise Exception("%s is not a valid slack directory" % p)
    return p

def run_slack(path, port):
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen([os.path.join(path,"slack.exe"), "--remote-debugging-port=%d" % port], creationflags=DETACHED_PROCESS, shell=True)


def inject_script(port, script):
    browser = pychrome.Browser(url = "http://127.0.0.1:%d" % port)
    tabs = browser.list_tab()
    for tab in tabs: # Inject into all open tabs
        tab.start()
        tab.Runtime.evaluate(expression = script)
        tab.stop()




def main():
    parser = ArgumentParser(description=""" 
    Inject hebrew support plugin into Slack's electron app.

    This program injects the Chrome's hebrew_slack plugin into the electron (desktop) version of the slack app
    """)
    parser.add_argument("-v", "--version",
                      action="store", dest="version", default="auto",
                      help="Version of slack to run [default: auto]")

    parser.add_argument("-t", "--time",
                      default=15,
                      type=int,
                      help="Wait for Slack to load for timeout seconds before injecting [default: %default]")

    parser.add_argument("-d","--debug", 
                      default=False,
                      action="store_true",
                      help="Additionally attempt to inject dev tools code [default: %defaut]")

    parser.add_argument("-p", "--port",
                      type=int,
                      default=9222,
                      help="Port on which Slack is listening to debug interface [default: %default]")

    # parse args
    args  = parser.parse_args()

    slack_path = find_slack_path(args.version)

    print("Running slack from %s" % slack_path)
    run_slack(slack_path,args.port)

    print("Sleeping for %s seconds" % args.time, end='', flush=True)
    for i in range(args.time):
        print('.', end='', flush=True)
        time.sleep(1)
    inject_script(args.port, SLACK_PLUGIN_CODE)
    if args.debug:
        inject_script(args.port, SCRIPT_HOTKEYS_F12_DEVTOOLS_F5_REFRESH)

    print("Hopefully done ")


if __name__ == "__main__":
    main()
