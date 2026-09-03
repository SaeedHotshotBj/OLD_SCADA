import time
from datetime import datetime, timezone

import requests

from config import (
    COMPANY_ID,
    PLC_ID,
    PLC_IP,
    PLC_PORT,
    SLAVE_ID,
    SERVER_URL,
    EDGE_TOKEN,
    READ_START,
    READ_COUNT,
    READ_INTERVAL,
    COMMAND_INTERVAL,
    HEARTBEAT_INTERVAL,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
)
from plc import read_registers, write_register, write_registers


SESSION = requests.Session()
SESSION.headers.update({
    "Content-Type": "application/json",
    "X-Edge-Token": EDGE_TOKEN,
})


last_heartbeat = 0


def post_json(path, payload):
    url = SERVER_URL.rstrip("/") + path
    try:
        response = SESSION.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json() if response.content else {}
    except Exception as exc:
        print("SERVER ERROR:", exc)
        return None


def send_plc_data(values):
    payload = {
        "company_id": COMPANY_ID,
        "plc_id": PLC_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "values": values,
    }
    return post_json("/api/edge/data", payload)


def heartbeat():
    payload = {
        "company_id": COMPANY_ID,
        "plc_id": PLC_ID,
        "plc_ip": PLC_IP,
        "plc_port": PLC_PORT,
        "slave_id": SLAVE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return post_json("/api/edge/heartbeat", payload)


def process_commands():
    url = SERVER_URL.rstrip("/") + "/api/edge/commands"
    try:
        response = SESSION.get(
            url,
            params={"company_id": COMPANY_ID, "plc_id": PLC_ID},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json() or {}
    except Exception as exc:
        print("COMMAND SERVER ERROR:", exc)
        return

    commands = data.get("commands", [])
    for command in commands:
        command_id = command.get("id")
        operation = command.get("operation")
        address = command.get("address")

        ok = False
        message = "Unknown command"

        if operation == "write_register":
            ok, message = write_register(
                PLC_IP, PLC_PORT, SLAVE_ID, address, command.get("value", 0)
            )
        elif operation == "write_registers":
            ok, message = write_registers(
                PLC_IP, PLC_PORT, SLAVE_ID, address, command.get("values", [])
            )
        else:
            message = "Unsupported operation"

        post_json("/api/edge/command-result", {
            "id": command_id,
            "company_id": COMPANY_ID,
            "plc_id": PLC_ID,
            "success": ok,
            "message": message,
        })

        print(
            "WRITE:", operation,
            "address=", address,
            "success=", ok,
            "message=", message,
        )


def main():
    print("SCADA EDGE STARTED")
    print("PLC:", PLC_IP, PLC_PORT, "SLAVE:", SLAVE_ID)
    print("SERVER:", SERVER_URL)
    print("COMPANY_ID:", COMPANY_ID, "PLC_ID:", PLC_ID)

    global last_heartbeat
    next_read = 0
    next_command = 0

    while True:
        now = time.monotonic()

        if now >= next_read:
            values = read_registers(
                PLC_IP, PLC_PORT, SLAVE_ID, READ_START, READ_COUNT
            )
            if values is not None:
                print("READ OK:", len(values), "registers")
                send_plc_data(values)
            else:
                print("READ FAILED")
            next_read = now + READ_INTERVAL

        if now >= next_command:
            process_commands()
            next_command = now + COMMAND_INTERVAL

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            heartbeat()
            last_heartbeat = now

        time.sleep(0.05)


if __name__ == "__main__":
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("SCADA EDGE STOPPED")
            break
        except Exception as exc:
            print("EDGE FATAL ERROR:", exc)
            time.sleep(RETRY_DELAY)
