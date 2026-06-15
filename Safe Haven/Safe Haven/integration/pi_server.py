from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import collections

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Store last 20 alerts in memory (deque acts as a circular buffer)
alerts_log = collections.deque(maxlen=20)

@app.route('/api/alert', methods=['POST'])
def receive_alert():
    """
    Receives alerts from AI Models.
    Expected JSON: {"type": "FALL" | "HELP", "confidence": 0.85}
    """
    try:
        data = request.json
        print(f"[PI SERVER] Raw data received: {data}")
        
        event_type = data.get("type", "UNKNOWN")
        confidence = data.get("confidence", 0)
        
        # Create a formatted alert object
        alert = {
            "id": int(datetime.now().timestamp() * 1000), # Simple unique ID (timestamp ms)
            "type": event_type,
            "confidence": confidence,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "emergency",
            "message": f"{event_type} Detected! (Conf: {confidence:.2f})"
        }
        
        # Add to local log
        alerts_log.appendleft(alert)
        
        print(f"[PI SERVER] 🚨 Alert Stored: {alert['message']}")
        return jsonify({"status": "stored", "alert": alert}), 200
        
    except Exception as e:
        print(f"[PI SERVER] Error processing alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """
    Mobile App polls this endpoint to get the latest alerts.
    """
    return jsonify(list(alerts_log)), 200

@app.route('/', methods=['GET'])
def home():
    return "Safe Haven Pi Backend is Runnning!", 200

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible by other devices on the network
    # Port 5000 is standard for Flask
    print("Starting Safe Haven Pi Server on port 5000...")
    app.run(host='0.0.0.0', port=5000)
