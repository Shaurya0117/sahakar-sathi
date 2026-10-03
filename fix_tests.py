
with open("backend/tests/test_bookings.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"client\.patch\(f\"/api/bookings/\{booking_id\}/accept\", headers=auth_header\(wtoken\)\)\n\s+res = client\.patch\(f\"/api/bookings/\{booking_id\}/start\", headers=auth_header\(wtoken\)\)",
    """client.patch(f\"/api/bookings/{booking_id}/accept\", headers=auth_header(wtoken))\n    client.patch(f\"/api/bookings/{booking_id}/arrive\", headers=auth_header(wtoken))\n    res = client.patch(f\"/api/bookings/{booking_id}/start\", headers=auth_header(wtoken))""",
    content
)
content = re.sub(
    r"client\.patch\(f\"/api/bookings/\{booking_id\}/accept\", headers=auth_header\(wtoken\)\)\n\s+client\.patch\(f\"/api/bookings/\{booking_id\}/start\", headers=auth_header\(wtoken\)\)",
    """client.patch(f\"/api/bookings/{booking_id}/accept\", headers=auth_header(wtoken))\n    client.patch(f\"/api/bookings/{booking_id}/arrive\", headers=auth_header(wtoken))\n    client.patch(f\"/api/bookings/{booking_id}/start\", headers=auth_header(wtoken))""",
    content
)
content = re.sub(
    r"client\.patch\(f\"/api/bookings/\{bid\}/accept\", headers=auth_header\(wt\)\)\n\s+st = client\.patch\(f\"/api/bookings/\{bid\}/start\", headers=auth_header\(wt\)\)\.json\(\)",
    """client.patch(f\"/api/bookings/{bid}/accept\", headers=auth_header(wt))\n        client.patch(f\"/api/bookings/{bid}/arrive\", headers=auth_header(wt))\n        st = client.patch(f\"/api/bookings/{bid}/start\", headers=auth_header(wt)).json()""",
    content
)

with open("backend/tests/test_bookings.py", "w", encoding="utf-8") as f:
    f.write(content)

