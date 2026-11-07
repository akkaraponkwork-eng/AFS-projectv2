from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from automation import run_automation
from datetime import datetime
import os
import json
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'afs-default-secret-key-change-in-env')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
SESSION_FILE = os.path.join(DATA_DIR, 'session.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

DEFAULT_SETTINGS = {
    "start_row": 1,
    "end_row": 39,
    "time_period": "morning",
    "temp_min": 35.9,
    "temp_max": 36.1,
    "u_value": "skip",
    "show_browser": True,
    "system_url": "https://rtamed.rta.mi.th:8443/login"
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                res = DEFAULT_SETTINGS.copy()
                res.update(saved)
                return res
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save settings.json: {e}")

def load_saved_auth():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('username') and data.get('password'):
                    return data
        except Exception:
            return None
    return None

def save_auth(username, password, remember=True):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "username": username,
                "password": password,
                "remember": remember
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save session.json: {e}")

def clear_auth():
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history_record(record):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        history = load_history()
        history.insert(0, record)
        history = history[:100] # เก็บย้อนหลังสูงสุด 100 รายการ
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save history.json: {e}")

def clear_history():
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
        except Exception:
            pass

automation_states = {}

def get_current_user():
    username = session.get('username')
    password = session.get('password')
    if not username or not password:
        saved = load_saved_auth()
        if saved and saved.get('remember', True):
            session['username'] = saved['username']
            session['password'] = saved['password']
            username = saved['username']
    return username

@app.route('/')
def index():
    username = get_current_user()
    if not username:
        return redirect(url_for('login'))
    settings = load_settings()
    return render_template('index.html', username=username, settings=settings)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    username = get_current_user()
    if not username:
        return redirect(url_for('login'))

    success_msg = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'reset':
            save_settings(DEFAULT_SETTINGS.copy())
            success_msg = "คืนค่าเริ่มต้นเรียบร้อยแล้ว"
        else:
            new_settings = {
                "start_row": int(request.form.get('start_row', 1)),
                "end_row": int(request.form.get('end_row', 39)),
                "time_period": request.form.get('time_period', 'morning'),
                "temp_min": float(request.form.get('temp_min', 35.9)),
                "temp_max": float(request.form.get('temp_max', 36.1)),
                "u_value": request.form.get('u_value', 'skip'),
                "show_browser": request.form.get('show_browser') == 'on' or request.form.get('show_browser') == 'true'
            }
            save_settings(new_settings)
            success_msg = "บันทึกการตั้งค่าเรียบร้อยแล้ว"

    current_settings = load_settings()
    return render_template('settings.html', username=username, settings=current_settings, success_msg=success_msg)

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    username = get_current_user()
    if not username:
        return jsonify({"success": False, "message": "ไม่ได้เข้าสู่ระบบ"}), 401

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict()
        new_settings = load_settings()
        if 'start_row' in data: new_settings['start_row'] = int(data['start_row'])
        if 'end_row' in data: new_settings['end_row'] = int(data['end_row'])
        if 'time_period' in data: new_settings['time_period'] = data['time_period']
        if 'temp_min' in data: new_settings['temp_min'] = float(data['temp_min'])
        if 'temp_max' in data: new_settings['temp_max'] = float(data['temp_max'])
        if 'u_value' in data: new_settings['u_value'] = data['u_value']
        if 'show_browser' in data: new_settings['show_browser'] = str(data['show_browser']).lower() in ('true', '1', 'on')
        save_settings(new_settings)
        return jsonify({"success": True, "message": "บันทึกการตั้งค่าเรียบร้อยแล้ว", "settings": new_settings})

    return jsonify({"success": True, "settings": load_settings()})

@app.route('/history')
def history():
    username = get_current_user()
    if not username:
        return redirect(url_for('login'))

    history_list = load_history()
    stats = {
        "total": len(history_list),
        "success": sum(1 for h in history_list if h.get('status') == 'success'),
        "total_items": sum(h.get('processed_count', 0) for h in history_list)
    }
    return render_template(
        'history.html',
        username=username,
        history=history_list,
        history_json=json.dumps(history_list, ensure_ascii=False),
        stats=stats
    )

@app.route('/api/history', methods=['GET', 'DELETE'])
def api_history():
    username = get_current_user()
    if not username:
        return jsonify({"success": False, "message": "ไม่ได้เข้าสู่ระบบ"}), 401

    if request.method == 'DELETE':
        clear_history()
        return jsonify({"success": True, "message": "ล้างประวัติเรียบร้อยแล้ว"})

    return jsonify({"success": True, "data": load_history()})

@app.route('/api/history/export')
def export_history_csv():
    username = get_current_user()
    if not username:
        return redirect(url_for('login'))

    history_list = load_history()
    output = io.StringIO()
    output.write('\ufeff') # UTF-8 BOM สำหรับเปิดใน Excel ภาษาไทยไม่เพี้ยน
    writer = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'Username', 'Start ID', 'End ID', 'Period', 'Temp Range', 'U Value', 'Status', 'Processed Count'])

    for h in history_list:
        writer.writerow([
            h.get('id', ''),
            h.get('timestamp', ''),
            h.get('username', ''),
            h.get('start_row', ''),
            h.get('end_row', ''),
            h.get('time_period', ''),
            h.get('temp_range', ''),
            h.get('u_value', ''),
            h.get('status', ''),
            h.get('processed_count', 0)
        ])

    filename = f"afs_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = Response(output.getvalue(), mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on' or request.form.get('remember') == 'true'

        if username and password:
            session['username'] = username
            session['password'] = password
            if remember:
                save_auth(username, password, remember=True)
            else:
                clear_auth()
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="กรุณากรอก Username และ Password")

    # GET: ตรวจสอบว่ามีข้อมูลใน data/session.json อยู่แล้วหรือไม่
    saved = load_saved_auth()
    if saved and saved.get('remember', True):
        session['username'] = saved['username']
        session['password'] = saved['password']
        return redirect(url_for('index'))

    saved_username = saved.get('username', '') if saved else ''
    return render_template('login.html', saved_username=saved_username)

