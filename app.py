import os, io
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# Supabase Setup
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
options = ClientOptions(schema="construction")
supabase = None

if url and "your_" not in url:
    try:
        supabase: Client = create_client(url, key, options=options)
    except Exception as e:
        print(f"Supabase 연결 실패 (UI 테스트 모드): {e}")
else:
    print("Supabase 설정이 비어있습니다. UI 테스트 모드로 시작합니다.")

@app.route('/')
def index():
    return render_template('index.html')

# GET: Fetch all initial data
@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    if not supabase:
        return jsonify({"areas": [], "members": [], "issues": [], "dailyReports": []})
    
    response = {"areas": [], "members": [], "issues": [], "dailyReports": []}
    
    try:
        response["areas"] = supabase.table("working_areas").select("*").execute().data
    except Exception as e:
        print(f"Error areas: {e}")
        
    try:
        response["members"] = supabase.table("team_members").select("*").execute().data
    except Exception as e:
        print(f"Error members: {e}")
        
    try:
        response["issues"] = supabase.table("issue_reports").select("*").order("id", desc=True).execute().data
    except Exception as e:
        # Fallback to order without 'date' if not exists
        try:
            response["issues"] = supabase.table("issue_reports").select("*").execute().data
        except: pass
        
    try:
        response["dailyReports"] = supabase.table("daily_reports").select("*").order("id", desc=True).execute().data
    except Exception as e:
        try:
            response["dailyReports"] = supabase.table("daily_reports").select("*").execute().data
        except: pass
        
    return jsonify(response)

# POST: Save/Update Issue Report Comments
@app.route('/api/issues/<int:id>', methods=['PATCH'])
def update_issue(id):
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
    data = request.json
    try:
        result = supabase.table("daily_reports").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Update Area
@app.route('/api/areas/<int:id>', methods=['PATCH'])
def update_area(id):
    data = request.json
    try:
        result = supabase.table("working_areas").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Update Member
@app.route('/api/members/<int:id>', methods=['PATCH'])
def update_member(id):
    data = request.json
    try:
        result = supabase.table("team_members").update(data).eq("id", id).execute()
        return jsonify({"status": "success", "data": result.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Issue Report
@app.route('/api/issues', methods=['POST'])
def create_issue():
    data = request.json
    try:
        result = supabase.table("issue_reports").insert(data).execute()
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# POST: Create New Daily Report
@app.route('/api/daily', methods=['POST'])
def create_daily():
    data = request.json
    try:
        result = supabase.table("daily_reports").insert(data).execute()
        return jsonify({"status": "success", "data": result.data}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/export-excel')
def export_excel():
    try:
        # Defaulting to Daily Reports for export
        res = supabase.table("daily_reports").select("*").order("created_at", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='DailyReports')
        output.seek(0)
        
        filename = f"Construction_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename, 
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
