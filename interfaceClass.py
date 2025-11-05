from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse, json



bedRotation = {'A':0}
laserRotation = {'B':0}

def generateOneHTML():
    html = f"""
        <html>
        <head><title>Stepper Control</title></head>
        <body style="font-family: Arial; margin: 30px;">

        <h2> Stepper Axis Control </h2>
        <p> Use the input fields below to set the desired positions for each axis.</p>
        <p> Click the buttons to move the axes (in degrees) or zero their positions.</p>

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

                    // Send values to server without triggering validation alerts
                    sendValue("bedRotation", 0);
                    sendValue("laserRotation", 0);
                }}
            </script>
        </body>
        </html>
        """
    return html.encode("utf-8")