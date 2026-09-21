from fastapi import FastAPI, HTTPException, Path, Query , Header
from datetime import date
import json
from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from enum import Enum

app = FastAPI()

class TransactionCategory(str, Enum):
    FOOD="Food"
    TRANSPORT="Transport"
    SALARY="Salary"
    RENT ="Rent"
    UTILITIES="Utilities"
    ENTERTAINMENT="Entertainment"
    HEALTH="Health"
    FREELANCE="Freelance"
    GIFT="Gift"
    SHOPPING="Shopping"
    BONUS="Bonus"
    EDUCATION="Education"
    OTHER="Other"

class BudgetStatusType(str, Enum):
    ON_TRACK="on_track"
    WARNING="warning"
    EXCEEDED= "exceeded"
    
class BudgetCreate(BaseModel):
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(...,description="Amount of transaction", gt=0)
    month: str = Field(...,description="Month of transaction in YYYY-MM format",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    
class Budget(BaseModel):
    user_id:str
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(...,description="Amount of transaction", gt=0)
    period: Literal["monthly"]
    month: str = Field(...,description="Month of transaction in YYYY-MM format",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    created_at:date
    
class BudgetStatus(BaseModel):
    budget_id: str
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    budget_amount: float=Field(...,description="Amount of transaction", gt=0)
    spent_amount: float=Field(...,description="How much spent amount", ge=0)
    remaining_amount: float=Field(description="Remaining amount")
    percentage_used:float=Field(description="Percentage of spent amount")
    status:Annotated[BudgetStatusType, Field(..., description="Status of amount used ")]
    
def load_data():
    with open("./data/transactions.json", "r") as f:
        data = json.load(f)
        return data

def save_data(data):
    with open('./data/transactions.json','w') as f:
        json.dump(data, f, indent=4)

def generate_budget_id(data,user_id: str) -> str:
    numbers = []

    for key in data["budgets"].keys():
        budgets = data["budgets"][key]

        if budgets["user_id"] == user_id:
            try:
                number = int(key.split("_")[1])
                numbers.append(number)

            except (ValueError, IndexError):
                print(f"Invalid key format: {key}. Skipping.")

    # User has no previous budgets
    if not numbers:
        user_number = int(user_id.split("_")[1])
        new_number = user_number * 1000 + 1
        return f"b_{new_number}"

    # User already has transactions
    highest_number = max(numbers)
    new_number = highest_number + 1

    return f"b_{new_number}"

def calculate_category_spending(data, user_id, category, month):
    pass

@app.get("/budgets")
def get_budgets(user_id: str = Header(...), month: Optional[str] = Query(None)):
    pass

@app.get("/budgets/status")
def get_budget_status(user_id: str = Header(...), month: Optional[str] = Query(None)):
    pass

@app.post("/budgets/create")
def create_budget(budget: BudgetCreate, user_id: str = Header(...)):
    pass

@app.put("/budgets/update/{budgets_id}")
def update_budget(budget_id: str, budget_update: dict, user_id: str = Header(...)):
    pass

@app.delete("/budgets/delete/{budgets_id}")
def delete_budget(budget_id: str, user_id: str = Header(...)):
    pass