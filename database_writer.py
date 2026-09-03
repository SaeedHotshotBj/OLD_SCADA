import time

from queue_manager import data_queue
from database import insert_plc_data


def database_writer():

    while True:

        try:

            item = data_queue.get()

            company_id = item["company_id"]
            timestamp = item["timestamp"]
            values = item["values"]


            insert_plc_data(
                company_id,
                timestamp,
                values
            )


            print(
                "DATABASE SAVED:",
                company_id,
                values
            )


            data_queue.task_done()


        except Exception as e:

            print(
                "Database Writer Error:",
                e
            )


        time.sleep(0.01)