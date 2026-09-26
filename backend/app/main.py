from fastapi import FastAPI, HTTPException, Path, Query, APIRouter, Depends
from fastapi.responses import JSONResponse,StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional,Literal
from datetime import date, datetime,timedelta
from app.routes.budget_system import router as budget_router
from app.routes.analytics import router as analytics_router
from app.utils.data import load_data, save_data
from app.utils.logger import *
from app.utils.security import (
    hash_password, verify_password, create_access_token, 
    get_current_user, add_token_to_blocklist, check_rate_limit, 
    record_failed_login, oauth2_scheme
    )
from app.enums.transaction import *
from app.model.user import *
from app.model.transactions import *
from fastapi import UploadFile, File
import csv
import io
from fpdf import FPDF
from app.enums.transaction import TransactionCategory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    logger.info("Server started successfully. FinLedger API is now running.")
    
    yield  # This is where the app runs
    
    # --- SHUTDOWN LOGIC ---
    logger.info("Server shutdown requested. FinLedger API is stopping.")

app = FastAPI(title="FinLedger", version="2.0.0")

# Allow all origins for development. In production, specify your frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["http://localhost:3000"] in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Allows all headers
)
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

# -------------Router ----------------------
app.include_router(budget_router, prefix="/budgets", tags=["Budgets"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

# ---------------------Helper -----------------------------
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

# ---------------------System Endpoints-----------------------
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
def home():
    logger.info("Home endpoint called")
    return {"message":"Check is fastapi work or not"}

@app.get("/about")
def about():
    logger.info("About endpoint called")
    return {"message":"A fully functional finacial tracker system API built with FastAPI."}

# ---------------------- User Endpoints --------------------
@app.post("/users/register", tags=["Users"])
def create_new_user(users: User):
    logger.info("User registration attempt for username: %s", users.username)
    try:
        data = load_data()
        # Username uniqueness check
        for existing_user in data.get("users", {}).values():
            if existing_user["username"] == users.username:
                logger.warning("Registration failed: username already exists: %s",users.username)
                raise HTTPException(status_code=409,detail="Username already exists.")
        logger.info("Username %s is available for registration",users.username)
        new_user_id = generate_user_id(data)
        logger.info("Generated new user ID: %s", new_user_id)
        user_data = users.model_dump(mode="json",exclude_unset=True)

        user_data["password"] = hash_password(user_data["password"])
        logger.info("Password hashed successfully for user: %s", new_user_id)

        user_data["created_at"] = date.today().isoformat()

        data["users"][new_user_id] = user_data

        save_data(data)
        logger.info("User registered successfully: %s",new_user_id)
        return JSONResponse(
            status_code=201,
            content={
                "message": "User registered successfully.",
                "id": new_user_id
            }
        )
    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error during registration for username: %s",users.username)
        raise
    
@app.post("/users/login", tags=["Users"])
def verify_user(form_data: OAuth2PasswordRequestForm = Depends()):
    if not check_rate_limit(form_data.username):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
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
        record_failed_login(form_data.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during login for username %s", form_data.username)
        raise
    
@app.get("/users/me", tags=["Users"])
def get_me(user_id: str = Depends(get_current_user)):
    logger.info("Fetching profile for user %s", user_id)
    try:
        data = load_data()
        user = data.get("users", {}).get(user_id)
        if not user:
            logger.warning("Profile not found for user %s", user_id)
            raise HTTPException(status_code=404, detail="User not found")
        user = {k: v for k, v in user.items() if k != "password"}
        return {"user_id": user_id, **user}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch profile for user %s", user_id)
        raise

@app.post("/users/logout", tags=["Users"])
def logout_user(token: str = Depends(oauth2_scheme)):
    logger.info("Logout attempt started")
    try:
        add_token_to_blocklist(token)
        logger.info("User logged out successfully and token was revoked")
        return {"message": "Successfully logged out"}
    except Exception:
        logger.exception("Logout failed while revoking token")
        raise
    
@app.put("/users/change-password", tags=["Users"])
def change_password(old_password: str,new_password: str,current_user_id: str = Depends(get_current_user)):
    logger.info("Password change attempt for user: %s",current_user_id)
    try:
        data = load_data()
        user = data["users"].get(current_user_id)
        if not user:
            logger.warning("Password change failed: user not found: %s",current_user_id)
            raise HTTPException(status_code=404,detail="User not found")
        logger.info("User found, verifying old password: %s",current_user_id)

        if not verify_password(old_password, user["password"]):
            logger.warning(
                "Password change failed: incorrect old password for user: %s",
                current_user_id
            )
            raise HTTPException(status_code=401,detail="Old password is incorrect")

        user["password"] = hash_password(new_password)
        logger.info("New password hashed successfully for user: %s",current_user_id)

        save_data(data)
        logger.info("Password changed successfully for user: %s",current_user_id)
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while changing password for user: %s",current_user_id)
        raise
    
# ---------------------- Transaction Endpoints -------------------
@app.get("/transactions", tags=["Transactions"])
def view_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user_id: str = Depends(get_current_user)
    ):
    logger.info("Viewing transactions for user: %s | skip=%s | limit=%s",current_user_id,skip,limit)

    try:
        data = load_data()
        transactions = [{"id": tid, **t} for tid, t in data.get("transactions", {}).items()
            if t.get("user_id") == current_user_id and not t.get("deleted_at")
        ]

        logger.info("Found %s transactions for user: %s", len(transactions), current_user_id)
        paginated_transactions = transactions[skip : skip + limit]

        logger.info("Returning %s transactions for user: %s",len(paginated_transactions),current_user_id)
        return {
            "total_count": len(transactions),
            "skip": skip,
            "limit": limit,
            "data": paginated_transactions
        }

    except Exception:
        logger.exception("Failed to retrieve transactions for user: %s",current_user_id)
        raise

@app.get("/transactions/filter", tags=["Transactions"])
def filter_transaction(
    type: Optional[Literal["income", "expense"]] = Query(None),
    category: Optional[TransactionCategory] = Query(None),
    start_date: Optional[date] = Query(None,description="Start date for filtering"),
    end_date: Optional[date] = Query(None,description="End date for filtering"),
    search: Optional[str] = Query(None,description="Search text for description, merchant, category, type, payment method, or status"
    ),user_id: str = Depends(get_current_user)
    ):
    logger.info(
        "Filtering transactions for user %s with type=%s category=%s search=%s",user_id,
        type,category,search
    )
    try:
        if start_date is not None and end_date is not None:
            if end_date < start_date:
                logger.warning("Invalid date range for user %s: start_date=%s end_date=%s",
                    user_id,start_date,end_date)
                raise HTTPException(status_code=400,detail="end_date cannot be before start date")

        data = load_data()
        filter_criteria = {}
        if type is not None:
            filter_criteria["type"] = type
        if category is not None:
            filter_criteria["category"] = category

        filtered_data = {}
        for transaction_id, transaction_info in data["transactions"].items():
            if transaction_info["user_id"] != user_id:
                continue
            if transaction_info.get("deleted_at"):
                continue
            match = True
            # Existing type/category filters
            for key, value in filter_criteria.items():
                if transaction_info.get(key) != value:
                    match = False
                    break
            if not match:
                continue
            # Date filtering
            transaction_date = date.fromisoformat(transaction_info["dates"])
            if start_date is not None and transaction_date < start_date:
                match = False
            if end_date is not None and transaction_date > end_date:
                match = False
            if not match:
                continue
            # Text search
            if search is not None:
                search_text = search.lower()
                description = str(transaction_info.get("description", "")).lower()
                merchant = str(transaction_info.get("merchant", "")).lower()
                transaction_category = str(transaction_info.get("category", "")).lower()
                transaction_type = str(transaction_info.get("type", "")).lower()
                payment_method = str(transaction_info.get("payment_method", "")).lower()
                status = str(transaction_info.get("status", "")).lower()
                currency = str(transaction_info.get("currency", "")).lower()
                notes = str(transaction_info.get("notes", "")).lower()
            if not (
                search_text in description
                or search_text in merchant
                or search_text in transaction_category
                or search_text in transaction_type
                or search_text in payment_method
                or search_text in status
                or search_text in currency
                or search_text in notes
            ):
                    match = False
                    continue

            if match:
                filtered_data[transaction_id] = {
                    "id": transaction_id,
                    **transaction_info
                }

        logger.info("Filtered transactions returned %s results for user %s",len(filtered_data),user_id)
        return list(filtered_data.values())

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to filter transactions for user %s",user_id)
        raise

@app.get("/transactions/summary/overview", tags=["Transactions"])
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
            if transaction_info.get("deleted_at"):
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
            "currency": data.get("users", {}).get(user_id, {}).get("currency", "INR")
        })
    except Exception:
        logger.exception("Failed to generate transaction overview for user %s", user_id)
        raise

