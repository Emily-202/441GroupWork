from http.server import BaseHTTPRequestHandler, HTTPServer
import math
import urllib.parse, json
import multiprocessing
from shifter import Shifter
import time
import json

## Helpful Websites ------------------------------------------------------------------
# https://www.w3schools.com/css/css3_buttons.asp


## Find JSON File --------------------------------------------------------------------
def load_target_data(filename="targets.json"):
    """Return parsed JSON (dict) from targets.json or {} if missing."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: targets.json not found.")
        return {}
    except Exception as e:
        print("Error loading targets.json:", e)
        return {}


## Get Theta and Z Values from JSON --------------------------------------------------
def extract_theta_z(data_text):
    """
    Parse JSON text containing turrets and globes and return a dictionary
    with key-value pairs of theta and z (if available) for all items.
    """
    # Convert the JSON text to a Python dictionary
    data = json.loads(data_text)

    result = {}

    # Extract theta for all turrets
    for turret_id, turret_data in data.get("turrets", {}).items():
        result[f"turret_{turret_id}_theta"] = turret_data.get("theta")

    # Extract theta and z for all globes
    for i, globe_data in enumerate(data.get("globes", []), start=1):
        result[f"globe_{i}_theta"] = globe_data.get("theta")
        result[f"globe_{i}_z"] = globe_data.get("z")

    return result

## Position Values -------------------------------------------------------------------
bedRotation = {'A':0}
laserRotation = {'B':0}
laserState = {"on": False}

## Generate HTML Code ----------------------------------------------------------------
def generateHTML():
    laser_color = "green" if laserState["on"] else "red"
    laser_text = "ON" if laserState["on"] else "OFF"

    html = f"""
    <html>
    <head>
        <title>Stepper Control</title>
        <meta charset="UTF-8">
        <style>
            #leftPanel {{
                width: 55%;
            }}
            #rightPanel {{
                width: 40%;
                border: 2px solid #333;
                border-radius: 10px;
                padding: 20px;
                background-color: #f0f0f0;
                height: fit-content;
            }}
            #orientationBox {{
                font-size: 18px;
                line-height: 1.6em;
            }}
            h3 {{
                margin-top: 10px;
            }}
            .fancyButton {{
                display: inline-block;
                padding: 15px 25px;
                font-size: 24px;
                cursor: pointer;
                text-align: center;
                text-decoration: none;
                color: #fff;
                background-color: #30ba6c;
                border: none;
                border-radius: 15px;
                width: 250px;
                box-shadow: 0 9px #999;
            }}
            .fancyButton:active {{
                box-shadow: 0 5px #666;
                transform: translateY(4px);
            }}
        </style>
    </head>
    <body style="font-family: Arial; margin: 30px;">

    <!-- LEFT SIDE (controls) -->
        <h3> Stepper Axis Control </h3>
        <p> Use the input fields below to set the desired positions for each axis. <br>
            Click the buttons to move the axes (in degrees) or zero their positions.</p>

            <div style="display: flex; flex-direction: row; gap: 40px; align-items: flex-start;">
            <div style="flex: 1; min-width: 350px;">

            <div>
                <p>
                    <label for="bedRotation">Bed Position [-180 and 180]:</label>
                    <input type="number" id="bedRotation" min="-180" max="180" value="{bedRotation['A']}"><br><br>
                </p>
                <p>
                    <label for="laserRotation">Laser Position [-180 and 180]:</label>
                    <input type="number" id="laserRotation" min="-180" max="180" value="{laserRotation['B']}"><br><br>
                </p>
                <input type="button" value="Move" onclick="moveMotors();">
                <input type="button" value="Zero Positions" onclick="zeroMotors();">
            </div>

            <br><hr><br>

            <h3>Laser Control</h3>
            <div id="laserIndicator"
                style="width:40px; height:40px; border-radius:50%; background:{laser_color};
                        display:inline-block; vertical-align:middle; margin-right:10px;"></div>
            <span id="laserStatus" style="font-weight:bold;">Laser is {laser_text}</span>
            <br><br>
            <input type="button" id="laserButton" value="Toggle Laser" onclick="toggleLaser();">

            <br><hr><br>

            <h3>Select Target</h3>
                <select id="targetSelector" onchange="selectTarget()">
                    <option value="">-- Choose a target --</option>
                </select>
            <br><br>
            <input type="button" id="moveTargetButton" value="Move to Target" onclick="moveToTarget();">
        </div>

    <!-- RIGHT SIDE (orientation display) -->
        <div style="flex: 1; min-width: 350px;">
            <h2>Robot Orientation</h2>
            <div id="orientationBox">
                <p><b>Bed Rotation:</b> <span id="bedAngleDisplay">{bedRotation['A']}</span>°</p>
                <p><b>Laser Rotation:</b> <span id="laserAngleDisplay">{laserRotation['B']}</span>°</p>
            </div>
            <br><br><br><br>
            <input type="button" value="start" onclick="startTrial();" class="fancyButton">
        </div>


    <script>
        function updateOrientationDisplay() {{
            document.getElementById('bedAngleDisplay').textContent =
                document.getElementById('bedRotation').value;
            document.getElementById('laserAngleDisplay').textContent =
                document.getElementById('laserRotation').value;

            const laserOn = document.getElementById('laserIndicator').style.background === 'green';
            document.getElementById('laserStateDisplay').textContent = laserOn ? 'ON' : 'OFF';
            document.getElementById('laserStateDisplay').style.color = laserOn ? 'green' : 'red';
        }}

        async function sendValue(axis, value, isZero=false) {{
            const body = new URLSearchParams();
            body.append(axis, value);
            if (isZero) body.append("zero", "true");

            const response = await fetch('/', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                body: body
            }});
            try {{
                await response.json();
            }} catch (e) {{
                console.error("Non-JSON response");
            }}
            updateOrientationDisplay();
        }}

        function moveMotors() {{
            let bed = parseInt(document.getElementById('bedRotation').value);
            let laser = parseInt(document.getElementById('laserRotation').value);
            if (isNaN(bed) || bed < -180 || bed > 180) return alert("Bed value must be between -180 and 180.");
            if (isNaN(laser) || laser < -180 || laser > 180) return alert("Laser value must be between -180 and 180.");
            sendValue("bedRotation", bed);
            sendValue("laserRotation", laser);
        }}

        function zeroMotors() {{
            document.getElementById('bedRotation').value = 0;
            document.getElementById('laserRotation').value = 0;
            sendValue("bedRotation", 0, true);
            sendValue("laserRotation", 0, true);
            updateOrientationDisplay();
        }}

        async function toggleLaser() {{
            const response = await fetch('/toggleLaser', {{ method: 'POST' }});
            const result = await response.json();
            updateLaserIndicator(result.on);
            updateOrientationDisplay();
        }}

        function updateLaserIndicator(isOn) {{
            const indicator = document.getElementById('laserIndicator');
            const status = document.getElementById('laserStatus');
            if (isOn) {{
                indicator.style.background = 'green';
                status.textContent = 'Laser is ON';
            }} else {{
                indicator.style.background = 'red';
                status.textContent = 'Laser is OFF';
            }}
        }}

        async function moveToTarget() {{
            const selected = document.getElementById('targetSelector').value;
            if (!selected) return alert("Please select a target first.");

            const data = await (await fetch('/targets')).json();
            let bedDeg = 0, laserDeg = 0;

            if (selected.startsWith('turret_')) {{
                const id = selected.split('_')[1];
                const vals = data.turrets[id];
                if (!vals) return alert("Invalid turret data.");
                bedDeg = (vals.theta * 180 / Math.PI).toFixed(1);
                laserDeg = 0;
            }} else if (selected.startsWith('globe_')) {{
                const id = parseInt(selected.split('_')[1]) - 1;
                const vals = data.globes[id];
                if (!vals) return alert("Invalid globe data.");
                bedDeg = (vals.theta * 180 / Math.PI).toFixed(1);
                laserDeg = (vals.z).toFixed(1);
            }}

            document.getElementById('bedRotation').value = bedDeg;
            document.getElementById('laserRotation').value = laserDeg;

            await sendValue("bedRotation", bedDeg);
            await sendValue("laserRotation", laserDeg);
            updateOrientationDisplay();
        }}

        async function loadTargets() {{
            const resp = await fetch('/targets');
            const data = await resp.json();
            const selector = document.getElementById('targetSelector');

            if (data.turrets) {{
                const groupTurrets = document.createElement('optgroup');
                groupTurrets.label = "Turrets";
                for (const [id, vals] of Object.entries(data.turrets)) {{
                    const option = document.createElement('option');
                    option.value = `turret_${{id}}`;
                    option.textContent = `Turret ${{id}} -> θ=${{(vals.theta||0).toFixed(3)}} rad, r=${{(vals.r||0).toFixed(1)}}`;
                    groupTurrets.appendChild(option);
                }}
                selector.appendChild(groupTurrets);
            }}

            if (data.globes) {{
                const groupGlobes = document.createElement('optgroup');
                groupGlobes.label = "Globes";
                data.globes.forEach((g, i) => {{
                    const option = document.createElement('option');
                    option.value = `globe_${{i+1}}`;
                    option.textContent = `Globe ${{i+1}} -> θ=${{(g.theta||0).toFixed(3)}} rad, z=${{(g.z||0).toFixed(1)}}, r=${{(g.r||0).toFixed(1)}}`;
                    groupGlobes.appendChild(option);
                }});
                selector.appendChild(groupGlobes);
            }}

        async function startTrial() {{
                const response = await fetch('/startTrial', {{
                    method: 'POST'
                }});

                try {{
                    const data = await response.json();
                    alert(data.message);
                }} catch {{
                    alert("Autonomous mode started.");
                }}
            }}
        }}

        loadTargets();
        updateOrientationDisplay();
    </script>

    </body>
    </html>
    """
    return html.encode("utf-8")



## Run Server Command ----------------------------------------------------------------
def runServer():
    server_address = ("0.0.0.0", 8080)
    httpd = HTTPServer(server_address, StepperHandler)
    print("Server running on http://localhost:8080 (Press Ctrl+C to stop)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
        print("Server stopped cleanly.")


## HTTP Request Handler --------------------------------------------------------------
class StepperHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(generateHTML())
        elif self.path == '/targets':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            targets = load_target_data()
            self.wfile.write(json.dumps(targets).encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/toggleLaser":
            laserState["on"] = not laserState["on"]
            print(f"Laser toggled {'ON' if laserState['on'] else 'OFF'}")
            # TODO: Add GPIO or relay control for actual laser here
            self._send_json({"success": True, "on": laserState["on"]})
            return

        if self.path == "/selectTarget":
            # read posted target name
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            parsed = urllib.parse.parse_qs(body)
            target_name = parsed.get('target', [''])[0]

            data = load_target_data()
            if target_name.startswith('turret_'):
                tid = target_name.split('_')[1]
                t = data.get('turrets', {}).get(tid)
                if t:
                    # respond with a descriptive text
                    msg = f"Turret {tid}: r={t.get('r')}, theta={t.get('theta')}"
                else:
                    msg = "Turret not found."
            elif target_name.startswith('globe_'):
                gid = int(target_name.split('_')[1]) - 1
                try:
                    g = data.get('globes', [])[gid]
                    msg = f"Globe {gid+1}: r={g.get('r')}, theta={g.get('theta')}, z={g.get('z')}"
                except Exception:
                    msg = "Globe not found."
            else:
                msg = "Unknown target."

            print("Selected target:", msg)
            # reply with plain text (client reads it)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(msg.encode('utf-8'))
            return

        # otherwise handle normal axis control as before
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(body)
        

        print("Received POST data:", params)
        is_zero = "zero" in params

        for key in params:
            if key == "zero":
                continue  # skip the flag itself

            try:
                value = int(params[key][0])
            except:
                self._send_json({"success": False, "message": "Invalid number format"})
                return

            # Validate input range
            if value < -180 or value > 180:
                self._send_json({"success": False, "message": f"{key} must be between -180 and 180"})
                return

            # Save and call motor functions (only if not zeroing)
            if key == "bedRotation":
                bedRotation['A'] = value
                if not is_zero:
                    self.move_bed_stepper(value)
                else:
                    print("Zeroing bed axis reference (no motion).")

            elif key == "laserRotation":
                laserRotation['B'] = value
                if not is_zero:
                    self.move_laser_stepper(value)
                else:
                    print("Zeroing laser axis reference (no motion).")

        self._send_json({"success": True})


    # ===== MOTOR CONTROL PLACEHOLDERS =====
    def move_bed_stepper(self, value):
        # enter working code here
        print(f"Moving bed axis to {value}")

    def move_laser_stepper(self, value):
        # enter working code here
        print(f"Moving laser axis to {value}")

    # ===== JSON RESPONSE HELPER =====
    def _send_json(self, obj):
        response = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response)


## Stepper Class ---------------------------------------------------------------------
class Stepper:
    # Class attributes
    num_steppers = 0      # track number of Steppers instantiated
    shifter_outputs = 0   # track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 2500          # delay between motor steps [us]
    steps_per_degree = 4096/360     # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter            # shift register
        self.angle = multiprocessing.Value('d', 0.0)  # current output shaft angle
        self.step_state = 0         # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock            # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        
        # 4-bit coil pattern for this motor
        mask   = 0b1111 << self.shifter_bit_start
        pattern = Stepper.seq[self.step_state] << self.shifter_bit_start

        # Clear existing bits only for this motor
        Stepper.shifter_outputs &= ~mask
        # Set this motor's new coil pattern
        Stepper.shifter_outputs |= pattern

        self.s.shiftByte(Stepper.shifter_outputs)

        # update shared angle
        with self.angle.get_lock():
            self.angle.value += dir / Stepper.steps_per_degree
            self.angle.value %= 360

    # Move relative angle from current position:
    def __rotate(self, delta):
        self.lock.acquire()                 # wait until the lock is available
        numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
        dir = self.__sgn(delta)        # find the direction (+/-1)
        for s in range(numSteps):      # take the steps
            self.__step(dir)
            time.sleep(Stepper.delay/1e6)
        self.lock.release()

    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, tarAngle):
        # read angle safely
        with self.angle.get_lock():
            curAngle = self.angle.value

        # shortest path math: force into [-180, 180]
        delta = ((tarAngle - curAngle + 540) % 360) - 180

        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()
    # moves the motor in the XZ when given our angular position with respect to the center and zero and a targets angular position with respect to the center and zero     
    def goAngleXZ(self, targetAngle,selfPosAngle):
        alpha=.5*(2*math.pi-abs(targetAngle-selfPosAngle))
        if (targetAngle-selfPosAngle <0):
            alpha=-alpha
        self.goAngle(alpha)
   # moves the motor in the Y when given our angular position with respect to the center and zero and a targets angular position with respect to the center and zero and circle radius our own height and target height     
    def goAngleY(self, targetAngle, selfPosAngle, selfHeight, radius,targetHeight):
        C=math.sqrt((2*radius**2)-(2*radius**2)*math.cos(targetAngle-selfPosAngle))
        phi=math.atan((targetHeight-selfHeight)/C)
        self.goAngle(phi)
    
    # Set the motor zero point
    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0


## Run Code --------------------------------------------------------------------------
if __name__ == "__main__":
    runServer()
