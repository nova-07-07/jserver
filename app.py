from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson import ObjectId
import datetime, requests

app = Flask(__name__)

# ================= MONGODB =================
MONGO_URI = "mongodb+srv://jsswater2025:nova2346@jsswater.sal0vb5.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)
db = client["jsswater"]
collection = db["entries"]

# ================= HELP =================
def count_empty(date, fname, count):
    return collection.count_documents({
        "date": date,
        "filling_name": fname,
        "filling_count": int(count),
        "name": "",
        "load": "",
        "empty": "",
        "amount": ""
    })

# ================= DROPDOWN =================
def get_names():
    try:
        return requests.get(
            "https://raw.githubusercontent.com/nova-07-07/rawData/refs/heads/main/data.json"
        ).json()
    except:
        return []

# ================= MAIN =================
@app.route("/")
def index():

    rows = list(collection.find().sort([
        ("date", -1),
        ("filling_count", -1)
    ]))

    grouped = {}

    for r in rows:
        date = r.get("date")
        fname = r.get("filling_name")
        count = int(r.get("filling_count"))

        grouped.setdefault(date, {}).setdefault(fname, {}).setdefault(count, []).append(r)

    # sort counts DESC
    for date in grouped:
        for fname in grouped[date]:
            grouped[date][fname] = dict(
                sorted(grouped[date][fname].items(), reverse=True)
            )

    return render_template("index.html", data=grouped)

# ================= CREATE =================
@app.route("/create_filling", methods=["POST"])
def create_filling():

    fname = request.form.get("filling_name") or "nova"
    raw_date = request.form.get("date")

    # normalize date
    if raw_date:
        date = datetime.datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    else:
        date = datetime.datetime.now().strftime("%d/%m/%Y")

    # count per date
    last = collection.find_one(
        {"filling_name": fname, "date": date},
        sort=[("filling_count", -1)]
    )

    count = last["filling_count"] + 1 if last else 1

    now = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

    collection.insert_one({
        "date": date,
        "filling_name": fname,
        "filling_count": count,
        "name": "",
        "load": "",
        "empty": "",
        "amount": "",
        "time": now
    })

    return redirect(url_for("edit", date=date.replace("/", "-"), fname=fname, count=count))

# ================= EDIT =================
@app.route("/edit/<path:date>/<fname>/<count>")
def edit(date, fname, count):

    date = date.replace("-", "/")
    count = int(count)

    rows = list(collection.find({
        "date": date,
        "filling_name": fname,
        "filling_count": count
    }))

    # ensure at least 1 empty row
    if count_empty(date, fname, count) == 0:
        collection.insert_one({
            "date": date,
            "filling_name": fname,
            "filling_count": count,
            "name": "",
            "load": "",
            "empty": "",
            "amount": "",
            "time": ""
        })

        rows = list(collection.find({
            "date": date,
            "filling_name": fname,
            "filling_count": count
        }))

    return render_template("edit.html",
        rows=rows,
        date=date,
        fname=fname,
        count=count,
        names=get_names()
    )

# ================= ADD ROW =================
@app.route("/add_row", methods=["POST"])
def add_row():

    date = request.form["date"]
    fname = request.form["fname"]
    count = int(request.form["count"])

    # limit 2 empty rows
    if count_empty(date, fname, count) >= 2:
        return "LIMIT"

    result = collection.insert_one({
        "date": date,
        "filling_name": fname,
        "filling_count": count,
        "name": "",
        "load": "",
        "empty": "",
        "amount": "",
        "time": ""
    })

    return str(result.inserted_id)

# ================= UPDATE =================
@app.route("/update/<id>", methods=["POST"])
def update(id):

    collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "name": request.form.get("name",""),
            "load": request.form.get("load",""),
            "empty": request.form.get("empty",""),
            "amount": request.form.get("amount",""),
            "time": request.form.get("time","")
        }}
    )

    return "OK"

# ================= DELETE FILLING =================
@app.route("/delete_filling", methods=["POST"])
def delete_filling():

    date = request.form.get("date")
    fname = request.form.get("fname")
    count = int(request.form.get("count"))

    collection.delete_many({
        "date": date,
        "filling_name": fname,
        "filling_count": count
    })

    return "OK"

# ================= DELETE ROW =================
@app.route("/delete_row", methods=["POST"])
def delete_row():

    id = request.form.get("id")

    collection.delete_one({
        "_id": ObjectId(id)
    })

    return "OK"

# ================= RUN =================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)