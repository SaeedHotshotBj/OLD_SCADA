import time
from pymodbus.client.sync import ModbusTcpClient

from database import get_all_company_plcs


def pulse_writer():

    while True:

        try:

            plcs = get_all_company_plcs()


            for plc in plcs:


                client = ModbusTcpClient(
                    plc.PLC_IP,
                    port=plc.PLC_Port
                )


                if client.connect():


                    # ON
                    client.write_register(
                        address=116,
                        value=1,
                        slave=plc.Slave_ID
                    )


                    


                    time.sleep(1)


                    # OFF
                    client.write_register(
                        address=116,
                        value=0,
                        slave=plc.Slave_ID
                    )


                    


                    client.close()


        except Exception as e:

            print(
                "Pulse Error:",
                e
            )


        # wait before next pulse
        time.sleep(1)