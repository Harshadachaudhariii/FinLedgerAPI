from fastapi import FastAPI, HTTPException, Path, Query , Header, APIRouter
from datetime import date
import json
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from app.routes.budget_system import router as budget_router
from app.routes.analytics import router as analytics_router
from app.utils.data import load_data, save_data
from app.utils.security import hash_password, verify_password
from app.enums.transaction import *
from app.model.user import *
from app.model.transactions import *

app = FastAPI()
app.include_router(budget_router, prefix="/budgets", tags=["Budgets"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
    
 

def generate_user_id(data) -> str:
    if not data:
        return "u_001"
    
    else:
        numbers =[]
        for key in data["users"].keys():
            try:
                number = int(key.split("_")[1])
                numbers.append(number)
            except ValueError:
                print(f"Invalid key format: {key}. Skipping.")
        if not numbers:
            return "u_001"
        highest_number = max(numbers)
        new_number= highest_number +1
        new_id = f"u_{new_number:03d}"
        return new_id

def generate_transaction_id(data, user_id: str) -> str:
    numbers = []

    for key in data["transactions"].keys():
        transaction = data["transactions"][key]

        if transaction["user_id"] == user_id:
            try:
                number = int(key.split("_")[1])
                numbers.append(number)

            except (ValueError, IndexError):
                print(f"Invalid key format: {key}. Skipping.")

    # User has no previous transactions
    if not numbers:
        user_number = int(user_id.split("_")[1])
        new_number = user_number * 1000 + 1
        return f"t_{new_number}"

    # User already has transactions
    highest_number = max(numbers)
    new_number = highest_number + 1

    return f"t_{new_number}"

@app.get("/")
def home():
    return {"message":"Check is fastapi work or not"}

@app.get("/about")
def about():
    return {"message":"A fully functional finacial tracker system API built with FastAPI."}

@app.get("/transactions")
def view_transactions(user_id: str = Header(...)):
    data = load_data()
    transactions = []

    for transaction in data["transactions"].values():
        if transaction["user_id"] == user_id:
            transactions.append(transaction)

    return transactions

@app.get("/transactions/filter")
def filter_transaction(type: Optional[Literal["income", "expense"]] = Query(None),
    category: Optional[TransactionCategory] = Query(None),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id: str = Header(...)):
    
    if start_date is not None and end_date is not None:
        if end_date <start_date:
            raise HTTPException(status_code=400, detail="end_date cannot be before start date")
        
    data = load_data()
    filter_criteria = {}
    if type is not None:
        filter_criteria["type"] = type

    if category is not None:
        filter_criteria["category"] = category
        
    
    filtered_data = {}
    for transaction_id , transaction_info in data["transactions"].items():
        # Check ownership first
        if transaction_info["user_id"] != user_id:
            continue
        match =True
        for key, value in filter_criteria.items():
            if transaction_info.get(key) != value:
                match = False
                break
        if not match:
            continue
        transaction_date= date.fromisoformat(transaction_info["dates"])
        if start_date is not None and transaction_date< start_date:
            match =False
            
        if end_date is not None and transaction_date > end_date:
            match =False
            
        if match:
            filtered_data[transaction_id] = transaction_info
    
    return filtered_data

@app.get("/transactions/summary/overview")
def summary_transactions(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Header(...)):
    data = load_data()
    
    total_income = 0.0
    total_expense = 0.0
    transaction_count = 0
    for transaction_id, transaction_info in data["transactions"].items():
        if transaction_info["user_id"] != user_id:
            continue
        
        transactions_date = date.fromisoformat(transaction_info["dates"])
        if start_date is not None and transactions_date < start_date:
            continue

        if end_date is not None and transactions_date > end_date:
            continue
        
        transaction_count += 1
        
        if transaction_info["type"] == "income":
            total_income += transaction_info["amount"]
        if transaction_info["type"] == "expense":
            total_expense += transaction_info["amount"]
        
    net_balance = round(total_income - total_expense, 2)
    total_income = round(total_income, 2)
    total_expense = round(total_expense, 2)
        
    return JSONResponse(status_code=200, content={
        "user_id": user_id,
        "period":{
            "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None
        },
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "transaction_count": transaction_count,
        "currency": "USD"
    })

@app.get("/transactions/summary/by-category")   
def summary_by_category_transaction(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Header(...)):
    
    data = load_data()
    
    category_totals = {}
    total_expense=0.0
    for transaction_id, transaction_info in data["transactions"].items():
        if transaction_info["user_id"] != user_id:
            continue
        transactions_date = date.fromisoformat(transaction_info["dates"])
        if start_date is not None and transactions_date < start_date:
            continue
        
        if end_date is not None and transactions_date > end_date:
            continue
        
        if transaction_info["type"] == "expense":
            category = transaction_info["category"]
            amount = transaction_info["amount"]
            
            total_expense += amount
            if category in category_totals:
                category_totals[category] += amount
            else:
                category_totals[category] = amount
     
    total_expense = round(total_expense, 2)

    breakdown=[]
    for category, amount in category_totals.items():
        percentage= (amount/total_expense) *100
        breakdown.append({
            "category":category,
            "amount":amount,
            "percentage":round(percentage,2)
        })

    return JSONResponse(status_code=200, content={
        "user_id":user_id,
        "period":{
            "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None
        },
        "total_expenses":total_expense,
        "breakdown":breakdown
    })
    
@app.get("/transactions/summary/monthly")
def summary_monthly_transaction(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Header(...)):
    data = load_data()
    
    monthly_data ={}

    for transaction_id, transaction_info in data["transactions"].items():
        if transaction_info["user_id"] != user_id:
            continue
        transactions_date = date.fromisoformat(transaction_info["dates"])
        if start_date is not None and transactions_date < start_date:
            continue
                
        if end_date is not None and transactions_date > end_date:
            continue
        
        month = transactions_date.strftime("%Y-%m")
        # Create month if it doesn't exist
        if month not in monthly_data:
            monthly_data[month] = {
                "income": 0.0,
                "expense": 0.0,
                "count": 0
            }
        
        if transaction_info["type"] == "income":
            monthly_data[month]["income"] += transaction_info["amount"]
        if transaction_info["type"] == "expense":
            monthly_data[month]["expense"] += transaction_info["amount"]
        
        monthly_data[month]["count"] += 1
        # Format monthly response
    monthly_summary = []

    for month, month_data in monthly_data.items():

        income = round(month_data["income"], 2)
        expense = round(month_data["expense"], 2)
        net_balance = round(income - expense, 2)

        monthly_summary.append({
            "month": month,
            "income": income,
            "expense": expense,
            "net_balance": net_balance,
            "transactions_count": month_data["count"]
        })
    monthly_summary.sort(key=lambda x: x["month"])

    
    return JSONResponse(status_code=200, content={
        "user_id": user_id,
        "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
        "monthly_summary":monthly_summary
    })

@app.get("/transactions/{transaction_id}")
def view_transaction(transaction_id: str,user_id: str = Header(...)):
    data =load_data()
    if transaction_id not in data["transactions"]:
        raise HTTPException(
            status_code=404,
            detail="Transaction ID not found."
        ) 
    transaction = data["transactions"][transaction_id]

    if transaction["user_id"] != user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this transaction."
        )

    return transaction

@app.post("/users/register")
def create_new_user(users: User):
    data = load_data()
    new_user_id = generate_user_id(data)
   # 1. Convert the user data to a dictionary
    user_data = users.model_dump(mode="json", exclude_unset=True)
    
    # 2. Hash the password before saving
    user_data["password"] = hash_password(user_data["password"])
    
    # 3. Save the hashed data
    data["users"][new_user_id] = user_data
    save_data(data)
    return JSONResponse(status_code=201,content={"message": "User registered successfully.", "id": new_user_id})

@app.post("/users/login")
def verify_user(users:User):
    data = load_data()
    
    for user_id, value in data["users"].items():
         if value["username"] == users.username:
            if verify_password(users.password, value["password"]):
                 return JSONResponse(
                            status_code=200,
                            content={
                                    "message": "User login successfully.",
                                    "user_id": user_id
                                }
                            )
    raise HTTPException(status_code=401, detail="Invalid username and password")
    
@app.post("/transactions/create")
def create_transactions(transactions:Transaction, user_id:str=Header(...)):
    data = load_data()
    if user_id not in data["users"]:
        raise HTTPException(status_code=404, detail="User ID not found.")
    transactions_id = generate_transaction_id(data, user_id)
    transaction_data = transactions.model_dump(mode="json", exclude_unset=True)
    transaction_data["user_id"] = user_id
    data["transactions"][transactions_id]= transaction_data
    save_data(data)
    
    return JSONResponse(status_code=201,content={"message":"Transaction created successfully.", "transactions_id":transactions_id})    

@app.put("/transactions/update/{transaction_id}")
def update_transaction(transaction_id: str,transaction:TransactionUpdate,user_id: str=Header(...)):
    data = load_data()
    if transaction_id not in data["transactions"]:
        raise HTTPException(
            status_code=404,
            detail="Transaction ID not found"
        )
    if data["transactions"][transaction_id]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You haven't ownership to this transactions")
    
    existing_transaction_info = data["transactions"][transaction_id]
    update_transaction_info = transaction.model_dump(mode="json", exclude_unset=True)
    existing_transaction_info.update(update_transaction_info)
    data["transactions"][transaction_id] = existing_transaction_info
    
    save_data(data)
    return JSONResponse(status_code=200, content={"message":"Transaction updated successfully.", "user_id":user_id, "transaction":data["transactions"][transaction_id]})
    
@app.delete("/transactions/delete/{transaction_id}")
def delete_transaction(transaction_id:str, user_id:str=Header(...)):
    data = load_data()
    
    if transaction_id not in data["transactions"]:
            raise HTTPException(
                status_code=404,
                detail="Transaction ID not found"
            )
    if data["transactions"][transaction_id]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You don't have ownership of this transaction")
    
    del data["transactions"][transaction_id]
    
    save_data(data)
    
    return JSONResponse(status_code=200, content={"message":"Transaction deleted successfully.","transaction_id":transaction_id})
    

    