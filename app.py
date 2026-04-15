import os, io
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Supabase Setup
url = os.environ.get("SUPABASE_URL", "https://wsvqeoufppcoeclbfbgz.supabase.co")
key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndzdnFlb3VmcHBjb2VjbGJmYmd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwMTQwNDIsImV4cCI6MjA5MTU5MDA0Mn0.p0rk8oPdVWO7xgvQiGUDSxzNWoi06NJZ3zcFN9SvGrE")
schema = os.environ.get("SUPABASE_SCHEMA", "public")
supabase = None
if url and "your_" not in url and key and "your_" not in key:
    try:
        if schema != "public":
            supabase = create_client(url, key, options=ClientOptions(schema=schema))
        else:
            supabase = create_client(url, key)
        print(f"Supabase connected to {url} (schema: {schema})")
    except Exception as e:
        print(f"Supabase 연결 실패: {e}")
else:
    print("Supabase 설정이 비어있습니다. UI 테스트 모드로 시작합니다.")

@app.route('/sw.js')
def service_worker():
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/')
def index():
    config = {
        "cloudName": os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
        "uploadPreset": os.environ.get("CLOUDINARY_UPLOAD_PRESET", "")
    }
    return render_template('index.html', cloudinary_config=config)

# GET: Fetch all initial data
@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    data = {"areas": [], "members": [], "issues": [], "dailyReports": []}
    if not supabase: return jsonify(data)

    def fetch_safe(table_name):
        try:
            res = supabase.table(table_name).select("*").execute()
            return res.data or []
        except Exception as e:
            print(f"Failed {table_name}: {e}", flush=True)
            return []

    data["areas"] = fetch_safe("working_areas")
    data["members"] = fetch_safe("team_members")
    data["issues"] = fetch_safe("issue_reports")
    data["dailyReports"] = fetch_safe("daily_reports")
    
    return jsonify(data)

# POST: Save/Update Issue Report Comments
@app.route('/api/issues/<int:id>', methods=['PATCH'])
def update_issue(id):
    print(f"PATCH /api/issues/{id} - supabase is {type(supabase)}")
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        # Only update columns provided in payload
        result = supabase.table("issue_reports").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Save/Update Daily Report Comments
@app.route('/api/daily/<int:id>', methods=['PATCH'])
def update_daily(id):
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        result = supabase.table("daily_reports").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        print(f"Error updating daily: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Update Area
@app.route('/api/areas/<int:id>', methods=['PATCH'])
def update_area(id):
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        result = supabase.table("working_areas").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        print(f"Error updating area: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Area
@app.route('/api/areas', methods=['POST'])
def create_area():
    print(f"POST /api/areas - supabase is {type(supabase)}")
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        result = supabase.table("working_areas").insert(data).execute()
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        print(f"Error creating area: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Update Member
@app.route('/api/members/<int:id>', methods=['PATCH'])
def update_member(id):
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        result = supabase.table("team_members").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        print(f"Error updating member: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Member
@app.route('/api/members', methods=['POST'])
def create_member():
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    try:
        result = supabase.table("team_members").insert(data).execute()
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        print(f"Error creating member: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Issue Report
@app.route('/api/issues', methods=['POST'])
def create_issue():
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    if not data or not data.get('title'):
        return jsonify({"status": "error", "message": "Title is required"}), 400
    try:
        result = supabase.table("issue_reports").insert(data).execute()
        # Fetch the newly created record by title+date to get real id (nulls last)
        if result.data:
            fetched = supabase.table("issue_reports").select("*").eq("title", data.get("title","")).eq("date", data.get("date","")).order("id", desc=True, nullsfirst=False).limit(1).execute()
            return jsonify({"status": "success", "data": fetched.data}), 201
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        print(f"Error creating issue: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Daily Report
@app.route('/api/daily', methods=['POST'])
def create_daily():
    if not supabase: return jsonify({"status": "error", "message": "Supabase not initialized"}), 500
    data = request.json
    if not data or not data.get('title'):
        return jsonify({"status": "error", "message": "Title is required"}), 400
    try:
        result = supabase.table("daily_reports").insert(data).execute()
        # Fetch the newly created record to get real id (nulls last)
        if result.data:
            fetched = supabase.table("daily_reports").select("*").eq("title", data.get("title","")).eq("date", data.get("date","")).order("id", desc=True, nullsfirst=False).limit(1).execute()
            return jsonify({"status": "success", "data": fetched.data}), 201
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        print(f"Error creating daily: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

def make_excel(tables):
    if not supabase:
        return jsonify({"status": "error", "message": "Database not connected"}), 500
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for table_name, sheet_name in tables:
                try:
                    res = supabase.table(table_name).select("*").execute()
                    df = pd.DataFrame(res.data) if res.data else pd.DataFrame([{"Message": f"No data in {table_name}"}])
                except Exception as e:
                    print(f"Excel fetch failed {table_name}: {e}", flush=True)
                    df = pd.DataFrame([{"Message": f"No data in {table_name}"}])
                df.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Construction_Report_{ts}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export-excel')
def export_excel():
    return make_excel([("daily_reports", "DailyReports"), ("issue_reports", "IssueReports")])

@app.route('/api/export-excel/daily')
def export_excel_daily():
    return make_excel([("daily_reports", "DailyReports")])

@app.route('/api/export-excel/issues')
def export_excel_issues():
    return make_excel([("issue_reports", "IssueReports")])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
