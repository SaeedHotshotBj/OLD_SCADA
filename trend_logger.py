import time

from database import (
    get_all_company_plcs,
    insert_trend_log
)

from plc import read_registers


def trend_logger():

    while True:

        try:

            plcs = get_all_company_plcs()

            for plc in plcs:

                values = read_registers(
                    plc.PLC_IP,
                    plc.PLC_Port,
                    plc.Slave_ID
                )

                if not values:
                    continue

                insert_trend_log(

                    plc.CompanyID,

                    values[35],  # 135
                    values[36],  # 136
                    values[37],  # 137

                    values[38],  # 138
                    values[39],  # 139
                    values[40],  # 140

                    values[41],  # 141
                    values[42],  # 142
                    values[43]   # 143

                )

        except Exception as e:

            print(
                "TREND LOGGER ERROR:",
                e
            )

        time.sleep(1)