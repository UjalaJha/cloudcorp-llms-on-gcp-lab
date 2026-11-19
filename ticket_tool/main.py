import functions_framework
from flask import jsonify

MOCK_TICKETS = {
    "INC-402": {
        "status": "In Progress",
        "assigned_to": "Hardware Desk",
        "category": "Hardware Repair",
        "summary": "Laptop keyboard key stuck",
        "eta": "Tomorrow 2:00 PM"
    },
    "INC-105": {
        "status": "Resolved",
        "assigned_to": "Network Ops",
        "category": "VPN Access",
        "summary": "Remote VPN gateway connectivity reset",
        "eta": "Completed"
    },
    "INC-889": {
        "status": "Pending Approval",
        "assigned_to": "IT Security",
        "category": "Access Request",
        "summary": "Production BigQuery dataset read grant",
        "eta": "Within 24 hours"
    }
}

TICKET_COUNTER = 501

@functions_framework.http
def handle_it_ticket(request):
    """
    Cloud Function supporting both:
    1. Creating a new hardware replacement request (action='create' or 'summary' provided)
    2. Querying status of an existing ticket (action='check' or 'ticket_id' provided)
    """
    global TICKET_COUNTER
    request_json = request.get_json(silent=True) or {}
    request_args = request.args or {}
    
    action = request_json.get("action") or request_args.get("action")
    ticket_id = request_json.get("ticket_id") or request_args.get("ticket_id")
    summary = request_json.get("summary") or request_args.get("summary")
    
    # Action 1: Create a new hardware replacement ticket
    if action == "create" or (summary and not ticket_id):
        new_id = f"INC-{TICKET_COUNTER}"
        TICKET_COUNTER += 1
        
        record = {
            "ticket_id": new_id,
            "status": "Created (Approved for Loaner)",
            "category": request_json.get("category", "Hardware Replacement"),
            "summary": summary or "Broken laptop screen replacement request",
            "assigned_to": "Hardware Fulfillment Desk (Floor 2)",
            "priority": request_json.get("priority", "High (P2)"),
            "eta": "Within 24 hours",
            "instructions": "Present this ticket ID at Floor 2 Tech Depot for your emergency loaner unit."
        }
        MOCK_TICKETS[new_id] = record
        return jsonify(record), 201

    # Action 2: Check status of existing ticket
    if ticket_id or action == "check":
        if not ticket_id:
            return jsonify({"error": "Missing ticket_id parameter"}), 400
        
        tid = ticket_id.upper()
        record = MOCK_TICKETS.get(tid)
        if record:
            return jsonify({"ticket_id": tid, **record}), 200
        else:
            return jsonify({
                "ticket_id": tid,
                "status": "Not Found",
                "message": f"No ticket record found matching {tid}"
            }), 404

    return jsonify({
        "error": "Invalid request. Provide either 'summary' to create a ticket or 'ticket_id' to check status."
    }), 400
