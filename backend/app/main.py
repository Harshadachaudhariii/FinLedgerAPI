import logging
from fastapi import FastAPI, HTTPException, Path, Query, APIRouter, Depends
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user
from datetime import date
import json
from pydantic import BaseModel
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from app.routes.budget_system import router as budget_router
from app.routes.analytics import router as analytics_router
from app.utils.data import load_data, save_data
from app.enums.transaction import *
from app.model.user import *
from app.model.transactions import *
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.logger import *

app = FastAPI()

@app.on_event("startup")
def startup_event():
    logger.info("Server started successfully. FinLedger API is now running.")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Server shutdown requested. FinLedger API is stopping.")

@app.middleware("http")
async def log_request_middleware(request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        logger.info("Request completed: %s %s - status=%s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        logger.exception("Unhandled exception while processing: %s %s", request.method, request.url.path)
        raise

app.include_router(budget_router, prefix="/budgets", tags=["Budgets"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
    

def generate_user_id(data) -> str:
    logger.info("Generating new user ID")
    try:
        if not data:
            logger.info("No existing users found; creating first user ID")
            return "u_001"

        numbers = []
        for key in data["users"].keys():
            try:
                number = int(key.split("_")[1])
                numbers.append(number)
            except ValueError:
                logger.warning("Invalid user key format encountered while generating ID: %s", key)

        if not numbers:
            logger.info("No valid user IDs found; creating first user ID")
            return "u_001"

        highest_number = max(numbers)
        new_number = highest_number + 1
        new_id = f"u_{new_number:03d}"
        logger.info("Generated user ID: %s", new_id)
        return new_id
    except Exception:
        logger.exception("Failed to generate user ID")
        raise


def generate_transaction_id(data, user_id: str) -> str:
    logger.info("Generating transaction ID for user: %s", user_id)
    try:
        numbers = []

        for key in data["transactions"].keys():
            transaction = data["transactions"][key]

            if transaction["user_id"] == user_id:
                try:
                    number = int(key.split("_")[1])
                    numbers.append(number)

                except (ValueError, IndexError):
                    logger.warning("Invalid transaction key format encountered: %s", key)

        # User has no previous transactions
        if not numbers:
            user_number = int(user_id.split("_")[1])
            new_number = user_number * 1000 + 1
            transaction_id = f"t_{new_number}"
            logger.info("Generated first transaction ID for user %s: %s", user_id, transaction_id)
            return transaction_id

        # User already has transactions
        highest_number = max(numbers)
        new_number = highest_number + 1
        transaction_id = f"t_{new_number}"
        logger.info("Generated transaction ID for user %s: %s", user_id, transaction_id)
        return transaction_id
    except Exception:
        logger.exception("Failed to generate transaction ID for user %s", user_id)
        raise

@app.get("/")
def home():
    logger.info("Home endpoint called")
    return {"message":"Check is fastapi work or not"}

@app.get("/about")
def about():
    logger.info("About endpoint called")
    return {"message":"A fully functional finacial tracker system API built with FastAPI."}

@app.get("/transactions")
def view_transactions(user_id: str = Depends(get_current_user)):
    logger.info("Fetching transactions for user %s", user_id)
    try:
        data = load_data()
        transactions = []

        for transaction in data["transactions"].values():
            if transaction["user_id"] == user_id:
                transactions.append(transaction)

        logger.info("Returned %s transactions for user %s", len(transactions), user_id)
        return transactions
    except Exception:
        logger.exception("Failed to fetch transactions for user %s", user_id)
        raise

@app.get("/transactions/filter")
def filter_transaction(type: Optional[Literal["income", "expense"]] = Query(None),
    category: Optional[TransactionCategory] = Query(None),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id: str = Depends(get_current_user)):
    logger.info("Filtering transactions for user %s with type=%s category=%s", user_id, type, category)
    try:
        if start_date is not None and end_date is not None:
            if end_date <start_date:
                logger.warning("Invalid date range for user %s: start_date=%s end_date=%s", user_id, start_date, end_date)
                raise HTTPException(status_code=400, detail="end_date cannot be before start date")

        data = load_data()
        filter_criteria = {}
        if type is not None:
            filter_criteria["type"] = type

        if category is not None:
            filter_criteria["category"] = category

        filtered_data = {}
        for transaction_id , transaction_info in data["transactions"].items():
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

        logger.info("Filtered transactions returned %s results for user %s", len(filtered_data), user_id)
        return filtered_data
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to filter transactions for user %s", user_id)
        raise

@app.get("/transactions/summary/overview")
def summary_transactions(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Depends(get_current_user)):
    logger.info("Generating transaction overview for user %s", user_id)
    try:
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

        logger.info("Overview created for user %s: income=%s expense=%s net=%s count=%s", user_id, total_income, total_expense, net_balance, transaction_count)
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
            "currency": "Indian Rupees (INR)"
        })
    except Exception:
        logger.exception("Failed to generate transaction overview for user %s", user_id)
        raise

@app.get("/transactions/summary/by-category")   
def summary_by_category_transaction(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Depends(get_current_user)):
    logger.info("Generating category summary for user %s", user_id)
    try:
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

        logger.info("Category summary generated for user %s with %s categories", user_id, len(breakdown))
        return JSONResponse(status_code=200, content={
            "user_id":user_id,
            "period":{
                "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
            },
            "total_expenses":total_expense,
            "breakdown":breakdown
        })
    except Exception:
        logger.exception("Failed to generate category summary for user %s", user_id)
        raise

@app.get("/transactions/summary/monthly")
def summary_monthly_transaction(start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    user_id:str=Depends(get_current_user)):
    logger.info("Generating monthly summary for user %s", user_id)
    try:
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

        logger.info("Monthly summary generated for user %s with %s periods", user_id, len(monthly_summary))
        return JSONResponse(status_code=200, content={
            "user_id": user_id,
            "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
            "monthly_summary":monthly_summary
        })
    except Exception:
        logger.exception("Failed to generate monthly summary for user %s", user_id)
        raise

@app.get("/transactions/{transaction_id}")
def view_transaction(transaction_id: str,user_id: str = Depends(get_current_user)):
    logger.info("Fetching transaction %s for user %s", transaction_id, user_id)
    try:
        data =load_data()
        if transaction_id not in data["transactions"]:
            logger.warning("Transaction lookup failed: transaction %s not found for user %s", transaction_id, user_id)
            raise HTTPException(
                status_code=404,
                detail="Transaction ID not found."
            )
        transaction = data["transactions"][transaction_id]

        if transaction["user_id"] != user_id:
            logger.warning("Permission denied for user %s on transaction %s", user_id, transaction_id)
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this transaction."
            )

        logger.info("Transaction %s returned successfully for user %s", transaction_id, user_id)
        return transaction
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch transaction %s for user %s", transaction_id, user_id)
        raise

@app.post("/users/register")
def create_new_user(users: User):
    logger.info("User registration initiated")
    try:
        data = load_data()
        new_user_id = generate_user_id(data)
        user_data = users.model_dump(mode="json", exclude_unset=True)
        user_data["password"] = hash_password(user_data["password"])
        data["users"][new_user_id] = user_data
        save_data(data)
        logger.info("User registered successfully with ID %s", new_user_id)
        return JSONResponse(status_code=201,content={"message": "User registered successfully.", "id": new_user_id})
    except Exception:
        logger.exception("Failed to register new user")
        raise

# Create a dedicated schema for login requests in your Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/users/login")
def verify_user(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info("Login attempt for username: %s", form_data.username)
    try:
        data = load_data()

        for user_id, value in data["users"].items():
            if value["username"] == form_data.username:
                if verify_password(form_data.password, value["password"]):
                    access_token = create_access_token({"sub": user_id})
                    logger.info("User %s logged in successfully", user_id)
                    return {
                        "message":"User Login Successfully.",
                        "access_token": access_token,
                        "token_type": "bearer"
                    }

        logger.warning("Failed login attempt for username: %s", form_data.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during login for username %s", form_data.username)
        raise

@app.post("/transactions/create")
def create_transactions(transactions:Transaction, user_id:str=Depends(get_current_user)):
    logger.info("Creating new transaction for user %s", user_id)
    try:
        data = load_data()
        if user_id not in data["users"]:
            logger.warning("Transaction creation failed: user %s not found", user_id)
            raise HTTPException(status_code=404, detail="User ID not found.")
        transactions_id = generate_transaction_id(data, user_id)
        transaction_data = transactions.model_dump(mode="json", exclude_unset=True)
        transaction_data["user_id"] = user_id
        data["transactions"][transactions_id]= transaction_data
        save_data(data)
        logger.info("Transaction %s created successfully for user %s", transactions_id, user_id)
        return JSONResponse(status_code=201,content={"message":"Transaction created successfully.", "transactions_id":transactions_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create transaction for user %s", user_id)
        raise

@app.put("/transactions/update/{transaction_id}")
def update_transaction(transaction_id: str,transaction:TransactionUpdate,user_id: str=Depends(get_current_user)):
    logger.info("Updating transaction %s for user %s", transaction_id, user_id)
    try:
        data = load_data()
        if transaction_id not in data["transactions"]:
            logger.warning("Transaction update failed: transaction %s not found for user %s", transaction_id, user_id)
            raise HTTPException(
                status_code=404,
                detail="Transaction ID not found"
            )
        if data["transactions"][transaction_id]["user_id"] != user_id:
            logger.warning("Permission denied for user %s updating transaction %s", user_id, transaction_id)
            raise HTTPException(status_code=403, detail="You haven't ownership to this transactions")

        existing_transaction_info = data["transactions"][transaction_id]
        update_transaction_info = transaction.model_dump(mode="json", exclude_unset=True)
        existing_transaction_info.update(update_transaction_info)
        data["transactions"][transaction_id] = existing_transaction_info

        save_data(data)
        logger.info("Transaction %s updated successfully for user %s", transaction_id, user_id)
        return JSONResponse(status_code=200, content={"message":"Transaction updated successfully.", "user_id":user_id, "transaction":data["transactions"][transaction_id]})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update transaction %s for user %s", transaction_id, user_id)
        raise

@app.delete("/transactions/delete/{transaction_id}")
def delete_transaction(transaction_id:str, user_id:str=Depends(get_current_user)):
    logger.info("Deleting transaction %s for user %s", transaction_id, user_id)
    try:
        data = load_data()

        if transaction_id not in data["transactions"]:
                logger.warning("Transaction delete failed: transaction %s not found for user %s", transaction_id, user_id)
                raise HTTPException(
                    status_code=404,
                    detail="Transaction ID not found"
                )
        if data["transactions"][transaction_id]["user_id"] != user_id:
            logger.warning("Permission denied for user %s deleting transaction %s", user_id, transaction_id)
            raise HTTPException(status_code=403, detail="You don't have ownership of this transaction")

        del data["transactions"][transaction_id]

        save_data(data)
        logger.info("Transaction %s deleted successfully for user %s", transaction_id, user_id)

        return JSONResponse(status_code=200, content={"message":"Transaction deleted successfully.","transaction_id":transaction_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete transaction %s for user %s", transaction_id, user_id)
        raise
    

    