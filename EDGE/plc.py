from pymodbus.client.sync import ModbusTcpClient


def _client(ip, port):
    return ModbusTcpClient(ip, port=port, timeout=3)


def read_registers(ip, port, slave_id, address, count):
    client = _client(ip, port)
    try:
        if not client.connect():
            return None, "PLC connection failed"
        result = client.read_holding_registers(address=address, count=count, unit=slave_id)
        if result.isError():
            return None, str(result)
        return list(result.registers), "OK"
    except Exception as exc:
        return None, str(exc)
    finally:
        client.close()


def write_register(ip, port, slave_id, address, value):
    client = _client(ip, port)
    try:
        if not client.connect():
            return False, "PLC connection failed"
        result = client.write_register(address=address, value=value, unit=slave_id)
        if result.isError():
            return False, str(result)
        return True, "OK"
    except Exception as exc:
        return False, str(exc)
    finally:
        client.close()
