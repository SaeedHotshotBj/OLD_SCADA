import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request, render_template_string

DB_PATH = os.getenv("SCADA_DB_PATH", "/var/www/global/scada.db")
EDGE_TOKEN = os.getenv("SCADA_EDGE_TOKEN", "")

app = Flask(__name__)


def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS EdgeCommands (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        CompanyID INTEGER NOT NULL,
        PLC_ID INTEGER NOT NULL,
        Operation TEXT NOT NULL,
        Address INTEGER NOT NULL,
        Value INTEGER,
        ValuesJSON TEXT,
        Status TEXT NOT NULL DEFAULT 'pending',
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        SentAt TEXT,
        ResultAt TEXT,
        ResultOK INTEGER,
        ResultMessage TEXT
    );
    CREATE INDEX IF NOT EXISTS IX_EdgeCommands
      ON EdgeCommands(CompanyID, PLC_ID, Status, ID);

    CREATE TABLE IF NOT EXISTS RegisterValues (
        CompanyID INTEGER NOT NULL,
        PLC_ID INTEGER NOT NULL,
        Address INTEGER NOT NULL,
        Value INTEGER NOT NULL,
        Timestamp TEXT NOT NULL,
        PRIMARY KEY (CompanyID, PLC_ID, Address)
    );

    CREATE TABLE IF NOT EXISTS EdgeStatus (
        CompanyID INTEGER NOT NULL,
        PLC_ID INTEGER NOT NULL,
        LastSeen TEXT NOT NULL,
        PRIMARY KEY (CompanyID, PLC_ID)
    );
    """)
    con.commit()
    con.close()


def auth():
    if not EDGE_TOKEN or EDGE_TOKEN == "CHANGE_ME":
        return False
    return request.headers.get("X-Edge-Token", "") == EDGE_TOKEN


def now():
    return datetime.now(timezone.utc).isoformat()


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/edge/data", methods=["POST"])
def edge_data():
    if not auth():
        return jsonify(ok=False, error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    company_id = int(data.get("company_id", 1))
    plc_id = int(data.get("plc_id", 1))
    values = data.get("values", [])
    if not isinstance(values, list):
        return jsonify(ok=False, error="values must be a list"), 400
    timestamp = data.get("timestamp") or now()
    con = db()
    for offset, value in enumerate(values):
        try:
            value = int(value)
        except Exception:
            continue
        con.execute("""
            INSERT INTO RegisterValues(CompanyID,PLC_ID,Address,Value,Timestamp)
            VALUES(?,?,?,?,?)
            ON CONFLICT(CompanyID,PLC_ID,Address) DO UPDATE SET
              Value=excluded.Value, Timestamp=excluded.Timestamp
        """, (company_id, plc_id, int(data.get("start", 0)) + offset, value, timestamp))
    con.execute("""
        INSERT INTO EdgeStatus(CompanyID,PLC_ID,LastSeen) VALUES(?,?,?)
        ON CONFLICT(CompanyID,PLC_ID) DO UPDATE SET LastSeen=excluded.LastSeen
    """, (company_id, plc_id, timestamp))
    con.commit()
    con.close()
    return jsonify(ok=True)


@app.route("/api/edge/heartbeat", methods=["POST"])
def heartbeat():
    if not auth():
        return jsonify(ok=False, error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    company_id = int(data.get("company_id", 1))
    plc_id = int(data.get("plc_id", 1))
    con = db()
    con.execute("""
        INSERT INTO EdgeStatus(CompanyID,PLC_ID,LastSeen) VALUES(?,?,?)
        ON CONFLICT(CompanyID,PLC_ID) DO UPDATE SET LastSeen=excluded.LastSeen
    """, (company_id, plc_id, now()))
    con.commit()
    con.close()
    return jsonify(ok=True, server_time=now())


@app.route("/api/edge/commands", methods=["GET"])
def edge_commands():
    if not auth():
        return jsonify(ok=False, error="unauthorized"), 401
    company_id = int(request.args.get("company_id", 1))
    plc_id = int(request.args.get("plc_id", 1))
    con = db()
    # Return commands that are pending. A sent command older than 30 seconds is retried.
    con.execute("""
        UPDATE EdgeCommands
        SET Status='pending', SentAt=NULL
        WHERE CompanyID=? AND PLC_ID=? AND Status='sent'
          AND julianday('now') - julianday(CreatedAt) > (30.0/86400.0)
    """, (company_id, plc_id))
    rows = con.execute("""
        SELECT * FROM EdgeCommands
        WHERE CompanyID=? AND PLC_ID=? AND Status='pending'
        ORDER BY ID LIMIT 20
    """, (company_id, plc_id)).fetchall()
    result = [dict(r) for r in rows]
    if rows:
        ids = [r["ID"] for r in rows]
        con.executemany("UPDATE EdgeCommands SET Status='sent',SentAt=? WHERE ID=?", [(now(), i) for i in ids])
    con.commit()
    con.close()
    return jsonify(ok=True, commands=result)


@app.route("/api/edge/command-result", methods=["POST"])
def command_result():
    if not auth():
        return jsonify(ok=False, error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    command_id = int(data.get("command_id", 0))
    ok = bool(data.get("ok", False))
    message = str(data.get("message", ""))
    value = data.get("value", None)
    address = data.get("address", None)
    con = db()
    con.execute("""
        UPDATE EdgeCommands
        SET Status=?, ResultAt=?, ResultOK=?, ResultMessage=?
        WHERE ID=?
    """, ("done" if ok else "failed", now(), 1 if ok else 0, message, command_id))
    if ok and address is not None and value is not None:
        row = con.execute("SELECT CompanyID,PLC_ID FROM EdgeCommands WHERE ID=?", (command_id,)).fetchone()
        if row:
            con.execute("""
                INSERT INTO RegisterValues(CompanyID,PLC_ID,Address,Value,Timestamp)
                VALUES(?,?,?,?,?)
                ON CONFLICT(CompanyID,PLC_ID,Address) DO UPDATE SET
                  Value=excluded.Value, Timestamp=excluded.Timestamp
            """, (row["CompanyID"], row["PLC_ID"], int(address), int(value), now()))
    con.commit()
    con.close()
    return jsonify(ok=True)


@app.route("/api/command", methods=["POST"])
def create_command():
    data = request.get_json(silent=True) or {}
    try:
        company_id = int(data.get("company_id", 1))
        plc_id = int(data.get("plc_id", 1))
        operation = str(data.get("operation", ""))
        address = int(data.get("address"))
        value = int(data["value"]) if data.get("value") is not None else None
        count = int(data.get("count", 1))
    except Exception:
        return jsonify(ok=False, error="invalid command"), 400
    if operation not in ("read_register", "read_registers", "write_register"):
        return jsonify(ok=False, error="unsupported operation"), 400
    if operation == "write_register" and value is None:
        return jsonify(ok=False, error="value is required"), 400
    if operation == "read_registers" and not 1 <= count <= 100:
        return jsonify(ok=False, error="count must be 1..100"), 400
    con = db()
    cur = con.execute("""
        INSERT INTO EdgeCommands(CompanyID,PLC_ID,Operation,Address,Value,ValuesJSON)
        VALUES(?,?,?,?,?,NULL)
    """, (company_id, plc_id, operation, address, value))
    con.commit()
    command_id = cur.lastrowid
    con.close()
    return jsonify(ok=True, command_id=command_id)


@app.route("/api/status")
def status():
    company_id = int(request.args.get("company_id", 1))
    plc_id = int(request.args.get("plc_id", 1))
    con = db()
    rows = con.execute("""
        SELECT Address,Value,Timestamp FROM RegisterValues
        WHERE CompanyID=? AND PLC_ID=? ORDER BY Address
    """, (company_id, plc_id)).fetchall()
    edge = con.execute("SELECT LastSeen FROM EdgeStatus WHERE CompanyID=? AND PLC_ID=?", (company_id, plc_id)).fetchone()
    con.close()
    return jsonify(ok=True, edge_last_seen=edge["LastSeen"] if edge else None,
                   registers=[dict(r) for r in rows])


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OLD SCADA - PLC Register</title>
<style>
body{font-family:Arial,sans-serif;max-width:900px;margin:30px auto;padding:0 15px;background:#f5f5f5;color:#222}
.card{background:#fff;border:1px solid #ddd;border-radius:10px;padding:18px;margin-bottom:16px}
input,button{padding:10px;font-size:16px;margin:4px}button{cursor:pointer}
#status{font-weight:bold}.online{color:green}.offline{color:#c00}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:center}
</style></head><body>
<h2>OLD SCADA - PLC Register</h2>
<div class="card"><div>Company ID <input id="company" type="number" value="1" min="1">
PLC ID <input id="plc" type="number" value="1" min="1"></div>
<div id="status">Checking...</div></div>
<div class="card"><h3>Read Register</h3>
<input id="readAddr" type="number" placeholder="Register address">
<button onclick="readReg()">Read Online</button>
<div id="readResult">-</div></div>
<div class="card"><h3>Write Register</h3>
<input id="writeAddr" type="number" placeholder="Register address">
<input id="writeValue" type="number" placeholder="Value">
<button onclick="writeReg()">Write</button><div id="writeResult">-</div></div>
<div class="card"><h3>Live Values</h3><table><thead><tr><th>Address</th><th>Value</th><th>Time</th></tr></thead><tbody id="rows"></tbody></table></div>
<script>
async function cmd(operation,address,value=null){let body={operation,company_id:+company.value,plc_id:+plc.value,address:+address};if(value!==null)body.value=+value;let r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json()}
async function readReg(){let a=readAddr.value;if(a==='')return;readResult.textContent='Waiting...';let x=await cmd('read_register',a);readResult.textContent=x.ok?'Command #'+x.command_id+' sent. The value will appear below.':'Error: '+x.error}
async function writeReg(){let a=writeAddr.value,v=writeValue.value;if(a===''||v==='')return;writeResult.textContent='Sending...';let x=await cmd('write_register',a,v);writeResult.textContent=x.ok?'Write command #'+x.command_id+' sent.':'Error: '+x.error}
async function refresh(){try{let r=await fetch('/api/status?company_id='+company.value+'&plc_id='+plc.value);let x=await r.json();let last=x.edge_last_seen;let online=last&&((Date.now()-new Date(last).getTime())<10000);status.className=online?'online':'offline';status.textContent=online?'EDGE ONLINE - last seen '+last:'EDGE OFFLINE';rows.innerHTML=x.registers.map(q=>'<tr><td>'+q.Address+'</td><td>'+q.Value+'</td><td>'+q.Timestamp+'</td></tr>').join('')}catch(e){status.textContent='Server error'}}
setInterval(refresh,1000);refresh();
</script></body></html>'''


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
