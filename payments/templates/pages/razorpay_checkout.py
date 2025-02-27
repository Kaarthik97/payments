# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import json
 
import frappe
from frappe import _
from frappe.utils import cint, flt, now
from datetime import datetime
import pytz
 
no_cache = 1
 
expected_keys = (
    "amount",
    "title",
    "description",
    "reference_doctype",
    "reference_docname",
    "payer_name",
    "payer_email",
    "order_id",
    "currency",
)
 
 
def get_context(context):
    context.no_cache = 1
    context.api_key = get_api_key()
 
    try:
        doc = frappe.get_doc("Integration Request", frappe.form_dict["token"])
        payment_details = json.loads(doc.data)
 
        for key in expected_keys:
            context[key] = payment_details[key]
 
        context["token"] = frappe.form_dict["token"]
        context["amount"] = flt(context["amount"])
        context["subscription_id"] = (
            payment_details["subscription_id"] if payment_details.get("subscription_id") else ""
        )
 
    except Exception as e:
        frappe.redirect_to_message(
            _("Invalid Token"),
            _("Seems token you are using is invalid!"),
            http_status_code=400,
            indicator_color="red",
        )
 
        frappe.local.flags.redirect_location = frappe.local.response.location
        raise frappe.Redirect
 
 
def get_api_key():
    api_key = frappe.db.get_single_value("Razorpay Settings", "api_key")
    if cint(frappe.form_dict.get("use_sandbox")):
        api_key = frappe.conf.sandbox_api_key
 
    return api_key
 
 
@frappe.whitelist(allow_guest=True)
def make_payment(razorpay_payment_id, options, reference_doctype, reference_docname, token):
    data = {}
 
    if isinstance(options, str):
        data = json.loads(options)
 
    data.update(
        {
            "razorpay_payment_id": razorpay_payment_id,
            "reference_docname": reference_docname,
            "reference_doctype": reference_doctype,
            "token": token,
        }
    )
 
    data = frappe.get_doc("Razorpay Settings").create_request(data)
    frappe.db.commit()
    # print(data)
    if data["status"] == 200 :
        event_form_status_change(reference_doctype,reference_docname)
        update_event_participants(reference_doctype, reference_docname, razorpay_payment_id)
    return data
 
def get_doc(reference_doctype,reference_docname):
    event_doc = frappe.get_doc(reference_doctype, reference_docname)
    return event_doc
 
def event_form_status_change(reference_doctype,reference_docname):
       event_doc = get_doc(reference_doctype,reference_docname)
       event_doc.status = "Paid"
       event_doc.save(ignore_permissions=True)
       
def update_event_participants(reference_doctype,reference_docname, razorpay_payment_id):
        event_form_doc = get_doc(reference_doctype,reference_docname)
        # ist_time_zone = pytz.timezone('Asia/Kolkata')
        now_time = datetime.now()
        # ist_time = ist_time_zone.localize(datetime.now())
        # check_time = str(ist_time)
        # ist_str = check_time.split(".")[0]
        # ist_strp_time = datetime.strptime(ist_str, "%Y-%m-%d %H:%M:%S")
        first_name = event_form_doc.first_name
        email = event_form_doc.email_id
        event_name = event_form_doc.event
        doctype = "Events"
        event_doc = get_doc(doctype, event_name)
        event_child = event_doc.append("participants", {})
        event_child.name1 =  f"{first_name}"
        event_child.email_id = email
        event_child.date = now_time
        event_child.contact_no = event_form_doc.mobile_number
        event_child.transaction_id = razorpay_payment_id
        event_child.paid_status = "Paid"
        event_child.reference_docname = reference_docname
        event_child.save(ignore_permissions=True)
        
        
        