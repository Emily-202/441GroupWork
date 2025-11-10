from http.server import BaseHTTPRequestHandler, HTTPServer
import math
import urllib.parse, json
import multiprocessing
from shifter import Shifter
import time


## Position Values -------------------------------------------------------------------
bedRotation = {'A':0}
laserRotation = {'B':0}

## Generate HTML Code ----------------------------------------------------------------
def generateHTML():
    html = f"""
        <html>
        <head><title>Stepper Control</title></head>
        <body style="font-family: Arial; margin: 30px;">

        <h2> Stepper Axis Control </h2>
        <p> Use the input fields below to set the desired positions for each axis. <br>
            Click the buttons to move the axes (in degrees) or zero their positions.</p>

            <br>

            <form action="/" method="POST">
                <p>
                    <label for="bedRotation">Bed Position [-180 and 180]:</label>
                    <input type="number" id="bedRotation" min="-180" max="180" value="{bedRotation['A']}"><br><br>
                </p>
                <p>
                    <label for="laserRotation">Laser Position [-180 and 180]:</label>
                    <input type="number" id="laserRotation" min="-180" max="180" value="{laserRotation['B']}"><br><br>
                </p>
                <input type="button" value="Move" onclick="updatePosition('bedRotation', document.getElementById('bedRotation').value); updatePosition('laserRotation', document.getElementById('laserRotation').value);">
                <input type="button" value="Zero Positions" onclick="updatePosition('bedRotation', 0); updatePosition('laserRotation', 0);">
            </form>

            <script>
                async function sendValue(axis, value) {{
                    const body = new URLSearchParams();
                    body.append(axis, value);

                    const response = await fetch('/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: body
                    }});

                    return response.json();
                }}

                function moveMotors() {{
                    let bed = parseInt(document.getElementById('bedRotation').value);
                    let laser = parseInt(document.getElementById('laserRotation').value);

                    if (isNaN(bed) || bed < -180 || bed > 180) {{
                        alert("Bed value must be between -180 and 180.");
                        return;
                    }}
                    if (isNaN(laser) || laser < -180 || laser > 180) {{
                        alert("Laser value must be between -180 and 180.");
                        return;
                    }}

                    sendValue("bedRotation", bed);
                    sendValue("laserRotation", laser);
                }}

                function zeroMotors() {{
                    // visually zero out the fields
                    document.getElementById('bedRotation').value = 0;
                    document.getElementById('laserRotation').value = 0;

                    // send both values to server
                    sendValue("bedRotation", 0);
                    sendValue("laserRotation", 0);
                }}
                </script>

        </body>
        </html>
        """
    return html.encode("utf-8")


## Run Server Command ------------------------------------------------------------------
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


## HTTP Request Handler ----------------------------------------------------------------
class StepperHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(generateHTML())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(body)

        print("Received POST data:", params)

        for key in params:
            try:
                value = int(params[key][0])
            except:
                self._send_json({"success": False, "message": "Invalid number format"})
                return

            # Validate input range
            if value < -180 or value > 180:
                self._send_json({"success": False, "message": f"{key} must be between -180 and 180"})
                return

            # Save and call motor functions
            if key == "bedRotation":
                bedRotation['A'] = value
                self.move_bed_stepper(value)
            elif key == "laserRotation":
                laserRotation['B'] = value
                self.move_laser_stepper(value)

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


## Run Code ----------------------------------------------------------------
if __name__ == "__main__":
    runServer()
