from flask import Flask, render_template, flash
from flask_toastr import *

app = Flask(__name__)
app.secret_key = 'secret'
toastr = Toastr(app)

@app.route('/')
def index():
    flash('Hello world!', 'success')
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)