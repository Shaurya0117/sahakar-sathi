
with open("backend/tests/test_bookings.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"acc = client\.patch\(f\"/api/bookings/\{booking_id\}/accept\", headers=auth_header\(wtoken\)\)\.json\(\)\n\s+assert acc\[\"status\"\] == \"ACCEPTED\"\n\n\s+# 3\. Start \(ACCEPTED -> IN_PROGRESS\)\n\s+st = client\.patch\(f\"/api/bookings/\{booking_id\}/start\", headers=auth_header\(wtoken\)\)\.json\(\)",
    """acc = client.patch(f\"/api/bookings/{booking_id}/accept\", headers=auth_header(wtoken)).json()\n    assert acc[\"status\"] == \"ACCEPTED\"\n\n    arr = client.patch(f\"/api/bookings/{booking_id}/arrive\", headers=auth_header(wtoken)).json()\n    assert arr[\"arrived_at\"] is not None\n\n    # 3. Start (ACCEPTED -> IN_PROGRESS)\n    st = client.patch(f\"/api/bookings/{booking_id}/start\", headers=auth_header(wtoken)).json()""",
    content
)
with open("backend/tests/test_bookings.py", "w", encoding="utf-8") as f:
    f.write(content)