@app.get("/transactions/summary/by-category", tags=["Transactions"])   
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
            if transaction_info.get("deleted_at"):
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
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0.0
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

@app.get("/transactions/summary/monthly", tags=["Transactions"])
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
            if transaction_info.get("deleted_at"):
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

@app.get("/dashboard", tags=["Transactions"])
def dashboard(current_user_id: str = Depends(get_current_user)):
    logger.info("Generating dashboard for user %s",current_user_id)

    try:
        data = load_data()
        current_month = date.today().strftime("%Y-%m")
        # --------------------------------
        # 1. Current Month Net Balance
        # --------------------------------

        current_month_net_balance = 0.0
        for transaction_id, transaction_info in data["transactions"].items():
            # Check user
            if transaction_info["user_id"] != current_user_id:
                continue

            # Ignore deleted transactions
            if transaction_info.get("deleted_at"):
                continue
            # Check current month
            if transaction_info["dates"][:7] != current_month:
                continue
            amount = transaction_info["amount"]
            if transaction_info["type"] == "income":
                current_month_net_balance += amount

            elif transaction_info["type"] == "expense":
                current_month_net_balance -= amount
        logger.info("Current month net balance for user %s: %s",current_user_id,current_month_net_balance)
        # --------------------------------
        # 2. Recent Transactions
        # --------------------------------

        user_transactions = []
        for transaction_id, transaction_info in data["transactions"].items():
            # Check user
            if transaction_info["user_id"] != current_user_id:
                continue
            # Ignore deleted transactions
            if transaction_info.get("deleted_at"):
                continue
            user_transactions.append({"id": transaction_id,**transaction_info})

        # Sort newest first
        user_transactions.sort(
            key=lambda transaction: transaction["dates"],
            reverse=True
        )
        # Get only latest 5
        recent_transactions = user_transactions[:5]
        logger.info("Found %s recent transactions for user %s",len(recent_transactions),current_user_id)

        # --------------------------------
        # 3. Budget Alerts
        # --------------------------------

        budget_alerts = []
        for budget_id, budget_info in data["budgets"].items():
            # Check user
            if budget_info["user_id"] != current_user_id:
                continue

            # Check current month
            if budget_info["month"] != current_month:
                continue

            # Calculate spending for this budget category
            spent_amount = 0.0
            for transaction_info in data["transactions"].values():

                if transaction_info["user_id"] != current_user_id:
                    continue
                if transaction_info.get("deleted_at"):
                    continue
                if transaction_info["type"] != "expense":
                    continue
                if transaction_info["category"] != budget_info["category"]:
                    continue
                if not transaction_info["dates"].startswith(current_month):
                    continue
                spent_amount += transaction_info["amount"]

            # Calculate budget status
                    # Calculate budget status (FIX 4: Changed 0.8 to 0.9 to match /budgets/status)
        budget_amount = budget_info["amount"]
        percentage_used = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0.0
        
        if percentage_used >= 100:
            status = "exceeded"
        elif percentage_used >= 90:
            status = "warning"
        else:
            status = "on_track"
            
        # Only return warning/exceeded
        if status in ["warning", "exceeded"]:
            budget_alerts.append({
                "id": budget_id,
                **budget_info,
                "spent_amount": spent_amount,
                "percentage_used": round(percentage_used, 2), # FIX 5: Added percentage
                "status": status
            })

        logger.info("Found %s budget alerts for user %s",len(budget_alerts),current_user_id)

        # --------------------------------
        # 4. Final Dashboard Response
        # --------------------------------

        logger.info("Dashboard generated successfully for user %s",current_user_id)
        return {
            "current_month_net_balance": current_month_net_balance,
            "recent_transactions": recent_transactions,
            "budget_alerts": budget_alerts
        }
    except Exception:
        logger.exception("Failed to generate dashboard for user %s",current_user_id)
        raise

