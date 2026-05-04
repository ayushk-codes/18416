import requests
from fastapi import FastAPI, Request
from logger import Log

app = FastAPI()

ACCESS_CODE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJNYXBDbGFpbXMiOnsiYXVkIjoiaHR0cDovLzIwLjI0NC41Ni4xNDQvZXZhbHVhdGlvbi1zZXJ2aWNlIiwiZW1haWwiOiJheXVzaGtkZXYyNUBnbWFpbC5jb20iLCJleHAiOjE3Nzc4Nzc3NzMsImlhdCI6MTc3Nzg3Njg3MywiaXNzIjoiQWZmb3JkIE1lZGljYWwgVGVjaG5vbG9naWVzIFByaXZhdGUgTGltaXRlZCIsImp0aSI6IjMzZjM3M2I5LTRhMzgtNDRiNS1hMTI1LTdhYjUyYWQ5Y2I4NCIsImxvY2FsZSI6ImVuLUlOIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwic3ViIjoiNDg1ZWE5Y2UtMTFhNi00MGZjLTk3ODktNzJmM2I0YzlkMDFhIn0sImVtYWlsIjoiYXl1c2hrZGV2MjVAZ21haWwuY29tIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwicm9sbE5vIjoiMTg0MTYiLCJhY2Nlc3NDb2RlIjoidWtzZFdUIiwiY2xpZW50SUQiOiI0ODVlYTljZS0xMWE2LTQwZmMtOTc4OS03MmYzYjRjOWQwMWEiLCJjbGllbnRTZWNyZXQiOiJHeFdyekdHWmtqcHlac3lTIn0.fG4ZUmvQX43Ii-uVC3oqX2NZ_bnt4eWEI9HwPkZG29k"
HEADERS = {"Authorization": f"Bearer {ACCESS_CODE}"}

@app.middleware("http")
async def student_logger(request: Request, call_next):
    Log("backend", "info", "middleware", "Started: " + request.method + " " + request.url.path)
    response = await call_next(request)
    Log("backend", "info", "middleware", "Finished with status " + str(response.status_code))
    return response

@app.get("/schedule")
def generate_schedule():
    Log("backend", "info", "controller", "Fetching depots and vehicles")

    try:
        depots_req = requests.get("http://20.207.122.201/evaluation-service/depots", headers=HEADERS, timeout=5)
        vehicles_req = requests.get("http://20.207.122.201/evaluation-service/vehicles", headers=HEADERS, timeout=5)

        if depots_req.status_code != 200:
            Log("backend", "error", "controller", "Depots fetch failed: " + depots_req.text)
            return {"status": "error", "message": "Depots API returned " + str(depots_req.status_code)}

        if vehicles_req.status_code != 200:
            Log("backend", "error", "controller", "Vehicles fetch failed: " + vehicles_req.text)
            return {"status": "error", "message": "Vehicles API returned " + str(vehicles_req.status_code)}

        depots_data = depots_req.json()
        vehicles_data = vehicles_req.json()

        depots = depots_data.get("depots", depots_data) if isinstance(depots_data, dict) else depots_data
        vehicles = vehicles_data.get("vehicles", vehicles_data) if isinstance(vehicles_data, dict) else vehicles_data

    except Exception as e:
        Log("backend", "error", "controller", "Fetch failed: " + str(e))
        return {"status": "error", "message": "Code crashed: " + str(e)}

    results = []

    Log("backend", "info", "controller", "Running scheduling algorithm")

    for depot in depots:
        budget = depot["MechanicHours"]
        dp = [[0, [], 0] for _ in range(budget + 1)]

        for vehicle in vehicles:
            task_id = vehicle["TaskID"]
            cost = vehicle["Duration"]
            impact = vehicle["Impact"]

            for w in range(budget, cost - 1, -1):
                if dp[w - cost][0] + impact > dp[w][0]:
                    dp[w] = [
                        dp[w - cost][0] + impact,
                        dp[w - cost][1] + [task_id],
                        dp[w - cost][2] + cost
                    ]

        results.append({
            "DepotID": depot["ID"],
            "MechanicHoursBudget": budget,
            "TotalMechanicHoursUsed": dp[budget][2],
            "TotalOperationalImpact": dp[budget][0],
            "TasksSelected": dp[budget][1]
        })

    Log("backend", "info", "controller", "Schedules created successfully")
    return {"status": "success", "data": results}