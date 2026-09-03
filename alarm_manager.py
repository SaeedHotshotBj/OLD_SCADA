import os
import json
from database import insert_alarm


ALARM_FILE = "active_alarms.json"


# ======================================
# Load active alarms from file
# ======================================

def load_active_alarms():

    if not os.path.exists(ALARM_FILE):

        return {}


    try:

        with open(
            ALARM_FILE,
            "r"
        ) as f:

            return json.load(f)


    except:

        return {}



# ======================================
# Save active alarms
# ======================================

def save_active_alarms(data):

    with open(
        ALARM_FILE,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )



# ======================================
# Create alarm
# ======================================

def create_alarm(company_id, text, level):


    alarms = load_active_alarms()


    key = f"{company_id}_{text}"



    # already active

    if key in alarms:

        return



    insert_alarm(

        company_id,

        text,

        level

    )



    alarms[key] = {

        "text": text,

        "level": level

    }


    save_active_alarms(
        alarms
    )



    print(
        "NEW ALARM:",
        text
    )



# ======================================
# Clear alarm
# ======================================

def clear_alarm(company_id,text):


    alarms = load_active_alarms()


    key = f"{company_id}_{text}"



    if key in alarms:


        del alarms[key]


        save_active_alarms(
            alarms
        )



# ======================================
# Alarm checking
# ======================================

def check_alarms(company_id, values):


    if len(values) < 9:

        return



    voltage1 = values[3]
    voltage2 = values[4]
    voltage3 = values[5]


    current1 = values[6]
    current2 = values[7]
    current3 = values[8]



    # Voltage

    check_limit(
        company_id,
        voltage1 < 180,
        "Low Voltage L1"
    )


    check_limit(
        company_id,
        voltage2 < 180,
        "Low Voltage L2"
    )


    check_limit(
        company_id,
        voltage3 < 180,
        "Low Voltage L3"
    )



    # Current

    check_limit(
        company_id,
        current1 > 100,
        "Over Current L1"
    )


    check_limit(
        company_id,
        current2 > 100,
        "Over Current L2"
    )


    check_limit(
        company_id,
        current3 > 100,
        "Over Current L3"
    )



def check_limit(company_id, condition, text):


    if condition:

        create_alarm(

            company_id,

            text,

            "Critical"

        )

    else:

        clear_alarm(

            company_id,

            text

        )



# ======================================
# PLC status
# ======================================

def check_plc_status(company_id, online):


    if not online:

        create_alarm(

            company_id,

            "PLC Offline",

            "Critical"

        )

    else:

        clear_alarm(

            company_id,

            "PLC Offline"

        )