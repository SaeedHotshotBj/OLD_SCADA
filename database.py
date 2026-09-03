import pyodbc
from config import SQL_SERVER, SQL_DATABASE, SQL_DRIVER
from pymodbus.client.sync import ModbusTcpClient


def get_connection():

    connection_string = (
        f"DRIVER={{{SQL_DRIVER}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        "Trusted_Connection=yes;"
    )

    return pyodbc.connect(connection_string)

def get_company_plc(company_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            PLC_Name,
            PLC_IP,
            PLC_Port,
            Slave_ID
        FROM PLC_Config
        WHERE CompanyID=?
        AND Enabled=1
    """,
    (
        company_id,
    ))

    plc = cursor.fetchone()

    conn.close()

    return plc



def get_plc_data(company_id, date_a, date_b):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            Timestamp,
            B1,B2,B3,B4,B5,B6,B7,B8,
            G1,G2,G3,G4,G5,G6,G7,G8
        FROM PLC_Data
        WHERE CompanyID=?
        AND Timestamp >= ?
        AND Timestamp < DATEADD(day,1,?)
        ORDER BY Timestamp DESC
    """,
    (
        company_id,
        date_a,
        date_b
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows



def insert_plc_data(company_id, timestamp, values):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO PLC_Data
        (
            CompanyID,
            Timestamp,
            B1,B2,B3,B4,B5,B6,B7,B8,
            G1,G2,G3,G4,G5,G6,G7,G8
        )
        VALUES
        (
            ?,
            ?,
            ?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?
        )
    """,
    (
        company_id,
        timestamp,

        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        values[6],
        values[7],

        values[8],
        values[9],
        values[10],
        values[11],
        values[12],
        values[13],
        values[14],
        values[15]
    ))


    conn.commit()

    conn.close()


def get_company_plc_config(company_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            PLC_IP,
            PLC_Port,
            Slave_ID
        FROM PLC_Config
        WHERE CompanyID=?
        AND Enabled=1
    """,
    (
        company_id,
    ))

    plc = cursor.fetchone()

    conn.close()

    return plc


def get_all_enabled_plcs():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CompanyID,
            PLC_IP,
            PLC_Port,
            Slave_ID
        FROM PLC_Config
        WHERE Enabled=1
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows

def insert_plc_data_company(company_id, values):

    from datetime import datetime

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO PLC_Data
        (
            CompanyID,
            Timestamp,
            B1,B2,B3,B4,B5,B6,B7,B8,
            G1,G2,G3,G4,G5,G6,G7,G8
        )
        VALUES
        (
            ?,
            ?,
            ?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?
        )
    """,
    (
        company_id,
        datetime.now(),
        *values
    ))

    conn.commit()

    conn.close()


def get_all_company_plcs():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CompanyID,
            PLC_IP,
            PLC_Port,
            Slave_ID
        FROM PLC_Config
        WHERE Enabled=1
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def insert_machine_runtime(company_id, timestamp, mill, mixer, presspellet):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Machine_Runtime
        (
            CompanyID,
            Timestamp,
            Mill,
            Mixer,
            PressPellet
        )
        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """,
    (
        company_id,
        timestamp,
        mill,
        mixer,
        presspellet
    ))

    conn.commit()

    conn.close()



def get_machine_runtime(company_id, date_a, date_b):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Timestamp,
            Mill,
            Mixer,
            PressPellet
        FROM Machine_Runtime
        WHERE CompanyID=?
        AND Timestamp >= ?
        AND Timestamp < DATEADD(day,1,?)
        ORDER BY Timestamp DESC
    """,
    (
        company_id,
        date_a,
        date_b
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows


def insert_trend_log(
    company_id,
    voltage12,
    voltage13,
    voltage23,
    voltage1,
    voltage2,
    voltage3,
    current1,
    current2,
    current3
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO TrendLog
        (
            CompanyID,
            Timestamp,

            Voltage12,
            Voltage13,
            Voltage23,

            Voltage1,
            Voltage2,
            Voltage3,

            Current1,
            Current2,
            Current3
        )
        VALUES
        (
            ?,
            GETDATE(),

            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?
        )
        """,
        (
            company_id,

            voltage12,
            voltage13,
            voltage23,

            voltage1,
            voltage2,
            voltage3,

            current1,
            current2,
            current3
        )
    )

    conn.commit()

    conn.close()


