import time

from database import get_all_company_plcs

from plc import read_registers

from extensions import socketio

from alarm_manager import (
    check_alarms,
    check_plc_status
)







def dashboard_reader():

    while True:

        try:

            plcs = get_all_company_plcs()


            for plc in plcs:


                try:


                    values = read_registers(

                        plc.PLC_IP,

                        plc.PLC_Port,

                        plc.Slave_ID

                    )



                    # ==========================
                    # PLC ONLINE
                    # ==========================

                    if values:


                        

                        # ==========================
                        # PLC ONLINE CHECK
                        # ==========================

                        check_plc_status(

                            plc.CompanyID,

                            True

                        )


                        # ==========================
                        # PARAMETER ALARMS
                        # ==========================

                        check_alarms(

                            plc.CompanyID,

                            values

                        )


                        socketio.emit(

                            "dashboard_update",

                            {

                                "company_id":
                                    plc.CompanyID,


                                "values":
                                    values,


                                "online":
                                    True

                            },

                            namespace="/"

                        )


                        



                    # ==========================
                    # PLC OFFLINE
                    # ==========================

                    else:


                        

                        check_plc_status(

                            plc.CompanyID,

                            False

                        )




                        socketio.emit(

                            "dashboard_update",

                            {

                                "company_id":
                                    plc.CompanyID,


                                "values":
                                    [],


                                "online":
                                    False

                            },

                            namespace="/"

                        )



                except Exception as plc_error:


                    print(

                        "PLC ERROR:",

                        plc.CompanyID,

                        plc_error

                    )

                    check_plc_status(

                        plc.CompanyID,

                        False

                    )


                    socketio.emit(

                        "dashboard_update",

                        {

                            "company_id":
                                plc.CompanyID,


                            "values":
                                [],


                            "online":
                                False

                        },

                        namespace="/"

                    )



        except Exception as e:


            print(

                "Dashboard Reader Error:",

                e

            )



        time.sleep(0.5)