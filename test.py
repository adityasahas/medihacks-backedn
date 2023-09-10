from pymongo import MongoClient
import pprint

client = MongoClient("mongodb+srv://techoptimum:admin%40techoptimum16125@clusterdeeznuts.etvosen.mongodb.net/?retryWrites=true&w=majority")

db = client['medsched']
collection = db['collectdeeznuts']
apptcollection = db['appointments']

data = collection.find_one({"email": "receptionist@doctor.com"})
num_exam_rooms = data.get("examroom", 20)
doctors = data.get("doctors", [])
nurses = data.get("nurses", [])
nurse_practitioners = data.get("nursePractitioners", [])

appointmentsdata = list(apptcollection.find({}))

prompt_base = "Sort the medical appointments by urgency and staff specialty.\n"
appointments_str = "\n".join(f"{appt['patientName']}, {appt['email']}, {appt['nature']}, {appt['preferredTime']}, {appt['reason']}" for appt in appointmentsdata)

rooms_str = f"Exam rooms: {num_exam_rooms}"
doctors_str = f"Docs: {', '.join([doc['name'] for doc in doctors])}"
nps_str = f"NPs: {', '.join([np['name'] for np in nurse_practitioners])}"
nurses_str = f"RNs: {', '.join([nurse['name'] for nurse in nurses])}"

json_keys = "Use keys: start_time, end_time, exam_room, provider, patient, urgency, type, nature, duration"

prompt = "\n".join([prompt_base, appointments_str, rooms_str, doctors_str, nps_str, nurses_str, json_keys])

print("Data from 'collection':")
pprint.pprint(data)

print("\nData from 'apptcollection':")
pprint.pprint(appointmentsdata)

print("\nConstructed Prompt:")
print(prompt)
