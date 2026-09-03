import time

from database import get_connection


def cleanup_old_trends():

    while True:

        try:

            conn = get_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM TrendLog
                WHERE Timestamp <
                DATEADD(day,-90,GETDATE())
                """
            )

            conn.commit()

            conn.close()

            print(
                "OLD TREND DATA DELETED"
            )

        except Exception as e:

            print(
                "CLEANUP ERROR:",
                e
            )

        time.sleep(86400)