@app.route('/logout')
def logout():
    username = session.get('username')
    if username and username in automation_states:
        automation_states[username]["should_stop"] = True
    session.clear()
    clear_auth()
    return redirect(url_for('login'))

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "ไม่ได้เข้าสู่ระบบ"}), 401
    
    if username in automation_states:
        automation_states[username]["should_stop"] = True
    return jsonify({"success": True, "message": "ส่งคำสั่งยกเลิกแล้ว"})

@app.route('/api/start', methods=['GET'])
def start_automation():
    username = session.get('username')
    password = session.get('password')

    # Fallback to saved auth if session cookie lost
    if not username or not password:
        saved = load_saved_auth()
        if saved:
            username = saved.get('username')
            password = saved.get('password')
            session['username'] = username
            session['password'] = password

    if not username or not password:
        return jsonify({"success": False, "message": "ไม่ได้เข้าสู่ระบบ หรือเซสชั่นหมดอายุ"}), 401

    temp_min = float(request.args.get('tempMin', 35.9))
    temp_max = float(request.args.get('tempMax', 36.1))
    start_row = int(request.args.get('startRow', 1))
    end_row = int(request.args.get('endRow', 39))
    time_period = request.args.get('timePeriod', 'morning')
    show_browser = request.args.get('showBrowser', 'true') == 'true'
    u_value = request.args.get('uValue', 'skip')

    state = {"should_stop": False}
    automation_states[username] = state

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    collected_logs = []
    final_status = "success"
    processed_count = 0

    def generate():
        nonlocal final_status, processed_count
        try:
            for log_line in run_automation(username, password, temp_min, temp_max, start_row, end_row, time_period, show_browser, u_value, state):
                try:
                    data = json.loads(log_line.strip())
                    msg = data.get("message", "")
                    log_type = data.get("type", "info")
                    collected_logs.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "type": log_type,
                        "message": msg
                    })

                    if log_type == "error":
                        final_status = "error"
                    elif log_type == "warning" and "ยกเลิก" in msg:
                        final_status = "cancelled"
                    elif log_type == "success" and "เสร็จสิ้น" in msg:
                        # Extract count if possible
                        try:
                            # e.g. "ทำงานเสร็จสิ้นทั้งหมด 39 รายการ!"
                            parts = msg.split()
                            for p in parts:
                                if p.isdigit():
                                    processed_count = int(p)
                                    break
                        except Exception:
                            pass
                    elif "กรอกอุณหภูมิ" in msg:
                        processed_count += 1
                except Exception:
                    pass

                yield f"data: {log_line}\n\n"
        except Exception as e:
            final_status = "error"
            collected_logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": "error",
                "message": f"Server Error: {str(e)}"
            })
        finally:
            record = {
                "id": run_id,
                "timestamp": start_time_str,
                "username": username,
                "start_row": start_row,
                "end_row": end_row,
                "time_period": time_period,
                "temp_range": f"{temp_min} - {temp_max}",
                "u_value": u_value,
                "status": final_status,
                "processed_count": processed_count,
                "logs": collected_logs
            }
            save_history_record(record)

            if username in automation_states and automation_states[username] is state:
                automation_states.pop(username, None)

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
