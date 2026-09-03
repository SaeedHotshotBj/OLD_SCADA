import time
from datetime import datetime, timezone
import requests
import config
from plc import read_registers, write_register

session = requests.Session()
session.headers.update({"X-Edge-Token": config.EDGE_TOKEN})


def post(path, payload):
    r = session.post(config.SERVER_URL.rstrip("/") + path, json=payload, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def send_live_values():
    values, message = read_registers(
        config.PLC_IP, config.PLC_PORT, config.SLAVE_ID,
        config.READ_START, config.READ_COUNT
    )
    if values is None:
        print("PLC READ ERROR:", message)
        return
    post("/api/edge/data", {
        "company_id": config.COMPANY_ID,
        "plc_id": config.PLC_ID,
        "start": config.READ_START,
        "values": values,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def handle_commands():
    data = post("/api/edge/commands", {
        "company_id": config.COMPANY_ID,
        "plc_id": config.PLC_ID,
    }) if False else None

    r = session.get(
        config.SERVER_URL.rstrip("/") + "/api/edge/commands",
        params={"company_id": config.COMPANY_ID, "plc_id": config.PLC_ID},
        timeout=config.REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    commands = r.json().get("commands", [])

    for cmd in commands:
        operation = cmd["Operation"]
        address = int(cmd["Address"])
        ok = False
        message = ""
        value = None

        if operation == "read_register":
            values, message = read_registers(config.PLC_IP, config.PLC_PORT, config.SLAVE_ID, address, 1)
            ok = values is not None
            if ok:
                value = int(values[0])

        elif operation == "read_registers":
            count = int(cmd.get("Value") or 1)
            values, message = read_registers(config.PLC_IP, config.PLC_PORT, config.SLAVE_ID, address, count)
            ok = values is not None
            if ok:
                value = int(values[0]) if values else None
                message = "OK values=" + repr(values)

        elif operation == "write_register":
            value = int(cmd["Value"])
            ok, message = write_register(
                config.PLC_IP, config.PLC_PORT, config.SLAVE_ID, address, value
            )
            if ok:
                # Immediately read it back so the server shows the real PLC value.
                values, read_message = read_registers(
                    config.PLC_IP, config.PLC_PORT, config.SLAVE_ID, address, 1
                )
                if values:
                    value = int(values[0])
                elif read_message:
                    message = "Write OK; readback failed: " + read_message

        else:
            ok = False
            message = "Unsupported operation: " + operation

        payload = {
            "command_id": int(cmd["ID"]),
            "ok": ok,
            "message": message,
            "address": address,
            "value": value,
        }
        try:
            post("/api/edge/command-result", payload)
        except Exception as exc:
            print("COMMAND RESULT ERROR:", exc)
        print("COMMAND", cmd["ID"], operation, address, "=>", value, ok, message)


def heartbeat():
    post("/api/edge/heartbeat", {
        "company_id": config.COMPANY_ID,
        "plc_id": config.PLC_ID,
    })


def main():
    print("OLD SCADA EDGE STARTED")
    print("PLC:", config.PLC_IP, "Slave:", config.SLAVE_ID)
    print("SERVER:", config.SERVER_URL)
    last_live = 0
    last_command = 0
    last_heartbeat = 0

    while True:
        now = time.time()
        try:
            if now - last_live >= config.READ_INTERVAL:
                send_live_values()
                last_live = now
            if now - last_command >= config.COMMAND_INTERVAL:
                handle_commands()
                last_command = now
            if now - last_heartbeat >= config.HEARTBEAT_INTERVAL:
                heartbeat()
                last_heartbeat = now
        except Exception as exc:
            print("EDGE ERROR:", exc)
            time.sleep(config.RETRY_DELAY)
        time.sleep(0.05)


if __name__ == "__main__":
    main()
