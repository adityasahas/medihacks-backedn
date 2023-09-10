from flask import Flask, jsonify
from pymongo import MongoClient
import openai
import random
from datetime import datetime, timedelta
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.getenv("MONGODBURI"))
db = client["medsched"]
collection = db["collectdeeznuts"]
apptcollection = db["appointments"]
openai.api_key = os.getenv("OPENAI_API_KEY")
latestschedule = db["latestschedule"]

@app.route("/generate_schedule", methods=["GET"])
def generate_schedule():
    data = collection.find_one({"email": "receptionist@doctor.com"})
    num_exam_rooms = data.get("examroom")
    doctors = data.get("doctors", [])
    nurses = data.get("nurses", [])
    nurse_practitioners = data.get("nursePractitioners", [])

    processed_schedule = []

    def create_prompt(appts):
        prompt = "Given the following medical appointments, sort ALL of them into a schedule that prioritizes urgency and aligns with staff specialties for the next week:\n"
        for appt in appts:
            prompt += f"Patient: {appt['patientName']}, Phone:{appt['phoneNumber']}, Email: {appt['email']}, Nature: {appt['nature']}, Preferred Time: {appt['preferredTime']}, Reason for Visit: {appt['reason']}\n"

            prompt += f"\nNumber of exam rooms: {num_exam_rooms}\n"
            prompt += "Doctors available: " + ", ".join([doc["name"] for doc in doctors]) + "\n"
            prompt += (
                "Nurse Practitioners available: "
                + ", ".join([np["name"] for np in nurse_practitioners])
                + "\n"
            )
            prompt += (
                "Nurses available: " + ", ".join([nurse["name"] for nurse in nurses]) + "\n"
            )
            prompt += "\nWhen generating the schedule, make sure the doctors and nurse practitioners have breaks for lunch so they don't get hungry."
            prompt += "\nGenerate a JSON schedule for the next 5 days (today is september 10th 2023), each appointment should have the Doctor or Nurse Practitioner or Nurse name, the time and date of appointment in the object start_time (format it in %Y-%m-%dT%H:%M) (office is open 9 am to 5 pm and also randomise the time so it is not in 30 minutes factoring in urgency of the appointment), exam room number, and of course all the patient info, and also a very short doctor's note that the patient should follow before meeting, make it detailed and give unique advice."
            prompt += "\nFor the time of the appointment, use the preferred time of the patient and if it is not available include a 'change_reason' object to give a explanation why the preferred time wasn't used, but don't be repetitive for the reason, be very creative with why there was a change in time. ONLY FOR THE DEMO OF THE PRODUCT, make TWO appointments not use the preferred time and give a reason why it wasn't available and it had to be changed in very technical terms, don't give a generic reason; be creative as possible. For the ones that the preferred time is available, make reason Preferred Time Available."
            prompt += "\nFor the nature of the appointment, use the reason for visit of the patient but summarized, this should be object nature."
            prompt += "\nFor the object names in the json, use the following: start_time, email, exam_room, provider, patient, urgency, type, nature, change_reason, doctors_note, phoneNumber. INCLUDE ALL OF THEM, even if they are empty, just make sure they are there."
            prompt += "\nGenerate a consistent JSON output to represent the schedule, only send the FULL json and no text message as this is an api call that parses json only, also make sure you send it all in one message, so if you stop automatically continue the message. DONT STOP BECAUSE OF LENGTH.\n"
        

        return prompt

    appointmentsdata = list(apptcollection.find({}))

    chunk_size = 10
    for i in range(0, len(appointmentsdata), chunk_size):
        chunked_data = appointmentsdata[i:i + chunk_size]
        prompt = create_prompt(chunked_data)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates consistent medical schedules as a receptionist for a large office.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=3500,
        )
        gpt_output = response["choices"][0]["message"]["content"].strip()
        gpt_schedule = json.loads(gpt_output).get("schedule", [])
        print(f"gpt_output: {gpt_output}")

        for appointment in gpt_schedule:
            try:
                time = datetime.strptime(appointment["start_time"], "%Y-%m-%dT%H:%M")
            except ValueError:
                time = appointment["start_time"]
            patient = appointment["patient"]
            if "email" in appointment:
                email = appointment["email"]
            else:
                email = "Email not found in appointment"
            urgency = appointment["urgency"]
            nature = appointment.get("nature", "Nature not specified")
            exam_room = appointment["exam_room"]
            change_reason = appointment.get("change_reason", "Preferred Time Available")
            doctors_note = appointment["doctors_note"]
            phone_number = appointment.get("phoneNumber", "Phone number opted out")
            provider = appointment["provider"]            
            processed_appointment = {
                "start_time": time,
                "exam_room": exam_room,
                "provider": provider,
                "patient": patient,
                "email": email,
                "urgency": urgency,
                "nature": nature,
                "change_reason": change_reason,
                "doctors_note": doctors_note,
                "phoneNumber": phone_number,
            }
            
            processed_schedule.append(processed_appointment)

    latestschedule.delete_many({})
    latestschedule.insert_one({"generated_schedule": processed_schedule})

    return jsonify({"generated_schedule": processed_schedule})

if __name__ == "__main__":
    app.run(debug=True)
