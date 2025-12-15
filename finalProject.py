from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
import math
import urllib.parse, json
from urllib.request import urlopen
import multiprocessing
from shifter import Shifter
import time
from RPi import GPIO

## GPIO Setup ------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
time.sleep(1)
laserpin = 23
GPIO.setup(laserpin, GPIO.OUT)
GPIO.output(laserpin, GPIO.LOW)

## Global Variables ------------------------------------------------------------------
Globalradius = 300
Globalangle = 0
Globalheight = 20.955

## Find JSON File --------------------------------------------------------------------
def load_target_data(url="http://192.168.66.122:8000/positions.json"):
    try:
        with urlopen(url) as response:
            return json.load(response)
    except Exception as e:
        print("Error loading JSON from URL:", e)
        try:
            with open("targets.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading local JSON:", e)
            return {}

## Position Values -------------------------------------------------------------------
bedRotation = {'A': 0}
laserRotation = {'B': 0}
laserState = {"on": False}

## Generate HTML ---------------------------------------------------------------------
def generateHTML():
    laser_color = "green" if laserState["on"] else "red"
    laser_text = "ON" if laserState["on"] else "OFF"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Stepper Control</title>
<meta charset="UTF-8">
</head>
<body style="font-family: Arial; margin: 30px;">

<h3>Stepper Axis Control</h3>

<label>Bed Position:</label>
<input type="number" id="bedRotation" value="{bedRotation['A']}"><br><br>

<label>Laser Position:</label>
<input type="number" id="laserRotation" value="{laserRotation['B']}"><br><br>

<button onclick="moveMotors()">Move</button>
<button onclick="zeroMotors()">Zero</button>

<hr>

<h3>Laser</h3>
<div style="width:40px;height:40px;border-radius:50%;background:{laser_color};"></div>
<p>Laser is {laser_text}</p>
<button onclick="toggleLaser()">Toggle Laser</button>

<hr>

<h3>Targets</h3>
<select id="targetSelector"></select>
<button onclick="moveToTarget()">Move to Target</button>

<script>
async function sendValue(axis,value,zero=false){{
    const body=new URLSearchParams();
    body.append(axis,value);
    if(zero) body.append("zero","true");
    await fetch("/",{{method:"POST",headers:{{"Content-Type":"application/x-www-form-urlencoded"}},body}});
}}

function moveMotors(){{
    sendValue("bedRotation",bedRotation.value);
    sendValue("laserRotation",laserRotation.value);
}}

function zeroMotors(){{
    sendValue("bedRotation",0,true);
    sendValue("laserRotation",0,true);
}}

async function toggleLaser(){{
    await fetch("/toggleLaser",{{method:"POST"}});
    location.reload();
}}

async function moveToTarget(){{
    const sel=document.getElementById("targetSelector").value;
    if(!sel) return alert("Select target");
    await fetch("/selectTarget",{{method:"POST",headers:{{"Content-Type":"application/x-www-form-urlencoded"}},body:"target="+sel}});
}}

async function loadTargets(){{
    const data=await (await fetch("/targets")).json();
    const sel=document.getElementById("targetSelector");
    sel.innerHTML="";
    for(const id in data.turrets){{
        const o=document.createElement("option");
        o.value="turret_"+id;
        o.textContent="Turret "+id;
        sel.appendChild(o);
    }}
}}
loadTargets();
</script>
</body>
</html>
"""
    return html.encode("utf-8")

## HTTP Handler ---------------------------------------------------------------------
class StepperHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type","text/html")
            self.end_headers()
            self.wfile.write(generateHTML())
        elif self.path == "/targets":
            self.send_response(200)
            self.send_header("Content-type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(load_target_data()).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/toggleLaser":
            laserState["on"] = not laserState["on"]
            GPIO.output(laserpin, GPIO.HIGH if laserState["on"] else GPIO.LOW)
            self._send_json({"on": laserState["on"]})
            return

        length=int(self.headers.get("Content-Length",0))
        body=self.rfile.read(length).decode()
        params=urllib.parse.parse_qs(body)

        for k,v in params.items():
            val=float(v[0])
            if k=="bedRotation":
                self.motor_bed.goAngle(val)
            elif k=="laserRotation":
                self.motor_laser.goAngle(val)

        self._send_json({"success":True})

    def _send_json(self,obj):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

## Stepper Class ---------------------------------------------------------------------
class Stepper:
    seq=[0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]
    steps_per_degree=4096/360
    delay=2500
    num_steppers=0
    shifter_outputs=0

    def __init__(self,shifter,lock):
        self.s=shifter
        self.lock=lock
        self.angle=multiprocessing.Value('d',0.0)
        self.step_state=0
        self.start=Stepper.num_steppers*4
        Stepper.num_steppers+=1

    def __step(self,dir):
        self.step_state=(self.step_state+dir)%8
        mask=0b1111<<self.start
        Stepper.shifter_outputs&=~mask
        Stepper.shifter_outputs|=Stepper.seq[self.step_state]<<self.start
        self.s.shiftByte(Stepper.shifter_outputs)
        with self.angle.get_lock():
            self.angle.value+=dir/Stepper.steps_per_degree

    def __rotate(self,delta):
        steps=int(abs(delta)*Stepper.steps_per_degree)
        d=1 if delta>0 else -1
        for _ in range(steps):
            self.__step(d)
            time.sleep(self.delay/1e6)

    def goAngle(self,deg):
        with self.angle.get_lock():
            cur=self.angle.value
        delta=((deg-cur+540)%360)-180
        p=multiprocessing.Process(target=self.__rotate,args=(delta,))
        p.start()
        p.join()

    def goAngleXZ(self,targetAngle):
        dtheta=(targetAngle-Globalangle+math.pi)%(2*math.pi)-math.pi
        self.goAngle(math.degrees(dtheta))

    # 🔥 FIXED FUNCTION 🔥
    def goAngleY(self,targetAngle,targetHeight):
        dtheta=(targetAngle-Globalangle+math.pi)%(2*math.pi)-math.pi
        C=2*Globalradius*math.sin(abs(dtheta)/2)
        if C<1e-6:
            return
        phi=math.degrees(math.atan2(targetHeight-Globalheight,C))
        self.goAngle(phi)

## Run -------------------------------------------------------------------------------
if __name__=="__main__":
    s=Shifter(data=14,latch=15,clock=18)
    lock=multiprocessing.Lock()
    bed=Stepper(s,lock)
    laser=Stepper(s,lock)
    StepperHandler.motor_bed=bed
    StepperHandler.motor_laser=laser

    server=ThreadingHTTPServer(("0.0.0.0",8080),StepperHandler)
    print("Server running on port 8080")
    server.serve_forever()