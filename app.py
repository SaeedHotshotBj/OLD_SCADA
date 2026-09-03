from flask import Flask, render_template, request, redirect, session, send_file, url_for
from extensions import socketio
import pandas as pd
from io import BytesIO
from database import (
    get_connection,
    get_company_plc,
    get_plc_data,
    get_machine_runtime,
    get_all_company_plcs,
    get_alarm_history,
    get_company_users,
    create_user,
    change_user_role,
    change_user_status,
    delete_user,
    get_all_companies,
    create_company,
    get_master_notifications,
    get_company_register117
)
from plc import test_plc_connection, read_registers
import threading
import threading
import reader
import database_writer
from auth import login_required
from register_map import (
    register_to_index,
    MILL_HOUR,
    MIXER_HOUR,
    PRESS_PELLET_HOUR
)
from register_map import (
    register_to_index,
    MILL_HOUR,
    MIXER_HOUR,
    PRESS_PELLET_HOUR,
    CURRENT,
    VOLTAGE
)
from flask_socketio import SocketIO
import reader
import database_writer
import dashboard_reader
import trend_logger
import cleanup
from database import (
    get_all_company_plcs,
    get_alarm_history
)
from pymodbus.client.sync import ModbusTcpClient
from auth import login_required, admin_required, master_required
import pulse




app = Flask(__name__)

app.config['SECRET_KEY'] = 'SCADA_SECRET_KEY'


socketio.init_app(
    app,
    cors_allowed_origins="*"
)

import jdatetime
from datetime import datetime


def jalali_to_gregorian(date_str):

    date_str = date_str.replace('-', '/')

    y, m, d = map(int, date_str.split('/'))

    j_date = jdatetime.date(y, m, d)

    g_date = j_date.togregorian()

    return datetime(
        g_date.year,
        g_date.month,
        g_date.day
    )


def gregorian_to_jalali(dt):

    jdt = jdatetime.datetime.fromgregorian(
        datetime=dt
    )

    return jdt.strftime("%Y/%m/%d %H:%M:%S")





