from flask import Flask, request, jsonify
from pymongo import MongoClient, errors
import logging
import os

app = Flask(__name__)

# ---------------- Logging Setup ----------------
LOG_FILE = "app.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------------- MongoDB Setup ----------------
try:
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI)
    logging.info("✅ Fetched MongoDB Credentials.")

    db = client["unisysibmDb"]

    # Collections
    unisyseportal_col = db["unisyseportal"]
    ibmzowe_col = db["ibmzowe"]

    logging.info("✅ Connected to MongoDB successfully.")
except errors.ConnectionFailure as e:
    logging.error(f"❌ MongoDB connection failed: {str(e)}")
    unisyseportal_col = None
    ibmzowe_col = None


# ---------------- Helper: Safe Response ----------------
def safe_response(success: bool, message: str, data=None, code=200):
    resp = {
        "success": success,
        "message": message,
        "data": data if data else {}
    }
    return jsonify(resp), code


# ---------------- APIs ----------------
@app.route("/get/unisys/payroll", methods=["GET"])
def get_payroll():
    try:
        # 🔹 Check MongoDB connection
        client.admin.command("ping")  # raises exception if not connected

        records = list(unisyseportal_col.find({}, {"_id": 0}))
        logging.info("Fetched payroll records.")
        return safe_response(True, "Payroll records fetched", records)

    except Exception as e:
        logging.error(f"Error in /get/unisys/payroll: {str(e)}")
        return safe_response(False, "Error fetching payroll records", code=500)


@app.route("/get/ibm/shipping", methods=["GET"])
def get_shipping():
    try:
        # 🔹 Check MongoDB connection
        client.admin.command("ping")  # raises exception if not connected

        records = list(ibmzowe_col.find({}, {"_id": 0}))
        logging.info("Fetched shipping records.")
        return safe_response(True, "Shipping records fetched", records)

    except Exception as e:
        logging.error(f"Error in /get/shipping: {str(e)}")
        return safe_response(False, "Error fetching shipping records", code=500)


@app.route("/update/unisys/payroll", methods=["POST"])
def update_payroll():
    try:
        # 🔹 Check MongoDB connection
        client.admin.command("ping")  # raises exception if not connected

        data = request.json
        emp_id = data.get("crewMemberId")
        field_path = data.get("field")
        new_value = data.get("value")

        if not emp_id or not field_path:
            return safe_response(False, "Missing required fields", code=400)

        result = unisyseportal_col.update_one(
            {"data.payrollRecords.crewMemberId": emp_id},
            {"$set": {f"data.payrollRecords.$.{field_path}": new_value}}
        )

        logging.info(f"Payroll update: emp_id={emp_id}, field={field_path}, modified={result.modified_count}")
        return safe_response(True, "Payroll updated", {"matched": result.matched_count, "modified": result.modified_count})

    except Exception as e:
        logging.error(f"Error in /update/unisys/payroll: {str(e)}")
        return safe_response(False, "Error updating payroll", code=500)


@app.route("/update/ibm/shipping", methods=["POST"])
def update_shipping():
    try:
        # 🔹 Check MongoDB connection
        client.admin.command("ping")  # raises exception if not connected

        data = request.json
        shipping_id = data.get("shippingId")
        field_path = data.get("field")
        new_value = data.get("value")

        if not shipping_id or not field_path:
            return safe_response(False, "Missing required fields", code=400)

        result = ibmzowe_col.update_one(
            {"shippingPerson.id": shipping_id},
            {"$set": {f"shippingPerson.{field_path}": new_value}}
        )

        logging.info(f"Shipping update: id={shipping_id}, field={field_path}, modified={result.modified_count}")
        return safe_response(True, "Shipping updated", {"matched": result.matched_count, "modified": result.modified_count})

    except Exception as e:
        logging.error(f"Error in /update/IBM/shipping: {str(e)}")
        return safe_response(False, "Error updating shipping", code=500)


# ---------------- Logs Endpoint ----------------
@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        if not os.path.exists(LOG_FILE):
            return safe_response(False, "Log file not found", code=404)

        with open(LOG_FILE, "r") as f:
            logs = f.readlines()[-100:]  # return last 100 lines
        return safe_response(True, "Logs fetched", logs)

    except Exception as e:
        logging.error(f"Error in /logs: {str(e)}")
        return safe_response(False, "Error fetching logs", code=500)


# ---------------- Main ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
