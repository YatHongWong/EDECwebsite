import sqlite3
from flask import Flask, redirect, render_template, request, session
from flask_session import Session

app = Flask(__name__)