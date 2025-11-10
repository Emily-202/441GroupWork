from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse, json


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
                function sendValue(axis, value) {{
                    return fetch('/', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: axis + '=' + value
                    }}).then(res => res.json());
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

                    sendValue("bedRotation", bed).then(resp => {{
                        if (!resp.success) alert(resp.message);
                    }});
                    sendValue("laserRotation", laser).then(resp => {{
                        if (!resp.success) alert(resp.message);
                    }});
                }}

                function zeroMotors() {{
                    // Update webpage values instantly
                    document.getElementById('bedRotation').value = 0;
                    document.getElementById('laserRotation').value = 0;

                    Promise.all([
                        sendValue("bedRotation", 0),
                        sendValue("laserRotation", 0)
                    ]).then(() => alert("Axes reset to zero ✅"));
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


## Run Code ----------------------------------------------------------------
if __name__ == "__main__":
    runServer()