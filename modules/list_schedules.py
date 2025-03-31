from modules.MongoDBClient import MongoDBClient
import pprint

mongo = MongoDBClient()
schedules = mongo.fetch_schedules()

for schedule in schedules:
    print("\n Title:", schedule["title"])
    print(" Algorithm:", schedule["algorithm"])
    print(" Timestamp:", schedule["timestamp"])
    print(" Schedule:")
    print(schedule["data"])
