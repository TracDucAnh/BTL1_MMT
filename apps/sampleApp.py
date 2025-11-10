# Example usage
import json
import time
from urllib.parse import parse_qs

from daemon import weaprous


app = weaprous.WeApRous()

@app.route("/", methods=["GET"])
def home(_):
    return {"message": "Welcome to the RESTful TCP WebApp"}

@app.route("/user", methods=["GET"])
def get_user(_):
    return {"id": 1, "name": "Alice", "email": "alice@example.com"}

@app.route("/echo", methods=["POST"])
def echo(body):
    try:
        data = json.loads(body)
        return {"received": data}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}