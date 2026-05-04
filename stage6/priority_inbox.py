import heapq
import requests
from datetime import datetime

ACCESS_CODE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJNYXBDbGFpbXMiOnsiYXVkIjoiaHR0cDovLzIwLjI0NC41Ni4xNDQvZXZhbHVhdGlvbi1zZXJ2aWNlIiwiZW1haWwiOiJheXVzaGtkZXYyNUBnbWFpbC5jb20iLCJleHAiOjE3Nzc4Nzc3NzMsImlhdCI6MTc3Nzg3Njg3MywiaXNzIjoiQWZmb3JkIE1lZGljYWwgVGVjaG5vbG9naWVzIFByaXZhdGUgTGltaXRlZCIsImp0aSI6IjMzZjM3M2I5LTRhMzgtNDRiNS1hMTI1LTdhYjUyYWQ5Y2I4NCIsImxvY2FsZSI6ImVuLUlOIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwic3ViIjoiNDg1ZWE5Y2UtMTFhNi00MGZjLTk3ODktNzJmM2I0YzlkMDFhIn0sImVtYWlsIjoiYXl1c2hrZGV2MjVAZ21haWwuY29tIiwibmFtZSI6ImF5dXNoIGt1bWFyIiwicm9sbE5vIjoiMTg0MTYiLCJhY2Nlc3NDb2RlIjoidWtzZFdUIiwiY2xpZW50SUQiOiI0ODVlYTljZS0xMWE2LTQwZmMtOTc4OS03MmYzYjRjOWQwMWEiLCJjbGllbnRTZWNyZXQiOiJHeFdyekdHWmtqcHlac3lTIn0.fG4ZUmvQX43Ii-uVC3oqX2NZ_bnt4eWEI9HwPkZG29k"

WEIGHT = {
    "Placement": 3,
    "Result": 2,
    "Event": 1
}

def fetch_notifications():
    response = requests.get(
        "http://20.207.122.201/evaluation-service/notifications",
        headers={"Authorization": "Bearer " + ACCESS_CODE},
        timeout=5
    )
    response.raise_for_status()
    data = response.json()
    return data.get("notifications", data)

def score(notification):
    weight = WEIGHT.get(notification["Type"], 0)
    timestamp = int(datetime.strptime(notification["Timestamp"], "%Y-%m-%d %H:%M:%S").timestamp())
    return weight * 1000000 + timestamp

def get_top_n(notifications, n=10):
    heap = []
    for notif in notifications:
        s = score(notif)
        if len(heap) < n:
            heapq.heappush(heap, (s, notif))
        elif s > heap[0][0]:
            heapq.heapreplace(heap, (s, notif))
    return [notif for _, notif in sorted(heap, reverse=True)]

def main():
    notifications = fetch_notifications()
    print("Total notifications fetched:", len(notifications))

    top10 = get_top_n(notifications, n=10)

    print("\nTop 10 Priority Notifications:\n")
    for i, notif in enumerate(top10, 1):
        print(str(i) + ". [" + notif["Type"] + "] " + notif["Message"] + " — " + notif["Timestamp"])

if __name__ == "__main__":
    main()