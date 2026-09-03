import os
import sqlite3
from datetime import datetime
from config import SQLITE_DB
from pymodbus.client.sync import ModbusTcpClient


SCHEMA = """
CREATE TABLE IF NOT EXISTS Companies (CompanyID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyName TEXT NOT NULL UNIQUE, Enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS PLC_Config (PLC_ID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, PLC_Name TEXT NOT NULL DEFAULT 'PLC', PLC_IP TEXT NOT NULL, PLC_Port INTEGER NOT NULL DEFAULT 502, Slave_ID INTEGER NOT NULL DEFAULT 1, Enabled INTEGER NOT NULL DEFAULT 1, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS PLC_Data (ID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, Timestamp TEXT NOT NULL, B1 REAL DEFAULT 0, B2 REAL DEFAULT 0, B3 REAL DEFAULT 0, B4 REAL DEFAULT 0, B5 REAL DEFAULT 0, B6 REAL DEFAULT 0, B7 REAL DEFAULT 0, B8 REAL DEFAULT 0, G1 REAL DEFAULT 0, G2 REAL DEFAULT 0, G3 REAL DEFAULT 0, G4 REAL DEFAULT 0, G5 REAL DEFAULT 0, G6 REAL DEFAULT 0, G7 REAL DEFAULT 0, G8 REAL DEFAULT 0, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS Machine_Runtime (ID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, Timestamp TEXT NOT NULL, Mill REAL DEFAULT 0, Mixer REAL DEFAULT 0, PressPellet REAL DEFAULT 0, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS TrendLog (ID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, Timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, Voltage12 REAL DEFAULT 0, Voltage13 REAL DEFAULT 0, Voltage23 REAL DEFAULT 0, Voltage1 REAL DEFAULT 0, Voltage2 REAL DEFAULT 0, Voltage3 REAL DEFAULT 0, Current1 REAL DEFAULT 0, Current2 REAL DEFAULT 0, Current3 REAL DEFAULT 0, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS AlarmLog (ID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, Timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, AlarmText TEXT, AlarmLevel TEXT, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS Users (UserID INTEGER PRIMARY KEY AUTOINCREMENT, Username TEXT NOT NULL UNIQUE, PasswordHash TEXT NOT NULL, CompanyID INTEGER, Role TEXT NOT NULL DEFAULT 'Operator', Enabled INTEGER NOT NULL DEFAULT 1, IsProtected INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS MasterNotifications (NotificationID INTEGER PRIMARY KEY AUTOINCREMENT, CompanyID INTEGER NOT NULL, Level TEXT, Title TEXT, Message TEXT, CreatedDate TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, IsRead INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (CompanyID) REFERENCES Companies(CompanyID) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_plc_data_company_time ON PLC_Data(CompanyID, Timestamp);
CREATE INDEX IF NOT EXISTS idx_runtime_company_time ON Machine_Runtime(CompanyID, Timestamp);
CREATE INDEX IF NOT EXISTS idx_trend_company_time ON TrendLog(CompanyID, Timestamp);
CREATE INDEX IF NOT EXISTS idx_alarm_company_time ON AlarmLog(CompanyID, Timestamp);
"""


