import time
from datetime import datetime

from database import (
    get_all_company_plcs,
    insert_machine_runtime
)

from plc import read_registers, read_trigger

from queue_manager import data_queue

from register_map import (
    register_to_index,
    MILL_HOUR,
    MIXER_HOUR,
    PRESS_PELLET_HOUR
)

# Remember previous trigger state for every PLC
previous_triggers = {}


def plc_reader():

    while True:

        try:

            plcs = get_all_company_plcs()


            for plc in plcs:


                plc_key = plc.CompanyID


                # first time initialization
                if plc_key not in previous_triggers:
                    previous_triggers[plc_key] = 0


                # read trigger register 118
                trigger = read_trigger(
                    plc.PLC_IP,
                    plc.PLC_Port,
                    plc.Slave_ID
                )


                if trigger is None:
                    continue


                old_trigger = previous_triggers[plc_key]



                # Rising edge detection: 0 --> 1
                if trigger == 1 and old_trigger == 0:


                    values = read_registers(
                        plc.PLC_IP,
                        plc.PLC_Port,
                        plc.Slave_ID
                    )


                    if values:


                        data_queue.put({

                            "company_id": plc.CompanyID,

                            "timestamp": datetime.now(),

                            "values": values

                        })

                        mill = values[
                            register_to_index(MILL_HOUR)
                        ]

                        mixer = values[
                            register_to_index(MIXER_HOUR)
                        ]

                        presspellet = values[
                            register_to_index(PRESS_PELLET_HOUR)
                        ]


                        insert_machine_runtime(

                            plc.CompanyID,

                            datetime.now(),

                            mill,

                            mixer,

                            presspellet

                        )


                        # Runtime saved successfully


                        # Trigger insert completed


                # save current trigger state
                previous_triggers[plc_key] = trigger



        except Exception as e:

            print(
                "PLC READER ERROR:",
                e
            )


        time.sleep(0.2)