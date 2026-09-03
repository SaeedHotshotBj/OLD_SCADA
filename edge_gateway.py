from datetime import datetime, timedelta
import os
import sqlite3

from flask import Flask, jsonify, request

from config import SQLITE_DB


app = Flask(__name__)
EDGE_TOKEN = os.environ.get("SCADA_EDGE_TOKEN", "CHANGE_ME")


def db():
    conn = sqlite3.connect(SQLITE_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db():
    conn = db()
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_commands ON EdgeCommands(CompanyID, PLC_ID, Status, ID)")
    conn.commit()
    conn.close()


def authorized():
    return request.headers.get("X-Edge-Token", "") == EDGE_TOKEN and EDGE_TOKEN != "CHANGE_ME"


def company_plc_ok(conn, company_id, plc_id):
    row = conn.execute(
        "SELECT 1 FROM PLC_Config WHERE PLC_ID=? AND CompanyID=? AND Enabled=1",
        (company_id, plc_id),
    ).fetchone()
    return row is not None


@app.before_request
def startup():
    init_db()


@app.post("/api/edge/data")
def edge_data():
    if not authorized():
        return jsonify(error="Unauthorized"), 401

    payload = request.get_json(silent=True) or {}
    company_id = int(payload.get("company_id", 0))
    plc_id = int(payload.get("plc_id", 0))
    values = list(payload.get("values") or [])[:16]
    values += [0] * (16 - len(values))
    timestamp = payload.get("timestamp") or datetime.utcnow().isoformat()

    conn = db()
    if not company_plc_ok(conn, company_id, plc_id):
        conn.close()
        return jsonify(error="Unknown company/PLC"), 400

    conn.execute("""
        INSERT INTO PLC_Data
        (CompanyID, Timestamp, B1,B2,B3,B4,B5,B6,B7,B8,G1,G2,G3,G4,G5,G6,G7,G8)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (company_id, timestamp, *values))
    conn.commit()
    conn.close()
    return jsonify(ok=True)


@app.post("/api/edge/heartbeat")
def edge_heartbeat():
    if not authorized():
        return jsonify(error="Unauthorized"), 401
    return jsonify(ok=True, server_time=datetime.utcnow().isoformat())


@app.get("/api/edge/commands")
def edge_commands():
    if not authorized():
        return jsonify(error="Unauthorized"), 401

    company_id = int(request.args.get("company_id", 0))
    plc_id = int(request.args.get("plc_id", 0))
    cutoff = (datetime.utcnow() - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")

    conn = db()
    conn.execute(
        "UPDATE EdgeCommands SET Status='pending', SentAt=NULL WHERE CompanyID=? AND PLC_ID=? AND Status='sent' AND SentAt<?",
        (company_id, plc_id, cutoff),
    )

    rows = conn.execute("""
        SELECT ID, Operation, Address, Value, ValuesJSON
        FROM EdgeCommands
        WHERE CompanyID=? AND PLC_ID=? AND Status='pending'
        ORDER BY ID
        LIMIT 20
    """, (company_id, plc_id)).fetchall()

    ids = [row["ID"] for row in rows]
    if ids:
        conn.executemany(
            "UPDATE EdgeCommands SET Status='sent', SentAt=CURRENT_TIMESTAMP WHERE ID=?",
            [(command_id,) for command_id in ids],
        )
    conn.commit()

    commands = []
    for row in rows:
        item = {
            "id": row["ID"],
            "operation": row["Operation"],
            "address": row["Address"],
        }
        if row["Operation"] == "write_register":
            item["value"] = row["Value"]
        else:
            import json
            item["values"] = json.loads(row["ValuesJSON"] or "[]")
        commands.append(item)

    conn.close()
    return jsonify(commands=commands)


@app.post("/api/edge/command-result")
def edge_command_result():
    if not authorized():
        return jsonify(error="Unauthorized"), 401

    payload = request.get_json(silent=True) or {}
    command_id = int(payload.get("id", 0))
    ok = 1 if payload.get("success") else 0
    message = str(payload.get("message", ""))[:1000]

    conn = db()
    conn.execute("""
        UPDATE EdgeCommands
        SET Status=?, ResultAt=CURRENT_TIMESTAMP, ResultOK=?, ResultMessage=?
        WHERE ID=?
    """, ("done" if ok else "failed", ok, message, command_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True)


@app.post("/api/edge/command")
def create_edge_command():
    if not authorized():
        return jsonify(error="Unauthorized"), 401

    payload = request.get_json(silent=True) or {}
    company_id = int(payload.get("company_id", 0))
    plc_id = int(payload.get("plc_id", 0))
    operation = payload.get("operation")
    address = int(payload.get("address", 0))

    if operation not in ("write_register", "write_registers"):
        return jsonify(error="Unsupported operation"), 400

    import json
    value = payload.get("value")
    values = payload.get("values")
    if operation == "write_register" and value is None:
        return jsonify(error="value is required"), 400
    if operation == "write_registers" and not isinstance(values, list):
        return jsonify(error="values must be a list"), 400

    conn = db()
    if not company_plc_ok(conn, company_id, plc_id):
        conn.close()
        return jsonify(error="Unknown company/PLC"), 400

    cur = conn.execute("""
        INSERT INTO EdgeCommands
        (CompanyID, PLC_ID, Operation, Address, Value, ValuesJSON)
        VALUES (?,?,?,?,?,?)
    """, (
        company_id, plc_id, operation, address,
        int(value) if operation == "write_register" else None,
        json.dumps(values) if operation == "write_registers" else None,
    ))
    conn.commit()
    command_id = cur.lastrowid
    conn.close()
    return jsonify(ok=True, id=command_id)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001)