@app.route("/")
@login_required
def home():


    if session.get("role") == "Master":
        return redirect("/master")

    if "user_id" not in session:
        return redirect("/login")


    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""
        SELECT CompanyName
        FROM Companies
        WHERE CompanyID=?
    """,
    (
        session["company_id"],
    ))

    company = cursor.fetchone()


    # Get PLC based on logged in company
    plc = get_company_plc(
        session["company_id"]
    )

    print("====================")
    print("SESSION:", session)
    print("COMPANY ID:", session.get("company_id"))
    print("PLC RESULT:", plc)
    print("====================")


    plc_values = read_registers(
        plc.PLC_IP,
        plc.PLC_Port,
        plc.Slave_ID
    )

    current = 0
    voltage = 0

    if plc_values:

        current = plc_values[
            register_to_index(CURRENT)
        ]

        voltage = plc_values[
            register_to_index(VOLTAGE)
        ]

    if plc_values:
        plc_status = True
    else:
        plc_status = False

        conn.close()


    return render_template(
        "dashboard.html",
        company_name=company.CompanyName,
        plc_name=plc.PLC_Name,
        plc_ip=plc.PLC_IP,
        plc_port=plc.PLC_Port,
        slave_id=plc.Slave_ID,
        plc_status=plc_status,
        plc_values=plc_values,
        current=current,
        voltage=voltage
    )


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]


        conn = get_connection()
        cursor = conn.cursor()


        cursor.execute("""
            SELECT 
                UserID,
                CompanyID,
                Role
            FROM Users
            WHERE Username=? 
            AND PasswordHash=?
            AND Enabled=1
        """,
        (
            username,
            password
        ))


        user = cursor.fetchone()


        conn.close()


        if user:

            session["logged_in"] = True

            session["user_id"] = user.UserID

            session["company_id"] = user.CompanyID

            session["role"] = user.Role


            if user.Role == "Master":

                session["is_master"] = True

                return redirect("/master")


            else:

                session["is_master"] = False

                return redirect("/")


        else:

            return "Wrong username or password"


    return render_template("login.html")


@app.route('/viewer', methods=['GET','POST'])

def viewer():

    data = []

    print("Logged company:", session["company_id"])


    if request.method == 'POST':

        date_a_jalali = request.form['date_a']
        date_b_jalali = request.form['date_b']


        date_a = jalali_to_gregorian(
            date_a_jalali
        )

        date_b = jalali_to_gregorian(
            date_b_jalali
        )


        rows = get_plc_data(
            session["company_id"],
            date_a,
            date_b
        )


        for row in rows:


            item = {


                "timestamp": gregorian_to_jalali(row.Timestamp),


                "B1": row.B1 or 0,
                "B2": row.B2 or 0,
                "B3": row.B3 or 0,
                "B4": row.B4 or 0,
                "B5": row.B5 or 0,
                "B6": row.B6 or 0,
                "B7": row.B7 or 0,
                "B8": row.B8 or 0,


                "G1": row.G1 or 0,
                "G2": row.G2 or 0,
                "G3": row.G3 or 0,
                "G4": row.G4 or 0,
                "G5": row.G5 or 0,
                "G6": row.G6 or 0,
                "G7": row.G7 or 0,
                "G8": row.G8 or 0

            }


            # Sum of this row
            item["row_sum"] = sum([

                item["B1"],
                item["B2"],
                item["B3"],
                item["B4"],
                item["B5"],
                item["B6"],
                item["B7"],
                item["B8"],

                item["G1"],
                item["G2"],
                item["G3"],
                item["G4"],
                item["G5"],
                item["G6"],
                item["G7"],
                item["G8"]

            ])


            data.append(item)



        # ===================================
        # ADD GRAND TOTAL ROW (جمع کل)
        # ===================================

        if data:


            total = {


                "timestamp": "جمع کل",


                "B1": 0,
                "B2": 0,
                "B3": 0,
                "B4": 0,
                "B5": 0,
                "B6": 0,
                "B7": 0,
                "B8": 0,


                "G1": 0,
                "G2": 0,
                "G3": 0,
                "G4": 0,
                "G5": 0,
                "G6": 0,
                "G7": 0,
                "G8": 0,


                "row_sum": 0

            }



            # Sum each column

            for item in data:


                total["B1"] += item["B1"]
                total["B2"] += item["B2"]
                total["B3"] += item["B3"]
                total["B4"] += item["B4"]
                total["B5"] += item["B5"]
                total["B6"] += item["B6"]
                total["B7"] += item["B7"]
                total["B8"] += item["B8"]


                total["G1"] += item["G1"]
                total["G2"] += item["G2"]
                total["G3"] += item["G3"]
                total["G4"] += item["G4"]
                total["G5"] += item["G5"]
                total["G6"] += item["G6"]
                total["G7"] += item["G7"]
                total["G8"] += item["G8"]



            # Sum of total row

            total["row_sum"] = (

                total["B1"] +
                total["B2"] +
                total["B3"] +
                total["B4"] +
                total["B5"] +
                total["B6"] +
                total["B7"] +
                total["B8"] +

                total["G1"] +
                total["G2"] +
                total["G3"] +
                total["G4"] +
                total["G5"] +
                total["G6"] +
                total["G7"] +
                total["G8"]

            )



            # Put total row at the end

            data.append(total)



    return render_template(
        "template.html",
        data=data
    )


@app.route("/export_excel", methods=["POST"])
@login_required
def export_excel():


    date_a_jalali = request.form["date_a"]

    date_b_jalali = request.form["date_b"]


    date_a = jalali_to_gregorian(
        date_a_jalali
    )


    date_b = jalali_to_gregorian(
        date_b_jalali
    )


    rows = get_plc_data(

        session["company_id"],

        date_a,

        date_b

    )


    data = []


    for row in rows:

        item = {

            "Timestamp":
            gregorian_to_jalali(row.Timestamp),

            "B1": row.B1 or 0,
            "B2": row.B2 or 0,
            "B3": row.B3 or 0,
            "B4": row.B4 or 0,
            "B5": row.B5 or 0,
            "B6": row.B6 or 0,
            "B7": row.B7 or 0,
            "B8": row.B8 or 0,

            "G1": row.G1 or 0,
            "G2": row.G2 or 0,
            "G3": row.G3 or 0,
            "G4": row.G4 or 0,
            "G5": row.G5 or 0,
            "G6": row.G6 or 0,
            "G7": row.G7 or 0,
            "G8": row.G8 or 0

        }


        # جمع ردیف
        item["جمع ردیف"] = sum([

            item["B1"],
            item["B2"],
            item["B3"],
            item["B4"],
            item["B5"],
            item["B6"],
            item["B7"],
            item["B8"],

            item["G1"],
            item["G2"],
            item["G3"],
            item["G4"],
            item["G5"],
            item["G6"],
            item["G7"],
            item["G8"]

        ])


        data.append(item)

    if data:

        total = {

            "Timestamp": "جمع کل",

            "B1": sum(x["B1"] for x in data),
            "B2": sum(x["B2"] for x in data),
            "B3": sum(x["B3"] for x in data),
            "B4": sum(x["B4"] for x in data),
            "B5": sum(x["B5"] for x in data),
            "B6": sum(x["B6"] for x in data),
            "B7": sum(x["B7"] for x in data),
            "B8": sum(x["B8"] for x in data),

            "G1": sum(x["G1"] for x in data),
            "G2": sum(x["G2"] for x in data),
            "G3": sum(x["G3"] for x in data),
            "G4": sum(x["G4"] for x in data),
            "G5": sum(x["G5"] for x in data),
            "G6": sum(x["G6"] for x in data),
            "G7": sum(x["G7"] for x in data),
            "G8": sum(x["G8"] for x in data),

        }


        total["جمع ردیف"] = sum([

            total["B1"],
            total["B2"],
            total["B3"],
            total["B4"],
            total["B5"],
            total["B6"],
            total["B7"],
            total["B8"],

            total["G1"],
            total["G2"],
            total["G3"],
            total["G4"],
            total["G5"],
            total["G6"],
            total["G7"],
            total["G8"]

        ])


        data.append(total)


    df = pd.DataFrame(data)


    output = BytesIO()


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="PLC_Data"
        )


    output.seek(0)


    return send_file(

        output,

        download_name="PLC_Report.xlsx",

        as_attachment=True,

        mimetype=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )



@app.route("/machine_report", methods=["GET","POST"])
def machine_report():

    if "user_id" not in session:
        return redirect("/login")


    data = []


    if request.method == "POST":

        date_a_jalali = request.form["date_a"]
        date_b_jalali = request.form["date_b"]


        date_a = jalali_to_gregorian(
            date_a_jalali
        )

        date_b = jalali_to_gregorian(
            date_b_jalali
        )


        rows = get_machine_runtime(
            session["company_id"],
            date_a,
            date_b
        )


        for row in rows:

            data.append({

                "timestamp":
                    gregorian_to_jalali(row.Timestamp),

                "Mill":
                    row.Mill,

                "Mixer":
                    row.Mixer,

                "PressPellet":
                    row.PressPellet
            })


    return render_template(
        "machine_report.html",
        data=data
    )


@app.route("/export_machine_excel", methods=["POST"])
@login_required
def export_machine_excel():


    # Get dates from machine_report form

    date_a_jalali = request.form["date_a"]

    date_b_jalali = request.form["date_b"]



    # Convert Jalali to Gregorian

    date_a = jalali_to_gregorian(
        date_a_jalali
    )


    date_b = jalali_to_gregorian(
        date_b_jalali
    )



    # Read data from SQL

    rows = get_machine_runtime(

        session["company_id"],

        date_a,

        date_b

    )



    data = []



    # Convert SQL rows to Excel rows

    for row in rows:


        data.append({

            "Timestamp":
                gregorian_to_jalali(row.Timestamp),

            "Mill":
                row.Mill or 0,

            "Mixer":
                row.Mixer or 0,

            "PressPellet":
                row.PressPellet or 0

        })



    # Add total row

    if data:


        total = {


            "Timestamp":
                "جمع کل",


            "Mill":
                sum(
                    item["Mill"]
                    for item in data
                ),


            "Mixer":
                sum(
                    item["Mixer"]
                    for item in data
                ),


            "PressPellet":
                sum(
                    item["PressPellet"]
                    for item in data
                )

        }



        data.append(total)



    # Create Excel file

    df = pd.DataFrame(data)



    output = BytesIO()



    with pd.ExcelWriter(

        output,

        engine="openpyxl"

    ) as writer:


        df.to_excel(

            writer,

            index=False,

            sheet_name="Machine_Runtime"

        )



    output.seek(0)



    return send_file(

        output,

        download_name="Machine_Runtime_Report.xlsx",

        as_attachment=True,

        mimetype=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )


@app.route("/trend")
@login_required
def trend():

    parameter = request.args.get(
        "parameter"
    )

    return render_template(
        "trend.html",
        parameter=parameter
    )



@app.route("/trend_data")
@login_required
def trend_data():

    parameter = request.args.get(
        "parameter"
    )


    start = request.args.get(
        "start"
    )

    end = request.args.get(
        "end"
    )


    print("START JALALI:", start)
    print("END JALALI:", end)



    # -----------------------------
    # Convert Jalali datetime
    # -----------------------------

    def jalali_datetime_to_gregorian(value):

        if not value:
            return None


        # convert Persian numbers to English

        persian_numbers = "۰۱۲۳۴۵۶۷۸۹"

        english_numbers = "0123456789"


        for p,e in zip(
            persian_numbers,
            english_numbers
        ):

            value = value.replace(
                p,
                e
            )


        # example:
        # 1405/04/21 14:30

        date_part, time_part = value.split(" ")


        y,m,d = map(
            int,
            date_part.split("/")
        )


        hh,mm = map(
            int,
            time_part.split(":")
        )


        jdate = jdatetime.datetime(
            y,
            m,
            d,
            hh,
            mm
        )


        return jdate.togregorian()



    start_time = jalali_datetime_to_gregorian(
        start
    )


    end_time = jalali_datetime_to_gregorian(
        end
    )



    print(
        "START SQL:",
        start_time
    )

    print(
        "END SQL:",
        end_time
    )



    conn = get_connection()

    cursor = conn.cursor()



    sql = f"""

    SELECT

        Timestamp,

        {parameter}

    FROM TrendLog


    WHERE CompanyID=?

    AND Timestamp >= ?

    AND Timestamp <= ?


    ORDER BY Timestamp

    """



    cursor.execute(

        sql,

        (

            session["company_id"],

            start_time,

            end_time

        )

    )


    rows = cursor.fetchall()


    conn.close()



    labels = []

    values = []



    for row in rows:


        # show Jalali date + time on graph

        labels.append(

            gregorian_to_jalali(
                row.Timestamp
            )

        )


        values.append(

            row[1]

        )



    return {


        "labels":labels,


        "values":values


    }



@app.route("/alarms")
@login_required
def alarms():


    from database import get_alarm_history


    company_id=session["company_id"]



    from_date=request.args.get(
        "from_date"
    )


    to_date=request.args.get(
        "to_date"
    )



    date_a=None
    date_b=None



    if from_date and to_date:


        date_a=jdatetime.datetime.strptime(
            from_date,
            "%Y/%m/%d"
        ).togregorian()



        date_b=jdatetime.datetime.strptime(
            to_date,
            "%Y/%m/%d"
        ).togregorian()



    alarms=get_alarm_history(

        company_id,

        date_a,

        date_b

    )



    return render_template(

        "alarms.html",

        alarms=alarms,

        from_date=from_date or "",

        to_date=to_date or ""

    )





@app.route('/control_plc', methods=["GET","POST"])
@admin_required
def control_plc():

    company_id = session.get("company_id")


    plc = get_company_plc(company_id)


    if plc is None:

        return "PLC not configured"


    # -----------------------------
    # USER MANAGEMENT
    # -----------------------------

    if request.method == "POST":


        action = request.form.get("action")



        if action == "create_user":


            create_user(

                request.form["username"],

                request.form["password"],

                company_id,

                request.form["role"]

            )



        elif action == "change_role":


            change_user_role(

                int(request.form["userid"]),

                request.form["role"],

                company_id

            )



        elif action == "disable_user":


            change_user_status(

                int(request.form["userid"]),

                0,

                company_id

            )



        elif action == "enable_user":


            change_user_status(

                int(request.form["userid"]),

                1,

                company_id

            )



        elif action == "delete_user":


            userid = int(
                request.form["userid"]
            )


            # do not delete yourself

            if userid != session["user_id"]:

                delete_user(

                    userid,

                    company_id

                )



    # -----------------------------
    # READ PLC REGISTER
    # -----------------------------


    current_value = 0


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


            if not result.isError():

                current_value=result.registers[0]


            client.close()


    except Exception as e:

        print(e)



    # -----------------------------
    # GET USERS
    # -----------------------------

    users = get_company_users(
        company_id
    )



    return render_template(
        "control_plc.html",

        register=117,

        current_value=current_value,

        plc_ip=plc.PLC_IP,

        slave=plc.Slave_ID,

        users=users

    )






@app.route('/control_write',methods=['POST'])
@admin_required
def control_write():

    print(
        "PLC WRITE REQUEST:",
        request.form
    )

    company_id = session.get("company_id")


    plc = get_company_plc(company_id)


    register = int(request.form["register"])

    value = int(request.form["value"])



    client = ModbusTcpClient(
        plc.PLC_IP,
        port=plc.PLC_Port
    )


    if client.connect():

        result = client.write_register(

            address=register,

            value=value,

            slave=plc.Slave_ID

        )

        client.close()


    return redirect(
        url_for("control_plc")
    )



@app.route('/control_toggle',methods=['POST'])
@admin_required
def control_toggle():


    company_id=session.get("company_id")


    plc = get_company_plc(company_id)



    register=int(request.form["register"])

    value=int(request.form["value"])



    client=ModbusTcpClient(

        plc.PLC_IP,

        port=plc.PLC_Port

    )



    if client.connect():


        client.write_register(

            address=register,

            value=value,

            slave=plc.Slave_ID

        )


        client.close()



    return redirect(
        url_for("control_plc")
    )



@app.route("/master_write_register", methods=["POST"])
@master_required
def master_write_register():


    company_id = int(
        request.form["company_id"]
    )


    value = int(
        request.form["value"]
    )


    plc = get_company_plc(company_id)


    if plc is None:

        return "PLC not configured"



    try:

        client = ModbusTcpClient(
            plc.PLC_IP,
            port=plc.PLC_Port
        )


        if client.connect():


            result = client.write_register(

                address=117,

                value=value,

                slave=plc.Slave_ID

            )


            client.close()


            if result.isError():

                return "PLC Write Error"



        else:

            return "PLC Connection Failed"



    except Exception as e:

        print(e)

        return "ERROR"



    return redirect("/master")




@app.route("/logout")
@login_required
def logout():

    session.clear()

    return redirect("/login")



@app.route("/master", methods=["GET","POST"])
@master_required
def master():


    if request.method=="POST":


        action=request.form.get("action")


        if action=="create_company":

            name=request.form["company_name"]

            create_company(name)



    companies = get_all_companies()


    company_list = []


    for company in companies:


        register117 = get_company_register117(
            company.CompanyID
        )


        company_list.append({

            "CompanyID": company.CompanyID,

            "CompanyName": company.CompanyName,

            "Register117": register117

        })


    companies = company_list



    notifications = get_master_notifications()



    return render_template(
        "master.html",

        companies=companies,

        notifications=notifications
    )


if __name__ == "__main__":


    threading.Thread(
        target=database_writer.database_writer,
        daemon=True
    ).start()


    threading.Thread(
        target=reader.plc_reader,
        daemon=True
    ).start()

    threading.Thread(
        target=dashboard_reader.dashboard_reader,
        daemon=True
    ).start()


    threading.Thread(
        target=trend_logger.trend_logger,
        daemon=True
    ).start()


    threading.Thread(
        target=cleanup.cleanup_old_trends,
        daemon=True
    ).start()


    threading.Thread(
        target=pulse.pulse_writer,
        daemon=True
    ).start()
    


    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )