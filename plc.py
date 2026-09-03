from pymodbus.client.sync import ModbusTcpClient
from register_map import (
    START_REGISTER,
    TRIGGER
)
from register_map import MACHINE_RUNTIME_TRIGGER



def test_plc_connection(ip, port):

    client = ModbusTcpClient(
        ip,
        port=port
    )

    try:

        if client.connect():

            client.close()
            return True

        else:
            return False

    except Exception:

        return False



def read_registers(ip, port, slave_id):

    client = ModbusTcpClient(
        ip,
        port=port
    )

    values = []

    try:

        if client.connect():

            result = client.read_holding_registers(
                address=START_REGISTER,
                count=61,
                slave=slave_id
            )


            if not result.isError():

                values = result.registers


            client.close()


    except Exception as e:

        print(
            "PLC Read Error:",
            e
        )


    return values



def read_trigger(ip, port, slave_id):

    client = ModbusTcpClient(
        ip,
        port=port
    )

    value = 0

    try:

        if client.connect():

            result = client.read_holding_registers(
                address=MACHINE_RUNTIME_TRIGGER,
                count=1,
                slave=slave_id
            )

            if not result.isError():

                value = result.registers[0]


        client.close()

    except Exception as e:

        print("Trigger Read Error:", e)


    return value