from pymodbus.client.sync import ModbusTcpClient
import threading
import time
from datetime import datetime

from database import (
    get_company_plc_config,
    insert_plc_data
)


REGISTER_START = 100
REGISTER_COUNT = 16
TRIGGER_REGISTER = 118


def read_company_plc(company_id):

    plc = get_company_plc_config(company_id)

    if plc is None:
        print("No PLC configuration")
        return


    ip = plc.PLC_IP
    port = plc.PLC_Port
    slave = plc.Slave_ID


    client = ModbusTcpClient(
        ip,
        port=port
    )

    previous_trigger = 0


    while True:

        try:

            if not client.connect():

                print("PLC connection failed")

                time.sleep(5)

                continue



            result = client.read_holding_registers(
                address=REGISTER_START,
                count=REGISTER_COUNT,
                slave=slave
            )


            trigger = client.read_holding_registers(
                address=TRIGGER_REGISTER,
                count=1,
                slave=slave
            )



            if not result.isError() and not trigger.isError():


                values = result.registers

                trigger_value = trigger.registers[0]



                if trigger_value == 1 and previous_trigger == 0:


                    timestamp = datetime.now()


                    insert_plc_data(
                        company_id,
                        timestamp,
                        values
                    )


                    print(
                        "Inserted:",
                        company_id,
                        timestamp
                    )


                    previous_trigger = 1



                elif trigger_value == 0:

                    previous_trigger = 0



            time.sleep(0.5)



        except Exception as e:

            print(e)

            time.sleep(5)



def start_company_reader(company_id):

    thread = threading.Thread(
        target=read_company_plc,
        args=(company_id,),
        daemon=True
    )

    thread.start()