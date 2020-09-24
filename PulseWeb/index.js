var express = require('express');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var tmp = require('tmp');
var fs = require('fs');
var process = require('process');

const { spawn } = require('child_process')

app.use(express.static('public'));

io.on('connection', function(socket){
	socket.on('run', function (code) {
		let temp = tmp.fileSync();
		fs.writeSync(temp.fd, code);

		process.chdir("/tmp/");
		
		let pulsec = spawn('/bin/pulsec', [temp.name], {detached: true, shell: true});
		
		pulsec.stdout.on('data', (data) => {
            socket.emit('out', data.toString());
        });
        
        pulsec.stderr.on('data', (data) => {
            socket.emit('err', data.toString());
        });
        
        pulsec.on('close', () => {
            socket.emit('html', "\n<hr />\n");
          
            let proc = spawn('/usr/bin/unbuffer', ['/usr/bin/firejail', '--quiet', '--timeout=00:00:04', temp.name], {detached: true, shell: true});
    		
    		proc.stdout.on('data', (data) => {
                socket.emit('out', data.toString());
            });
            
            proc.stderr.on('data', (data) => {
                socket.emit('err', data.toString());
            });
    
            proc.on('close', (code) => {
                if(code !== 0) {
                    socket.emit('err', "The program ran unsuccessfully. Please ensure that your code has no errors and can run in the allotted timeout of 4 seconds.")
                }
        
        		fs.unlinkSync(temp.name);
            });
        });
	});
});

http.listen(8005, function(){
  console.log('listening on *:8005');
});
