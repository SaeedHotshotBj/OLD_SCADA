from pymodbus.client.sync import ModbusTcpClient


def _client(ip, port):
    return ModbusTcpClient(ip, port=port)


def read_registers(ip, port, slave_id, start, count):
    client = _client(ip, port)
    try:
        if not client.connect():
            return None
        result = client.read_holding_registers(
            address=start,
            count=count,
            slave=slave_id,
        )
        if result.isError():
            return None
        return list(result.registers)
    except Exception as exc:
        print("PLC READ ERROR:", exc)
        return None
    finally:
        try:
            client.close()
        except Exception:
            pass


def write_register(ip, port, slave_id, address, value):
    client = _client(ip, port)
    try:
        if not client.connect():
            return False, "PLC connection failed"
        result = client.write_register(
            address=int(address),
            value=int(value),
            slave=slave_id,
        )
        if result.isError():
            return False, str(result)
        return True, "OK"
    except Exception as exc:
        return False, str(exc)
    finally:
        try:
            client.close()
        except Exception:
            pass


def write_registers(ip, port, slave_id, address, values):
    client = _client(ip, port)
    try:
        if not client.connect():
            return False, "PLC connection failed"
        result = client.write_registers(
            address=int(address),
            values=[int(v) for v in values],
            slave=slave_id,
        )
        if result.isError():
            return False, str(result)
        return True, "OK"
    except Exception as exc:
        return False, str(exc)
    finally:
        try:
            client.close()
        except Exception:
            pass
