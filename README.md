# Factline API

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)](https://www.postgresql.org/)

---

**Factline is a powerful backend service designed to analyze news articles, assess their credibility, and combat misinformation. It uses AI to perform in depth analysis, providing valuable insights into news content.**

The project also includes a fun, interactive game to help users learn to distinguish between real and fake news.

## ✨ Key Features

* **AI Powered News Analysis:** Automatically analyzes news articles to generate a credibility score, identify bias, sentiment, and potential risks.
* **In depth Claim Verification:** Extracts key claims from articles and uses web searches to find supporting evidence and fact checks.
* **Rich Data Extraction:** Identifies red flags, trust signals, and relevant tags for each article.
* **User Engagement System:** Includes features for upvoting, downvoting, and tracking views to rank and recommend content.
* **"Real or Fake" News Game:** An interactive game that challenges users to differentiate between genuine and AI-doctored news articles.
* **Secure Authentication:** JWT based authentication for user sign up, sign in, and session management.
* **Role-Based Access Control:** Differentiates between regular users and editors with specific permissions.
* **Asynchronous Task Processing:** Uses background tasks for intensive analysis, ensuring the API remains responsive.

## 🚀 Getting Started

Follow these instructions to get a local copy of the project up and running for development and testing purposes.

### Prerequisites

* Python 3.9+
* PostgreSQL Database
* API Keys for Google, Tavily, and NewsAPI

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/pratyakshkwatra/factline_backend.git](https://github.com/pratyakshkwatra/factline_backend.git)
    cd factline_backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**
    * Create a `.env` file in the root directory by copying the example file:
        ```bash
        cp .env.example .env
        ```
    * Update the `.env` file with your specific configurations:
        ```dotenv
        DATABASE_URL="postgresql://factline_user:yourpassword@localhost:5432/factline"
        SECRET_KEY="<your_strong_secret_key>"
        GOOGLE_API_KEY="<your_google_ai_api_key>"
        TAVILY_API_KEY="<your_tavily_search_api_key>"
        NEWS_API_KEY="<your_newsapi_org_key>"
        ```

5.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

## 📖 API Endpoints Overview

The API is structured into three main sections: **Auth**, **Posts**, and **Game**.

### Authentication (`/auth`)

* `POST /auth/sign_up`: Register a new user.
* `POST /auth/sign_in`: Log in and receive JWT tokens.
* `POST /auth/refresh_token`: Refresh an expired access token.
* `POST /auth/sign_out`: Log out and blacklist tokens.

### Posts (`/posts`)

* `POST /posts/`: Create a new post for analysis (Editor only).
* `DELETE /posts/{post_id}`: Delete a post (Editor only).
* `GET /posts/{post_id}/status`: Check the analysis status of a post.
* `POST /posts/{post_id}/upvote`: Upvote a post.
* `POST /posts/{post_id}/downvote`: Downvote a post.
* `POST /posts/{post_id}/view`: Record a view for a post.
* `GET /posts/breaking-news`: Get a ranked list of top/breaking news.
* `GET /posts/recommendations`: Get personalized post recommendations.

### Game (`/game`)

* `POST /game/generate`: Generate a new article for the "Real or Fake" game, which may be real or AI-altered.

---

<p align="center">
  Made with 💜 by The Factline Team.
  <br>
  Fueled by ☕, powered by 🚀, and sprinkled with a bit of ✨ magic.
</p>