@app.post("/transactions/create", tags=["Transactions"])
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
        # Override currency with the user's preferred currency
        transaction_data["currency"] = data["users"][user_id].get("currency", "INR")
        data["transactions"][transactions_id]= transaction_data
        save_data(data)
        logger.info("Transaction %s created successfully for user %s", transactions_id, user_id)
        return JSONResponse(status_code=201,content={"message":"Transaction created successfully.", "transactions_id":transactions_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create transaction for user %s", user_id)
        raise

@app.put("/transactions/update/{transaction_id}", tags=["Transactions"])
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
            
        # NEW: Check if soft-deleted
        if data["transactions"][transaction_id].get("deleted_at"):
            logger.warning("User %s tried to update deleted transaction %s", user_id, transaction_id)
            raise HTTPException(status_code=404, detail="Transaction not found")

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

@app.delete("/transactions/delete/{transaction_id}", tags=["Transactions"])
def delete_transaction(transaction_id: str,user_id: str = Depends(get_current_user)):
    logger.info("Deleting transaction %s for user %s",transaction_id,user_id)
    try:
        data = load_data()
        # Check transaction exists
        if transaction_id not in data.get("transactions", {}):
            logger.warning("Transaction delete failed: transaction %s not found for user %s",transaction_id,user_id)
            raise HTTPException(status_code=404,detail="Transaction ID not found")

        transaction = data["transactions"][transaction_id]

        # Check ownership
        if transaction.get("user_id") != user_id:
            logger.warning("Permission denied for user %s deleting transaction %s",user_id,transaction_id)
            raise HTTPException(status_code=403,detail="You don't have ownership of this transaction")

        # Check if already deleted
        if transaction.get("deleted_at"):
            logger.warning("Transaction %s is already deleted for user %s",transaction_id,user_id)
            raise HTTPException(status_code=404,detail="Transaction not found")

        # Soft delete
        transaction["deleted_at"] = datetime.now().isoformat()
        save_data(data)
        logger.info("Transaction %s deleted successfully for user %s",transaction_id,user_id)

        return JSONResponse(status_code=200,content={
                "message": "Transaction deleted successfully.",
                "transaction_id": transaction_id
            }
        )
    except HTTPException:
        raise

    except Exception:
        logger.exception("Failed to delete transaction %s for user %s",transaction_id,user_id)
        raise

@app.post("/transactions/import-csv", tags=["Transactions"])
def import_transactions_csv(
    file: UploadFile = File(...), 
    current_user_id: str = Depends(get_current_user)
    ):
    logger.info("CSV import started for user: %s", current_user_id)
    try:
        data = load_data()
        imported_count = 0
        
        # Read the uploaded file
        contents = file.file.read()
        csv_data = io.StringIO(contents.decode("utf-8"))
        reader = csv.DictReader(csv_data)
        
        # Expected CSV headers: type,category,amount,currency,dates,description
        for row in reader:
            try:
                trans_id = generate_transaction_id(data, current_user_id)
                transaction_data = {
                    "user_id": current_user_id,
                    "type": row["type"],
                    "category": row["category"],
                    "amount": float(row["amount"]),
                    "currency": row.get("currency", "INR"),
                    "dates": row["dates"],
                    "description": row.get("description", ""),
                    "payment_method": row.get("payment_method", "Cash"),
                    "status": "completed",
                    "notes": "Imported via CSV"
                }
                data["transactions"][trans_id] = transaction_data
                imported_count += 1
            except Exception as e:
                # Skip invalid rows but continue processing
                continue
                
        save_data(data)
        logger.info("Successfully imported %s transactions for user: %s", imported_count, current_user_id)
        return {"message": f"Successfully imported {imported_count} transactions."}
    except Exception:
        logger.exception("Failed to import CSV for user: %s", current_user_id)
        raise HTTPException(status_code=500, detail="Failed to process CSV file")

@app.get("/transactions/export-csv", tags=["Transactions"])
def export_transactions_csv(start_date: Optional[date] = Query(None,description="Start date for filtering"),
    end_date: Optional[date] = Query(None,description="End date for filtering"),
    current_user_id: str = Depends(get_current_user)):
    logger.info(f"Starting CSV export for user: {current_user_id}")
    try:
        # Load JSON data
        data = load_data()
        logger.info(f"Export date range: {start_date} to {end_date}")
        # Create in-memory buffer
        buffer = io.StringIO()
        # Create CSV writer
        writer = csv.writer(buffer)
        # Header row
        writer.writerow([
            "id",
            "type",
            "category",
            "amount",
            "currency",
            "dates",
            "description",
            "merchant",
            "payment_method",
            "status",
            "notes"
        ])

        exported_count = 0
        # Loop through transactions
        for transaction_id, transaction in data["transactions"].items():

            # Check user
            if transaction["user_id"] != current_user_id:
                continue
            # Ignore deleted transactions
            if transaction.get("deleted_at") is not None:
                continue
            # Convert transaction date
            transaction_date = date.fromisoformat(
                transaction["dates"]
            )

            # Start date filter
            if start_date and transaction_date < start_date:
                continue
            # End date filter
            if end_date and transaction_date > end_date:
                continue

            # Write transaction row
            writer.writerow([
                transaction_id,
                transaction.get("type", ""),
                transaction.get("category", ""),
                transaction.get("amount", ""),
                transaction.get("currency", ""),
                transaction.get("dates", ""),
                transaction.get("description", ""),
                transaction.get("merchant", ""),
                transaction.get("payment_method", ""),
                transaction.get("status", ""),
                transaction.get("notes", "")
            ])

            exported_count += 1
        logger.info(f"CSV export completed for user: {current_user_id}. "f"Transactions exported: {exported_count}")
        # Return CSV file
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    'attachment; filename="transactions.csv"'
            }
        )

    except Exception as e:
        logger.error(f"Error exporting CSV for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export CSV file.")

