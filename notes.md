# M1 Mac
Life became so much harder when using the M1 Macos version due to mandatory code signing.
now we have to take the following steps.
1. Patch files as always
1. Extract the sha256 of the header (serialized as json with no padding)
1. Edit the "Info.plist" by and update the hash at ElectronAsarIntegrity -> Resources/app.asar -> hash by
```console
➜ sudo vi Slack.app/Contents/Info.plist
```
1. Resign Slack with an adhoc signature so mac will run it by ```console 
sudo codesign --sign -  --force --deep --preserve-metadata=entitlements ./Slack.app
```

# Notes to self.
Slack makes life harder and less fun.

Now, I've had to do the following changes.
```python
a = Asar.open(r"C:\Users\yonatan\AppData\Local\slack\app-4.0.1\resources\app.asar")        
a.mark_packed(r'dist/main.js', True)                                                       
a.save(r"C:\Users\yonatan\AppData\Local\slack\app-4.0.1\resources\app.asar")               
```

and then changed main.js to 
```javascript
const { app } = require('electron')
const { BrowserWindow } = require('electron')

payload = `
function changeStyle() { 
    var classes = ['ql-editor', 'c-message__body', 'message_body', 'c-message_attachment__text', 'msg_inline_attachment_row', 'c-mrkdwn__pre', 'c-message_kit__text'];

    classes.forEach((cls) => {
      for (let item of document.getElementsByClassName(cls))
      { 
        item.setAttribute('dir','auto');
        item.style.textAlign = 'start';
      }
    });


    classes = ['c-message__edited_label'];

    classes.forEach((cls) => {
      for (let item of document.getElementsByClassName(cls))
      { 
        item.style.display = 'inline-block';
      }
    });
    

    //$('.ql-editor, .c-message__body, .message_body, .c-message_attachment__text, .msg_inline_attachment_row, .c-mrkdwn__pre, .c-message_kit__text').attr('dir', 'auto').css('text-align', 'start');
    //$('.c-message__edited_label').css('display','inline-block');
}
function doIt() {
  alert('running 2 ');
  document.getElementsByTagName('body')[0].addEventListener('DOMSubtreeModified', changeStyle)
}

alert('running 3');
doIt();
`;

app.commandLine.appendSwitch('remote-debugging-port', '9222');
app.on('web-contents-created', (evt, webContents) => {
     webContents.on('did-finish-load', function() {
        webContents.executeJavaScript("alert('running');"); 
        webContents.executeJavaScript(payload); 
     });
});
require('./common.vendor.js'); require('./main.vendor.js'); require('./main.bundle.js'); 
```
