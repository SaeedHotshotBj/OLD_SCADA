from functools import wraps
from flask import session, redirect


def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function



def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")


        if session.get("role") != "admin":

            return "Access Denied: Admin Only", 403


        return f(*args, **kwargs)


    return decorated_function




def master_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")


        if session.get("role") != "Master":

            return """
            <h2 style='color:red;text-align:center'>
            Master Access Only
            </h2>
            """,403


        return f(*args, **kwargs)


    return wrapper