@app.get("/transactions/export-pdf", tags=["Transactions"])
def export_transactions_pdf(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user_id: str = Depends(get_current_user)
):
    logger.info("PDF export started for user: %s", current_user_id)
    try:
        data = load_data()
        
        # 1. Filter transactions
        transactions = []
        for tid, t in data.get("transactions", {}).items():
            if t.get("user_id") != current_user_id or t.get("deleted_at"):
                continue
            
            trans_date = date.fromisoformat(t["dates"])
            if start_date and trans_date < start_date:
                continue
            if end_date and trans_date > end_date:
                continue
                
            transactions.append({"id": tid, **t})
            
        # Sort by date (newest first)
        transactions.sort(key=lambda x: x["dates"], reverse=True)

        # 2. Custom PDF class with footer
        class FinLedgerPDF(FPDF):
            def footer(self):
                self.set_y(-15)
                self.set_font("Arial", "I", 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

        pdf = FinLedgerPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # 3. Colorful Header
        pdf.set_fill_color(25, 55, 95)
        pdf.rect(10, 10, 190, 35, "F")
        
        pdf.set_y(15)
        pdf.set_font("Arial", style="B", size=20)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "Financial Transaction Statement", ln=True, align="C")
        
        pdf.set_font("Arial", size=11)
        pdf.set_text_color(220, 230, 245)
        user_info = data.get("users", {}).get(current_user_id, {})
        pdf.cell(0, 6, f"User: {user_info.get('username', current_user_id)}", ln=True, align="C")
        
        period_text = "All Time"
        if start_date and end_date:
            period_text = f"{start_date.isoformat()} to {end_date.isoformat()}"
        elif start_date:
            period_text = f"From {start_date.isoformat()}"
        elif end_date:
            period_text = f"Until {end_date.isoformat()}"
        pdf.cell(0, 6, f"Period: {period_text}", ln=True, align="C")
        
        pdf.ln(15)

        # 4. Table Header
        pdf.set_font("Arial", style="B", size=9)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(41, 98, 155)
        col_widths = [25, 20, 28, 25, 92]
        
        headers = ["Date", "Type", "Category", "Amount", "Description"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 9, header, border=1, fill=True, align="C")
        pdf.ln()

        # 5. Transaction Rows - FIXED VERSION (no gaps)
        pdf.set_font("Arial", size=8)
        total_income = 0.0
        total_expense = 0.0
        row_index = 0

        for t in transactions:
            amount = float(t["amount"])
            if t["type"] == "income":
                total_income += amount
                row_bg = (220, 245, 220)
                type_color = (0, 100, 0)
            else:
                total_expense += amount
                row_bg = (255, 230, 230)
                type_color = (150, 0, 0)

            # Alternating background
            if row_index % 2 == 0:
                bg_color = row_bg
            else:
                bg_color = tuple(max(0, c - 15) for c in row_bg)

            # FIX: Calculate row height BEFORE drawing
            desc = t.get("description", "")
            # ~50 chars fit in the description column width
            lines_needed = max(1, (len(desc) + 49) // 50)
            row_height = max(7, lines_needed * 5)

            # Check if we need a new page
            if pdf.get_y() + row_height > 270:
                pdf.add_page()
                pdf.set_font("Arial", style="B", size=9)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(41, 98, 155)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 9, header, border=1, fill=True, align="C")
                pdf.ln()

            # FIX: Draw ALL cells with cell() using the SAME height
            x_start = pdf.get_x()
            y_start = pdf.get_y()

            # Background rectangle
            pdf.set_fill_color(*bg_color)
            pdf.rect(x_start, y_start, sum(col_widths), row_height, "F")

            # Date
            pdf.set_xy(x_start, y_start)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_widths[0], row_height, t["dates"], border=1, align="C")

            # Type
            pdf.set_text_color(*type_color)
            pdf.set_font("Arial", style="B", size=8)
            pdf.cell(col_widths[1], row_height, t["type"].capitalize(), border=1, align="C")
            pdf.set_font("Arial", size=8)

            # Category
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_widths[2], row_height, t["category"], border=1, align="C")

            # Amount
            pdf.set_text_color(*type_color)
            pdf.set_font("Arial", style="B", size=8)
            pdf.cell(col_widths[3], row_height, f"{amount:.2f}", border=1, align="R")
            pdf.set_font("Arial", size=8)

            # FIX: Description - use cell() with truncation instead of multi_cell
            pdf.set_text_color(40, 40, 40)
            pdf.set_xy(x_start + sum(col_widths[:4]), y_start)
            
            # Truncate description to fit in one row (max ~45 chars)
            max_chars = 45
            if len(desc) > max_chars:
                desc = desc[:max_chars - 3] + "..."
            pdf.cell(col_widths[4], row_height, desc, border=1, align="L")

            # Move to next row
            pdf.set_xy(x_start, y_start + row_height)
            row_index += 1

        # 6. Summary Section
        pdf.ln(8)
        net_balance = total_income - total_expense

        pdf.set_font("Arial", style="B", size=10)
        
        # Income box
        pdf.set_fill_color(200, 240, 200)
        pdf.set_text_color(0, 100, 0)
        pdf.cell(95, 10, f"Total Income: {total_income:.2f}", border=1, fill=True, align="C")

        # Expense box
        pdf.set_fill_color(255, 210, 210)
        pdf.set_text_color(150, 0, 0)
        pdf.cell(95, 10, f"Total Expense: {total_expense:.2f}", border=1, fill=True, align="C", ln=True)

        # Net balance box
        pdf.ln(3)
        if net_balance >= 0:
            pdf.set_fill_color(200, 220, 255)
            pdf.set_text_color(0, 0, 150)
        else:
            pdf.set_fill_color(255, 200, 200)
            pdf.set_text_color(150, 0, 0)
        
        pdf.set_font("Arial", style="B", size=11)
        pdf.cell(190, 12, f"Net Balance: {net_balance:.2f}", border=1, fill=True, align="C", ln=True)

        # Transaction count
        pdf.ln(3)
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Total Transactions: {len(transactions)}", ln=True, align="C")

        # 7. Return PDF
        pdf_bytes = pdf.output()
        
        logger.info("PDF export successful for user: %s", current_user_id)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=transactions_statement.pdf"}
        )

    except Exception as e:
        logger.error(f"Error exporting PDF for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")

