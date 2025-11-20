# smart-diet-planner
AI nutrition assistant using Dialogflow + Python
1. Project Overview

The Smart Diet Planner is an AI-powered nutrition assistant designed to help users make healthier food choices. The system utilizes Dialogflow for natural language understanding and a Python Flask webhook to generate meal plans, provide nutritional information, and create grocery lists. This project was developed as part of Senior Project II at the University of the District of Columbia.

2. Features

Meal plan generation (daily, weekly, vegan, low-carb, high-protein, etc.)

Nutrition information for individual foods and meals

Automated grocery list suggestions

Healthy snack ideas

Dialogflow-trained intents and entities for nutrition topics

Optional API integration (Spoonacular or alternative nutrition APIs)

Front-end demo using a web page with Dialogflow Messenger

Backend Flask webhook (running locally or deployed)

3. Project Structure
smart-diet-planner/
│
├── backend/
│     app.py
│
├── frontend/
│     index.html
│
├── docs/
│     Senior_Project_Proposal.pdf
│     Senior_Project_Presentation.pptx
│     Screenshots/
│
└── README.md

4. Technologies Used

Dialogflow ES

Python Flask

HTML/CSS

Optional API (Spoonacular or alternative free API)

GitHub for hosting and version control

5. How It Works (High-Level)

The user interacts with the chatbot through the website or Dialogflow console.

Dialogflow recognizes the intent and extracts parameters such as diet type, number of days, or meal type.

The webhook (app.py) processes the request.

The webhook either returns a hardcoded response or queries an external nutrition API.

Dialogflow displays the final answer to the user.

6. How to Run the Backend (Flask)

Install Python (3.9+ recommended).

Install Flask:

pip install flask


Save the webhook file as app.py.

Run the webhook using:

python app.py


Use a tool like ngrok if Dialogflow requires a public URL.

7. How to Test the Frontend

Open index.html in any browser.

The Dialogflow Messenger widget will load.

Interact with the chatbot to test meal plans, nutrition info, and grocery lists.

8. Screenshots Included

The repository includes screenshots showing:

Dialogflow intent setup

Entity creation

Training phrases

Webhook configuration

Flask backend code

Front-end preview of the chatbot

Successful test results

9. Current Status

Dialogflow intents created and functioning

Webhook code working with static responses

Optional API connection in progress

Presentation completed

The project is ready for continued improvements

10. Future Improvements

Full API integration for dynamic recipes

User accounts and saved meal plans

Calorie tracking dashboard

Mobile-friendly UI

Enhanced nutrition database

11. Author

Developed by Maxzine Reid
University of the District of Columbia
Senior Project II