class Row(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        sql = sql.replace("GETDATE()", "CURRENT_TIMESTAMP")
        sql = sql.replace("DATEADD(day,1,?)", "datetime(?, '+1 day')")
        self._cursor.execute(sql, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return None if row is None else Row(dict(row))

    def fetchall(self):
        return [Row(dict(row)) for row in self._cursor.fetchall()]

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class Connection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return Cursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_connection():
    os.makedirs(os.path.dirname(SQLITE_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(SCHEMA)
    conn.commit()
    return Connection(conn)


def get_company_plc(company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT PLC_Name,PLC_IP,PLC_Port,Slave_ID FROM PLC_Config WHERE CompanyID=? AND Enabled=1 ORDER BY PLC_ID LIMIT 1",(company_id,)); row=cur.fetchone(); conn.close(); return row


def get_plc_data(company_id,date_a,date_b):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT Timestamp,B1,B2,B3,B4,B5,B6,B7,B8,G1,G2,G3,G4,G5,G6,G7,G8 FROM PLC_Data WHERE CompanyID=? AND Timestamp>=? AND Timestamp<datetime(?, '+1 day') ORDER BY Timestamp DESC",(company_id,date_a,date_b)); rows=cur.fetchall(); conn.close(); return rows


def insert_plc_data(company_id,timestamp,values):
    values=list(values)[:16]; values += [0]*(16-len(values)); conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO PLC_Data (CompanyID,Timestamp,B1,B2,B3,B4,B5,B6,B7,B8,G1,G2,G3,G4,G5,G6,G7,G8) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(company_id,timestamp,*values)); conn.commit(); conn.close()


def get_company_plc_config(company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT PLC_IP,PLC_Port,Slave_ID FROM PLC_Config WHERE CompanyID=? AND Enabled=1 ORDER BY PLC_ID LIMIT 1",(company_id,)); row=cur.fetchone(); conn.close(); return row


def get_all_enabled_plcs():
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT CompanyID,PLC_IP,PLC_Port,Slave_ID FROM PLC_Config WHERE Enabled=1 ORDER BY PLC_ID"); rows=cur.fetchall(); conn.close(); return rows


def insert_plc_data_company(company_id,values):
    insert_plc_data(company_id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),values)


def get_all_company_plcs(): return get_all_enabled_plcs()


def insert_machine_runtime(company_id,timestamp,mill,mixer,presspellet):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO Machine_Runtime (CompanyID,Timestamp,Mill,Mixer,PressPellet) VALUES (?,?,?,?,?)",(company_id,timestamp,mill,mixer,presspellet)); conn.commit(); conn.close()


def get_machine_runtime(company_id,date_a,date_b):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT Timestamp,Mill,Mixer,PressPellet FROM Machine_Runtime WHERE CompanyID=? AND Timestamp>=? AND Timestamp<datetime(?, '+1 day') ORDER BY Timestamp DESC",(company_id,date_a,date_b)); rows=cur.fetchall(); conn.close(); return rows


def insert_trend_log(company_id,voltage12,voltage13,voltage23,voltage1,voltage2,voltage3,current1,current2,current3):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO TrendLog (CompanyID,Timestamp,Voltage12,Voltage13,Voltage23,Voltage1,Voltage2,Voltage3,Current1,Current2,Current3) VALUES (?,CURRENT_TIMESTAMP,?,?,?,?,?,?,?,?,?)",(company_id,voltage12,voltage13,voltage23,voltage1,voltage2,voltage3,current1,current2,current3)); conn.commit(); conn.close()


def insert_alarm(company_id,alarm_text,alarm_level):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO AlarmLog (CompanyID,AlarmText,AlarmLevel) VALUES (?,?,?)",(company_id,alarm_text,alarm_level)); conn.commit(); conn.close()


def get_alarm_history(company_id,date_a=None,date_b=None):
    import jdatetime
    conn=get_connection(); cur=conn.cursor(); query="SELECT Timestamp,AlarmText,AlarmLevel FROM AlarmLog WHERE CompanyID=?"; params=[company_id]
    if date_a and date_b: query += " AND Timestamp>=? AND Timestamp<datetime(?, '+1 day')"; params += [date_a,date_b]
    query += " ORDER BY Timestamp DESC"; cur.execute(query,params); rows=cur.fetchall(); conn.close(); result=[]
    for row in rows:
        try: jalali=jdatetime.datetime.fromgregorian(datetime=datetime.fromisoformat(str(row.Timestamp).replace('Z',''))).strftime("%Y/%m/%d %H:%M:%S")
        except Exception: jalali=str(row.Timestamp)
        result.append({"Timestamp":row.Timestamp,"AlarmText":row.AlarmText,"AlarmLevel":row.AlarmLevel,"jalali":jalali})
    return result


def get_company_users(company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT UserID,Username,Role,Enabled FROM Users WHERE CompanyID=? ORDER BY UserID",(company_id,)); rows=cur.fetchall(); conn.close(); return rows


def create_user(username,password,company_id,role):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO Users (Username,PasswordHash,CompanyID,Role,Enabled) VALUES (?,?,?,?,1)",(username,password,company_id,role)); conn.commit(); conn.close()


def change_user_role(user_id,role,company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("UPDATE Users SET Role=? WHERE UserID=? AND CompanyID=?",(role,user_id,company_id)); conn.commit(); conn.close()


def change_user_status(user_id,status,company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("UPDATE Users SET Enabled=? WHERE UserID=? AND CompanyID=?",(status,user_id,company_id)); conn.commit(); conn.close()


def delete_user(user_id,company_id):
    conn=get_connection(); cur=conn.cursor(); cur.execute("DELETE FROM Users WHERE UserID=? AND CompanyID=?",(user_id,company_id)); conn.commit(); conn.close()


def get_master_plc_status():
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT C.CompanyID,C.CompanyName,P.PLC_Name,P.PLC_IP,P.PLC_Port,P.Slave_ID FROM Companies C LEFT JOIN PLC_Config P ON C.CompanyID=P.CompanyID WHERE P.Enabled=1 ORDER BY C.CompanyID"); rows=cur.fetchall(); conn.close(); return rows


def is_protected_user(userid):
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT IsProtected FROM Users WHERE UserID=?",(userid,)); row=cur.fetchone(); conn.close(); return bool(row.IsProtected) if row else False


def get_all_companies():
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT CompanyID,CompanyName FROM Companies ORDER BY CompanyID"); rows=cur.fetchall(); conn.close(); return rows


def create_company(name):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO Companies (CompanyName,Enabled) VALUES (?,1)",(name,)); conn.commit(); conn.close()


def get_master_notifications():
    conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT n.NotificationID,n.CompanyID,c.CompanyName,n.Level,n.Title,n.Message,n.CreatedDate,n.IsRead FROM MasterNotifications n INNER JOIN Companies c ON n.CompanyID=c.CompanyID ORDER BY n.CreatedDate DESC"); rows=cur.fetchall(); conn.close(); return rows


def create_master_notification(company_id,level,title,message):
    conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO MasterNotifications (CompanyID,Level,Title,Message,CreatedDate,IsRead) VALUES (?,?,?,?,CURRENT_TIMESTAMP,0)",(company_id,level,title,message)); conn.commit(); conn.close()


def get_company_register117(company_id):
    plc=get_company_plc(company_id)
    if plc is None: return None
    try:
        client=ModbusTcpClient(plc.PLC_IP,port=plc.PLC_Port)
        if client.connect():
            result=client.read_holding_registers(address=117,count=1,slave=plc.Slave_ID); client.close()
            if not result.isError(): return result.registers[0]
    except Exception as exc: print("PLC register 117 error:",exc)
    return None
