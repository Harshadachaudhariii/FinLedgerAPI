from fastapi import FastAPI, HTTPException, Path, Query, Header, APIRouter
from datetime import date
import json
from typing import Optional
from fastapi.responses import JSONResponse
from app.utils.data import load_data, save_data
from app.model.budget import *
from app.enums.budget import BudgetStatusType, TransactionCategory

router = APIRouter()    

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
    data = load_data()
    total_spent =0.0
    for transaction_id, transaction_info in data["transactions"].items():
        if transaction_info["user_id"] != user_id:
            continue
        transactions_date = date.fromisoformat(transaction_info["dates"])
        if transaction_info["type"] == "expense":
            if transaction_info["category"] == category:
                transaction_month = transactions_date.strftime("%Y-%m")
                if transaction_month == month:
                    total_spent += transaction_info["amount"]
    return total_spent

@router.get("")
def get_budgets(user_id: str = Header(...), month: Optional[str] = Query(None)):
    data = load_data()
    budgets = []
    for budgets_id, budgets_info in data["budgets"].items():
        if budgets_info["user_id"] != user_id:
            continue

        if month is not None and budgets_info["month"] != month:
            continue
        budgets.append(budgets_info)
    return budgets
        
@router.get("/status")
def get_budget_status(user_id: str = Header(...), month: Optional[str] = Query(None)):
    data = load_data()
    if month is None:
        month = date.today().strftime("%Y-%m")

    budget_statuses = []
    for budgets_id, budgets_info in data["budgets"].items():
        if budgets_info["user_id"] != user_id:
            continue

        if budgets_info["month"] != month:
            continue
        budgeted_amount = budgets_info["amount"]
        spent_amount = calculate_category_spending(
            data,
            user_id,
            budgets_info["category"],
            month
        )
        remaining = budgeted_amount - spent_amount
        percentage_used = (spent_amount / budgeted_amount) * 100
        if percentage_used < 90:
            status = "on_track"
        elif percentage_used < 100:
            status = "warning"
        else:
            status = "exceeded"
        budget_statuses.append(
            BudgetStatus(
                budget_id=budgets_id,
                category=budgets_info["category"],
                month=month,
                budget_amount=budgeted_amount,
                spent_amount=spent_amount,
                remaining_amount=remaining,
                percentage_used=percentage_used,
                status=status
            )
        )
    
    return JSONResponse(status_code=200, content={
        "user_id": user_id,
        "month": month,
        "Budgets status": [status.model_dump(mode="json") for status in budget_statuses]
    })
            
@router.post("/create")
def create_budget(budget: BudgetCreate, user_id: str = Header(...)):
    data = load_data()
    for budget_id, budget_info in data["budgets"].items():
        if (
            budget_info["user_id"] == user_id
            and budget_info["category"] == budget.category
            and budget_info["month"] == budget.month
        ):
            raise HTTPException(status_code=409, detail="Budget already exists")
    budget_id = generate_budget_id(data,user_id)
    budget_data = budget.model_dump(mode="json", exclude_unset=True)
    budget_data["user_id"] = user_id
    data["budgets"][budget_id] = budget_data
    save_data(data)
    return JSONResponse(status_code=201, content={"message":"Budget created successfully.","user_id":user_id})

@router.put("/update/{budget_id}")
def update_budget(budget_id: str, budget_update: BudgetUpdate, user_id: str = Header(...)):
    data = load_data()
    if budget_id not in data["budgets"]:
        raise HTTPException(
                status_code=404,
                detail="budget_id ID not found"
            )
    if data["budgets"][budget_id]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You haven't ownership to this budgets")
    existing_budget_info = data["budgets"][budget_id]
    update_budgets_info = budget_update.model_dump(mode="json", exclude_unset=True)
    existing_budget_info.update(update_budgets_info)
    data["budgets"][budget_id] = existing_budget_info
    
    save_data(data)
    return JSONResponse(status_code=200, content={"message":"budgets updated successfully.", "user_id":user_id, "budgets":data["budgets"][budget_id]})

@router.delete("/delete/{budget_id}")
def delete_budget(budget_id: str, user_id: str = Header(...)):
    data = load_data()
        
    if budget_id not in data["budgets"]:
            raise HTTPException(
                status_code=404,
                detail="Budget ID not found"
            )
    if data["budgets"][budget_id]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You don't have ownership of this budgets")
    
    del data["budgets"][budget_id]
        
    save_data(data)
        
    return JSONResponse(status_code=200, content={"message":"Budgets deleted successfully.","budget_id":budget_id})
        