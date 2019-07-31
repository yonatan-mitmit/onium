Onium - Inject hebrew support into slack desktop app 
=====================================================

Onium is a small utility to inject Hebrew support (automatic RTL) into Slack's desktop app.
Onium does this by modifying Slack's app.asar (Slack application code) and changes the Slack app itself.


What is Onium?
--------------

Onium fixes one of Slack's most glaring issues for users in countries whose script is written
Right-to-left. It does so by injecting code into Slack that modifies the displayed text to correctly
show Right-to-left words. 

The Slack app is built using Electron, which essentially wraps a Chromium browser and a Node.js
server together. Onium modifies the HTML displayed by the Chromium browser to properly support
Hebrew (and RTL) languages. 

Onium does this by modifying Slack's internal code (creating a "Fixed" solution), until Slack adds a new update.

Requirements
------------

You need Python 2.7 or 3.5 or later to run Onium. 
Onium should work on Windows, Mac and Linux.

Quick start
-----------

Onium can be installed using pip:

    $ python -m pip install onium

As long as python's scripts folder is in your path, simply run

    $ onium 


Usage
-----

Onium supports various command line parameters

```
usage: onium [-h] [-l LOCATION] [--no-kill] [--no-start] [-b BACKUP]
                   [-f] [-d]

Inject hebrew support plugin into Slack's tab inside an electron app. This
program injects the Chrome's hebrew_slack plugin into any electron (desktop)
version of the slack app

optional arguments:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
                        Location of application to run, or auto, local
                        (Windows only), store (Windows only) [default: auto]
  --no-kill             Do not attempt to kill original application before
                        starting
  --no-start            Do not attempt to start application (assume already
                        running)
  -b BACKUP, --backup BACKUP
                        Name to use save original slack app backup. This will
                        never overwrite an existing backup file. Fails if file
                        already exists and not used with -f [default:
                        app.asar.orig]
  -f, --force           Proceed even if backup file already exists [default:
                        False]
  -d, --debug           Pass --remote-debugging-port=9222 to enable rendered
                        debugger with chrome
```


Contribute / Join the conversation
----------------------------------

Onium is an open-source project distributed under the MIT license. Basically means go wild.  
Development is taking place at [https://github.com/yonatan-mitmit/onium](https://github.com/yonatan-mitmit/onium)  

Please report issues [here](https://github.com/yonatan-mitmit/onium/issues)

License
-------

Onium is licensed under the terms of the MIT License (see the file LICENSE.txt).

Acknowledgement
---------------
Shlomi Matichin for his [slack_hebrew](https://github.com/shlomimatichin/slack-hebrew) plugin  
Yuval Raz and Lital Lechtman for Mac port and testing  
Ami Chayun for Linux port  
