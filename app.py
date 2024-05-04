import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from cs50 import SQL
import sqlite3
from helper import apology, login_required, usd, compare

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///data.db")
# con = sqlite3.connect("data.db")
# db = con.cursor()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods = ["GET", "POST"])
@login_required
def index():
    months = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]
    today = datetime.date.today()
    if request.method == "POST":
        today = today.replace(month = int(request.form.get("month")))
    current = "%" + today.strftime("%Y-%m") + "%"
    # check = []
    # for x in range(0, 3):
    #     mon = today.month - 2 + x
    #     mon = today.replace(month = mon)
    #     mon = mon.strftime("%Y-%m")
    #     mon = "%" + mon + "%"
    #     check.append(db.execute("SELECT *, SUM(amount) FROM transactions WHERE amount < 0 AND date LIKE ? ", mon))
    #     check1 = check[x][0]
        # if check1["SUM(amount)"] is  None:
        #     check.pop(x)
    # print(check)
    # for x in check:
    #     if x[0]["SUM(amount)"] == None:
    #         check.remove(x)
    # print(check)
    today = today.strftime("%Y-%m")
    print(today)
    print(current)
    spendingChart = db.execute("SELECT *, SUM(amount) FROM transactions WHERE amount < 0 AND user_id = ? AND date LIKE ? GROUP BY type", session["user_id"], current)
    incomeChart = db.execute("SELECT *, SUM(amount) FROM transactions WHERE amount > 0 AND user_id = ? AND date LIKE ? GROUP BY type", session["user_id"], current)
    spending = 0
    income = 0
    for x in spendingChart:
        spending += x["SUM(amount)"]
    for x in incomeChart:
        income += x["SUM(amount)"]
    cashflow = income + spending
    spending *= -1
    if income < spending:
        comment  = "Your should change your spending habit ASAP!!!!"
    elif spending == 0 or income == 0:
        comment = "No record yet!"
    elif (spending / income) * 100 > 60:
        comment = "Your spending is high, should lower your spending"
    elif (spending / income) * 100 < 35:
        comment = "Your expense to spending ratio is good, keep it up!"
    elif (spending / income) * 100 < 50:
        comment = "Your expense to spending ratio is very good, keep it up!"
    print (spendingChart)
    return render_template("index.html", pieChart = spendingChart, incomes = incomeChart, months = months, today = today, cashflow = cashflow, comment = comment)


@app.route("/register", methods=["GET", "POST"])
def register():
    # To check the type of data submitted.
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        rPassword = request.form.get("confirmation")
        existedUser = db.execute("SELECT username FROM users WHERE username = ?", (username))

        if not username:
            return apology("must provide username", 400)
        elif len(existedUser)!=0:
            if username == existedUser[0]["username"]:
                return apology("username is chosen, please choose another one", 400)
        elif not password:
            return apology("must provide password", 400)
        elif not rPassword:
            return apology("must provide repeat password", 400)
        elif password != rPassword:
            return apology("both password and repeat password must match", 400)

        newPass = generate_password_hash(password)

        db.execute("INSERT INTO users(username, hash) VALUES (?, ?)", username, newPass)
        row = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = row[0]["id"]
        print(session)
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/login", methods = ["POST", "GET"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/expenses", methods = ["GET", "POST"])
def expenses():
    spendingType = ["Cars", "Transportation", "Entertainment", "Food", "House", "Bills & Fees", "Travel", "Family", "Healthcare", "Groceries", "Education", "Others"]
    if request.method == "POST":
        date = request.form.get("date")
        type = request.form.get("type")
        amount = request.form.get("amount")
        if compare(type, spendingType) == False:
            flash("Please select a valid spending type")
            return redirect("/expenses")
        print(date)
        if not date:
            date = datetime.date.today()
        if not type:
            flash("Expense type is needed")
            return redirect("/expenses")
        if not amount:
            flash("Amount is needed")
            return redirect("/expenses")

        amount = float(amount) * -1
        db.execute("INSERT INTO transactions (user_id, type, amount, date) VALUES(?, ?, ?, ?)", session["user_id"], type, amount, date)
        flash("Expense recorded succesfully")
        return redirect("/expenses")
    else:
        for x in spendingType:
            print(x)
        return render_template("expenses.html", types = spendingType)


@app.route("/income", methods = ["GET", "POST"])
def income():
    incomeType = ["Salary", "Business", "Gifts", "Side Income", "Loans", "Others"]
    if request.method == "POST":
        date = request.form.get("date")
        type = request.form.get("type")
        amount = request.form.get("amount")
        if compare(type, incomeType) == False:
            flash("Please select a valid income type")
            return redirect("/income")
        print(date)
        if not date:
            date = datetime.date.today()
        if not type:
            flash("Income type is needed")
            return redirect("/income")
        if not amount:
            flash("Amount is needed")
            return redirect("/income")

        amount = float(amount)
        db.execute("INSERT INTO transactions (user_id, type, amount, date) VALUES(?, ?, ?, ?)", session["user_id"], type, amount, date)
        flash("Income recorded succesfully")
        return redirect("/income")
    else:
        for x in incomeType:
            print(x)
        return render_template("income.html", types = incomeType)


@app.route("/history", methods = ["GET", "POST"])
def history():
    months = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]
    today = datetime.date.today()
    if request.method == "POST":
        today = today.replace(month = int(request.form.get("month")))
    current = "%" + today.strftime("%Y-%m") + "%"
    today = today.strftime("%Y-%m")
    spendingHistory = db.execute("SELECT * FROM transactions WHERE amount < 0 AND user_id = ? AND date LIKE ? ", session["user_id"], current)
    incomeHistory = db.execute("SELECT * FROM transactions WHERE amount > 0 AND user_id = ? AND date LIKE ? ", session["user_id"], current)
    # print(spendingHistory)
    # print(incomeHistory)
    return render_template("history.html",spendingHistory = spendingHistory, incomeHistory = incomeHistory, months = months, today = today)


@app.route("/password", methods=["POST", "GET"])
def passwordChange():
    if request.method == "POST":
        password = generate_password_hash(request.form.get("password"))
        newPass = request.form.get("newPassword")
        confirmPass = request.form.get("confirmation")
        checkPass = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])
        # print(newPass)
        # print(confirmPass)
        if not password or not newPass or not confirmPass:
            return apology("Please fill in the blanks!", 400)
        if check_password_hash(checkPass[0]["hash"], request.form.get("password")) == False:
            return apology("Sorry, please try again", 400)
        if newPass != confirmPass:
            return apology("Sorry, please try again", 400)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(newPass), session["user_id"])
        flash("Password changed succesfully!")
        return redirect("/")
    else:
        return render_template("password.html")


@app.route("/delete/<int:id>", methods=["GET"])
def delete_transaction(id):
    db.execute("DELETE FROM transactions WHERE id = ?", id)
    return redirect("/history")