@app.post("/transactions/process-recurring", tags=["Transactions"])
def process_recurring(current_user_id: str = Depends(get_current_user)):
    logger.info(f"Starting recurring transaction processing for user: {current_user_id}")

    try:
        # Load JSON data
        data = load_data()
        today = date.today()
        current_day = today.day
        current_month = today.strftime("%Y-%m")
        logger.info(f"Processing recurring transactions for date: {today}")

        new_transactions = []
        # Loop through all transactions
        for transaction_id, transaction in data["transactions"].items():
            # Check user
            if transaction["user_id"] != current_user_id:
                continue
            # Check recurring
            if transaction.get("is_recurring") is not True:
                continue
            # Check recurrence day
                    # FIX 3: Handle month-end edge cases (e.g., 31st of the month)
            recurrence_day = transaction.get("recurrence_day")
            is_last_day_of_month = (today + timedelta(days=1)).month != today.month
            
            if recurrence_day != current_day:
            # If today is the last day of the month, also trigger transactions set for 28, 29, 30, or 31
                if not (is_last_day_of_month and recurrence_day >= 28):
                    continue
            logger.info(f"Recurring transaction matched: {transaction_id} "f"({transaction['category']})")

            # Check if same category + type already exists
            # in the current month
            already_exists = False
            for existing_transaction in data["transactions"].values():
                if (existing_transaction["user_id"] == current_user_id and existing_transaction["category"]
                    == transaction["category"] and existing_transaction["type"] == transaction["type"]
                    and existing_transaction["dates"].startswith(current_month)):
                    already_exists = True
                    logger.info(f"Skipping duplicate recurring transaction: "
                        f"{transaction['category']} - "f"{transaction['type']}")
                    break
            if already_exists:
                continue
                    # Create a copy
            new_transaction = transaction.copy()
            
            # FIX 6: Set currency from user's profile
            new_transaction["currency"] = data["users"][current_user_id].get("currency", "INR")
            # Generate new transaction ID
            existing_ids = []
            for transaction_id in data["transactions"]:
                if transaction_id.startswith("t_"):
                    try:
                        existing_ids.append(int(transaction_id.split("_")[1]))
                    except ValueError:
                        continue
            if existing_ids:
                new_transaction_id = f"t_{max(existing_ids) + 1}"
            else:
                new_transaction_id = "t_1001"
            # Update date
            new_transaction["dates"] = today.isoformat()
            # Generated transaction is not the recurring template
            new_transaction["is_recurring"] = False
            new_transactions.append((new_transaction_id, new_transaction))

            logger.info(f"New recurring transaction prepared: "f"{new_transaction_id} - "f"{new_transaction['category']}")

        # Add generated transactions
        for transaction_id, transaction in new_transactions:
            data["transactions"][transaction_id] = transaction
        # Save only if transactions were generated
        if new_transactions:
            save_data(data)
            logger.info(f"Generated {len(new_transactions)} recurring transactions "
                f"for user: {current_user_id}")
        else:
            logger.info(f"No recurring transactions generated for user: "
                f"{current_user_id}")

        return {
            "message": "Recurring transactions processed successfully",
            "generated_count": len(new_transactions),
            "transactions": [
                {
                    "transaction_id": transaction_id,
                    "category": transaction["category"],
                    "type": transaction["type"],
                    "dates": transaction["dates"]
                }
                for transaction_id, transaction in new_transactions
            ]
        }

    except Exception as e:
        logger.error(f"Error processing recurring transactions "f"for user {current_user_id}: {str(e)}",
            exc_info=True)
        raise

@app.get("/transactions/{transaction_id}", tags=["Transactions"])
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
        # NEW: Check if soft-deleted
        if transaction.get("deleted_at"):
            logger.warning("User %s tried to access deleted transaction %s", user_id, transaction_id)
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        logger.info("Transaction %s returned successfully for user %s", transaction_id, user_id)
        return transaction
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch transaction %s for user %s", transaction_id, user_id)
        raise
