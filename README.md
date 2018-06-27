Onium - Inject hebrew support into slack desktop app 
=====================================================

Onium is a small utility to inject Hebrew support (automatic RTL) into Slack's desktop app.
It uses one of two methods:
1. Inject - Using Electron's debug API to inject a Chrome plugin into the Electron app. 
2. Edit - Modifying Slack's app.asar (Slack application code) and changes the Slack app itself.


What is Onium?
--------------

Onium fixes one of Slack's most glaring issues for users in countries whose script is written
Right-to-left. It does so by injecting code into Slack that modifies the displayed text to correctly
show Right-to-left words. 

The Slack app is built using Electron, which essentially wraps a Chromium browser and a Node.js
server together. Onium modifies the HTML displayed by the Chromium browser to properly support
Hebrew (and RTL) languages. 

Onium does this by either modifying Slack's internal code (creating a "Fixed" solution), or by
injecting the code into Slack (A temporary, but more resillient solution).

Onium uses Shlomi Matichin's excellent [slack_hebrew](https://github.com/shlomimatichin/slack-hebrew) plugin.

Requirements
------------

You need Python 2.7 or 3.5 or later to run Onium. 
Onium should work on Windows, Mac and Linux.

Quick start
-----------

Onium can be installed using pip:

    $ python -m pip install onium

As long as python's scripts folder is in your path, simply run

    $ onium [inject]
or 

    $ onium edit


Usage
-----

Onium supports various command line parameters

```
usage: onium [-h] [-l LOCATION] [-a APP] [--no-kill] [--no-start]
             [-s {old,new}] [--update | --no-update]
             {inject,edit} ...

Inject hebrew support plugin into Slack's tab inside an electron app. This
program injects the Chrome's hebrew_slack plugin into any electron (desktop)
version of the slack app

positional arguments:
  {inject,edit}
    inject              Use the injection method - run slack with debugging
                        support and inject the hebrew scripts at runtime
    edit                Use the edit method - modify Slack's on-disk files to
                        permanently inject the hebrew support

optional arguments:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
                        Location of application to run, or auto, local (Windows only), 
                        store (Windows only) [default: auto]
  --no-kill             Do not attempt to kill original application before
                        starting
  --no-start            Do not attempt to start application (assume already
                        running)
  -s {old,new}, --script {old,new}
                        Which script to inject to Slack [default: new]
  --update              Update the slack plugin from slack_hebrew github page
  --no-update           Do not update the slack plugin
```

The inject command accepts the following arguments

```
usage: onium inject [-h] [-t TIME] [-p PORT]                                 
                                                                                   
optional arguments:                                                                
  -h, --help            show this help message and exit                            
  -t TIME, --time TIME  Wait for application to load for timeout seconds           
                        before injecting [default: 15]                             
  -p PORT, --port PORT  Port on which application is listening to debug            
                        interface [default: 9222]                                  
```

The edit command accepts the following arguments

```
usage: onium edit [-h] [-b BACKUP] [-f]

optional arguments:
  -h, --help            show this help message and exit
  -b BACKUP, --backup BACKUP
                        Name to use save original slack app backup. This will
                        never overwrite an existing backup file. Fails if file
                        already exists and not used with -f [default:
                        app.asar.orig]
  -f, --force           Proceed even if backup file already exists [default:
                        False]
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
