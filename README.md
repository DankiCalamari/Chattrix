# Chattrix - Flask SocketIO Chat App

Chattrix is a real-time chat application built with Flask, Flask-SocketIO, and SQLite. It supports user registration, login, and a live chat room with a responsive UI.

## Features

- User registration and authentication
- Real-time messaging via WebSockets (Socket.IO)
- SQLite database for users and messages
- Responsive UI with custom CSS
- Persistent chat history

## Project Structure

```
app.py
instance/
    db.sqlite3
static/
    style.css
templates/
    base.html
    chat.html
    login.html
    register.html
```

## Setup & Run

1. **Install dependencies:**
    ```sh
    pip install flask flask_sqlalchemy flask_socketio
    ```

2. **Run the app:**
    ```sh
    python app.py
    ```

3. **Open your browser:**  
   Go to [http://localhost:5000](http://localhost:5000)

## Usage

- Register a new account.
- Log in with your credentials.
- Join the chat room and start messaging!

## File Overview

- [`app.py`](app.py): Main Flask app, database models, routes, and SocketIO events.
- [`static/style.css`](static/style.css): Custom styles for the chat UI.
- [`templates/base.html`](templates/base.html): Base HTML template.
- [`templates/login.html`](templates/login.html): Login page.
- [`templates/register.html`](templates/register.html): Registration page.
- [`templates/chat.html`](templates/chat.html): Chat room page.

## License

This project is licensed under the MIT License.
