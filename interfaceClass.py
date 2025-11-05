from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse



bedRotation = {'A':0}
laserRotation = {'B':0}

def generateOneHTML():
    html = f"""
        <html>
        <head><title>LED Brightness Control</title></head>
        <body style="font-family: Arial; margin: 30px;">
            <form action="/" method="POST">
                <p>
                    <label for="bedRotation">Bed Position (between -180 and 180):</label>
                    <input type="number" id="bedRotation" name="bedRotation" min="-180" max="180" value="{bedRotation['A']}">
                </p>
                <p>
                    <label for="laserRotation">Laser Position (between -180 and 180):</label>
                    <input type="number" id="laserRotation" name="laserRotation" min="-180" max="180" value="{laserRotation['B']}">
                </p>
                <input type="submit" value="Move">
                <input type="button" value="Zero Positions">
            </form>
        </body>
        </html>
        """
    return html.encode("utf-8")