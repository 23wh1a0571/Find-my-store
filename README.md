# Find-my-store

FindMyStore is an AI-powered shopping assistant web application designed to streamline the retail shopping experience.

---

## Prerequisites

Before running the application, ensure you have the following:

- Python 3.8 or higher installed
- API keys for:
  - Google Gemini LLM (Google AI language model)
  - Google Maps API (for store location and navigation)
- Gmail account credentials for sending email alerts

**Note:** Create a `.env` file to store your API keys and credentials securely. Do not commit this file to version control.
  
---

## Features

- Find nearby stores by city and category
- Compare product prices across multiple stores
- Optimize shopping lists with budget mode
- Real-time stock and deal alerts with email notifications
- Upload PDF/DOCX/TXT documents for AI-assisted Q&A using RAG
- Interactive AI chatbot with store tools and document context

---

## Tech Stack

| Layer         | Technology                                                                 |
|---------------|----------------------------------------------------------------------------|
| Backend       | ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)               |
| Frontend      | ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)        |
| AI / ML       | ![LangChain](https://img.shields.io/badge/LangChain-000000?logo=python&logoColor=white)           |
| Language Model| ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?logo=google&logoColor=white)  |
| Maps API     | ![Google Maps API](https://img.shields.io/badge/Google%20Maps-blue?logo=googlemaps&logoColor=white)|
| Database      | ![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)                  |
| Vector Search | ![FAISS](https://img.shields.io/badge/FAISS-000000?logo=python&logoColor=white)                    |
| Email Service | ![SMTP Gmail](https://img.shields.io/badge/SMTP%20Gmail-D14836?logo=gmail&logoColor=white)          |
| Env Management| ![dotenv](https://img.shields.io/badge/dotenv-214B8A?logo=python&logoColor=white)                   |
| Document Parsing | ![PyPDF](https://img.shields.io/badge/PyPDF-FF6C37?logo=python&logoColor=white), ![python-docx](https://img.shields.io/badge/python--docx-3566AC?logo=python&logoColor=white) |
| Data Handling | ![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)                   |
| Geo Utility  | ![Geopy](https://img.shields.io/badge/Geopy-60A5FA?logo=python&logoColor=white)                    |
| Tunneling    | ![Pyngrok](https://img.shields.io/badge/Pyngrok-4F46E5?logo=python&logoColor=white)                |
