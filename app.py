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
    data = {"areas": [], "members": [], "issues": [], "dailyReports": []}
    if not supabase: return jsonify(data)
    
    def fetch_safe(table_name):
        try:
            # Try current schema (construction)
            res = supabase.table(table_name).select("*").execute()
            if res.data: return res.data
        except Exception as e:
            print(f"Failed {table_name} in construction schema: {e}")
            
        try:
            # Fallback to public schema
            pub_client = create_client(url, key)
            res = pub_client.table(table_name).select("*").execute()
            return res.data
        except Exception as e:
            print(f"Failed {table_name} in public schema: {e}")
            return []

    data["areas"] = fetch_safe("working_areas")
    data["members"] = fetch_safe("team_members")
    data["issues"] = fetch_safe("issue_reports")
    data["dailyReports"] = fetch_safe("daily_reports")
    
    return jsonify(data)

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
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            def fetch_df(table_name):
                try:
                    # Current schema
                    res = supabase.table(table_name).select("*").execute()
                    if res.data: return pd.DataFrame(res.data)
                except: pass
                try:
                    # Fallback public
                    pc = create_client(url, key)
                    res = pc.table(table_name).select("*").execute()
                    if res.data: return pd.DataFrame(res.data)
                except: pass
                return pd.DataFrame([{"Message": f"No data in {table_name}"}])

            fetch_df("daily_reports").to_excel(writer, index=False, sheet_name='DailyReports')
            fetch_df("issue_reports").to_excel(writer, index=False, sheet_name='IssueReports')
        
        output.seek(0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Construction_Report_{ts}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename, 
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
