# Chattrix - Flask SocketIO Chat App

Chattrix is a simple real-time chat application built with Flask, Flask-SocketIO, and SQLite. It features user registration, login, and a live chat room with a modern UI.

## Features

- User registration and login
- Real-time messaging using WebSockets (Socket.IO)
- SQLite database for storing users and messages
- Responsive and modern UI with custom CSS

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
   Visit [http://localhost:5000](http://localhost:5000)

## Usage

- Register a new account.
- Log in with your credentials.
- Start chatting in the chat room!

## File Overview

- [`app.py`](app.py): Main Flask application with routes, models, and SocketIO logic.
- [`static/style.css`](static/style.css): Custom styles for the UI.
- [`templates/base.html`](templates/base.html): Base HTML template.
- [`templates/login.html`](templates/login.html): Login page.
- [`templates/register.html`](templates/register.html): Registration page.
- [`templates/chat.html`](templates/chat.html): Chat room page.

## License

MIT License