def insert_alarm(
    company_id,
    alarm_text,
    alarm_level
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO AlarmLog
        (
            CompanyID,
            AlarmText,
            AlarmLevel
        )
        VALUES
        (
            ?, ?, ?
        )
        """,
        (
            company_id,
            alarm_text,
            alarm_level
        )
    )

    conn.commit()

    conn.close()



def get_alarm_history(company_id, date_a=None, date_b=None):

    import jdatetime

    conn = get_connection()

    cursor = conn.cursor()


    query = """
        SELECT
            Timestamp,
            AlarmText,
            AlarmLevel

        FROM AlarmLog

        WHERE CompanyID=?
    """


    params = [
        company_id
    ]


    if date_a and date_b:

        query += """
        AND Timestamp >= ?
        AND Timestamp < DATEADD(day,1,?)
        """

        params.append(date_a)
        params.append(date_b)



    query += """
        ORDER BY Timestamp DESC
    """



    cursor.execute(
        query,
        params
    )


    rows = cursor.fetchall()


    alarms=[]



    for row in rows:


        alarms.append({

            "Timestamp":
                row.Timestamp,


            "AlarmText":
                row.AlarmText,


            "AlarmLevel":
                row.AlarmLevel,


            "jalali":

                jdatetime.datetime.fromgregorian(
                    datetime=row.Timestamp
                ).strftime(
                    "%Y/%m/%d %H:%M:%S"
                )

        })


    conn.close()


    return alarms





def get_company_users(company_id):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            UserID,
            Username,
            Role,
            Enabled
        FROM Users
        WHERE CompanyID=?
        ORDER BY UserID
    """,
    (
        company_id,
    ))


    users = cursor.fetchall()

    conn.close()

    return users




def create_user(username,password,company_id,role):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute("""
        INSERT INTO Users
        (
            Username,
            PasswordHash,
            CompanyID,
            Role,
            Enabled
        )
        VALUES
        (?,?,?,?,1)
    """,
    (
        username,
        password,
        company_id,
        role
    ))


    conn.commit()

    conn.close()




def change_user_role(user_id,role,company_id):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute("""
        UPDATE Users
        SET Role=?
        WHERE UserID=?
        AND CompanyID=?
    """,
    (
        role,
        user_id,
        company_id
    ))


    conn.commit()

    conn.close()




def change_user_status(user_id,status,company_id):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute("""
        UPDATE Users
        SET Enabled=?
        WHERE UserID=?
        AND CompanyID=?
    """,
    (
        status,
        user_id,
        company_id
    ))


    conn.commit()

    conn.close()




def delete_user(user_id,company_id):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute("""
        DELETE FROM Users
        WHERE UserID=?
        AND CompanyID=?
    """,
    (
        user_id,
        company_id
    ))


    conn.commit()

    conn.close()




def get_master_plc_status():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            C.CompanyID,
            C.CompanyName,
            P.PLC_Name,
            P.PLC_IP,
            P.PLC_Port,
            P.Slave_ID
        FROM Companies C
        LEFT JOIN PLC_Config P
        ON C.CompanyID = P.CompanyID
        WHERE P.Enabled = 1
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def is_protected_user(userid):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT IsProtected
        FROM Users
        WHERE UserID=?
    """,
    (
        userid,
    ))

    row = cursor.fetchone()

    conn.close()


    if row:

        return row.IsProtected

    return False


def get_all_companies():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CompanyID,
            CompanyName
        FROM Companies
    """)

    companies = cursor.fetchall()

    conn.close()

    return companies



def create_company(name):

    conn=get_connection()

    cursor=conn.cursor()


    cursor.execute("""
        INSERT INTO Companies
        (
            CompanyName,
            Enabled
        )
        VALUES
        (
            ?,
            1
        )
    """,
    (
        name,
    ))


    conn.commit()

    conn.close()



def get_master_notifications():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            n.NotificationID,
            n.CompanyID,
            c.CompanyName,
            n.Level,
            n.Title,
            n.Message,
            n.CreatedDate,
            n.IsRead

        FROM MasterNotifications n

        INNER JOIN Companies c
        ON n.CompanyID = c.CompanyID

        ORDER BY n.CreatedDate DESC
    """)


    rows = cursor.fetchall()

    conn.close()

    return rows



def create_master_notification(
        company_id,
        level,
        title,
        message):


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        INSERT INTO MasterNotifications
        (
            CompanyID,
            Level,
            Title,
            Message,
            CreatedDate,
            IsRead
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            GETDATE(),
            0
        )

    """,
    (
        company_id,
        level,
        title,
        message
    ))


    conn.commit()

    conn.close()


def get_company_register117(company_id):

    plc = get_company_plc(company_id)

    if plc is None:
        return None


    try:

        client = ModbusTcpClient(
            plc.PLC_IP,
            port=plc.PLC_Port
        )


        if client.connect():


            result = client.read_holding_registers(
                address=117,
                count=1,
                slave=plc.Slave_ID
            )


            client.close()


            if not result.isError():

                return result.registers[0]


    except Exception as e:

        print(e)


    return None