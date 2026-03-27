# Python 3.x - dOTA APP
# Install dependencies: pip install flask

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def gsi():
    game_state = request.json  # GSI sends JSON data
    print("Received Game State Data:")
    print(game_state)  # You can also process or store this data
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=3000)
