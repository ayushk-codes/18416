import heapq
import requests
from datetime import datetime

ACCESS_CODE = "YOUR_EXAM_ACCESS_CODE_HERE"

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