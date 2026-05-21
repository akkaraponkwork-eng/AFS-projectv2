from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from automation import run_automation
import json
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            session['username'] = username
            session['password'] = password
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="กรุณากรอก Username และ Password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

automation_state = {"should_stop": False}

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    automation_state["should_stop"] = True
    return jsonify({"success": True, "message": "ส่งคำสั่งยกเลิกแล้ว"})

@app.route('/api/start', methods=['GET'])
def start_automation():
    username = session.get('username')
    password = session.get('password')
    temp_min = float(request.args.get('tempMin', 35.9))
    temp_max = float(request.args.get('tempMax', 36.1))
    start_row = int(request.args.get('startRow', 1))
    end_row = int(request.args.get('endRow', 39))
    time_period = request.args.get('timePeriod', 'morning')
    show_browser = request.args.get('showBrowser', 'true') == 'true'
    u_value = request.args.get('uValue', 'skip')

    if not username or not password:
        return jsonify({"success": False, "message": "ไม่ได้เข้าสู่ระบบ หรือเซสชั่นหมดอายุ"}), 401

    # Reset state
    automation_state["should_stop"] = False

    def generate():
        for log_line in run_automation(username, password, temp_min, temp_max, start_row, end_row, time_period, show_browser, u_value, automation_state):
            yield f"data: {log_line}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
