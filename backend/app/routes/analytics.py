from fastapi import FastAPI, HTTPException, Path, Query , Header
from datetime import date
import json
from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from app.utils.data import load_data, save_data

app = FastAPI()

def get_filtered_expenses():
    pass

@app.get("/analytics/average-daily-spend")
def daily_average_spent():
    pass

@app.get("/analytics/month-over-month")
def month_over_month_comparing():
    pass

@app.get("/analytics/highest-spending-day")
def highest_spending_in_day():
    pass
