Onium - Inject hebrew support into slack desktop app 
=====================================================

This little utility is using Electron's debug API (Using chrome's debug API) to
inject Chrome plugins into an Electron app. 
The code was developed to inject the Hebrew support (RTL) support into Slack, but the concept can be changed to other apps and plugins. 


What is Onium?
--------------

Onium is a tool to inject the Hebrew support chrome plugin into the any slack desktop app. 
The tool was built to allow to inject any chrome plugin into electron, and will
be changed in the future to support other electron apps. 

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

    $ onium

Usage
-----

Onium supports various command line parameters

```
usage: onium [-h] [-l LOCATION] [-a APP] [-t TIME] [-d] [-p PORT]
             [--no-kill] [--no-start] [--update | --no-update]

Inject hebrew support plugin into Slack's tab inside an electron app. This
program injects the Chrome's hebrew_slack plugin into any electron (desktop)
version of the slack app

optional arguments:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
                        Location of application to run, or auto, local
                        (Windows only), store (Windows only) [default: auto]
  -a APP, --app APP     application to launch and inject code into [default:
                        slack]
  -t TIME, --time TIME  Wait for application to load for timeout seconds
                        before injecting [default: 15]
  -d, --debug           Additionally attempt to inject dev tools code
                        [default: False]
  -p PORT, --port PORT  Port on which application is listening to debug
                        interface [default: 9222]
  --no-kill             Do not attempt to kill original application before
                        starting
  --no-start            Do not attempt to start application (assume already
                        running)
  --update              Update the slack plugin from slack_hebrew github page
  --no-update           Do not update the slack plugin
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
