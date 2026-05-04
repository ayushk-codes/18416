import requests

ACCESS_CODE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJNYXBDbGFpbXMiOnsiYXVkIjoiaHR0cDovLzIwLjI0NC41Ni4xNDQvZXZhbHVhdGlvbi1zZXJ2aWNlIiwiZW1haWwiOiJheXVzaGtkZXYyNUBnbWFpbC5jb20iLCJleHAiOjE3Nzc4Nzc3NzMsImlhdCI6MTc3Nzg3Njg3MywiaXNzIjoiQWZmb3JkIE1lZGljYWwgVGVjaG5vbG9naWVzIFByaXZhdGUgTGltaXRlZCIsImp0aSI6IjMzZjM3M2I5LTRhMzgtNDRiNS1hMTI1LTdhYjUyYWQ5Y2I4NCIsImxvY2FsZSI6ImVuLUlOIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwic3ViIjoiNDg1ZWE5Y2UtMTFhNi00MGZjLTk3ODktNzJmM2I0YzlkMDFhIn0sImVtYWlsIjoiYXl1c2hrZGV2MjVAZ21haWwuY29tIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwicm9sbE5vIjoiMTg0MTYiLCJhY2Nlc3NDb2RlIjoidWtzZFdUIiwiY2xpZW50SUQiOiI0ODVlYTljZS0xMWE2LTQwZmMtOTc4OS03MmYzYjRjOWQwMWEiLCJjbGllbnRTZWNyZXQiOiJHeFdyekdHWmtqcHlac3lTIn0.fG4ZUmvQX43Ii-uVC3oqX2NZ_bnt4eWEI9HwPkZG29k"

def Log(stack: str, level: str, package: str, message: str):
    response = requests.post(
        "http://20.207.122.201/evaluation-service/logs",
        json={
            "stack": stack,
            "level": level,
            "package": package,
            "message": message
        },
        headers={
            "Authorization": f"Bearer {ACCESS_CODE}",
            "Content-Type": "application/json"
        },
        timeout=3
    )
    return response.json()