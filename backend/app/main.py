from fastapi import FastAPI, HTTPException, Path, Query, APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional,Literal
from datetime import date, datetime
from app.routes.budget_system import router as budget_router
from app.routes.analytics import router as analytics_router
from app.utils.data import load_data, save_data
from app.utils.logger import *
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user, add_token_to_blocklist, check_rate_limit, record_failed_login, oauth2_scheme
from app.enums.transaction import *
from app.model.user import *
from app.model.transactions import *
from fastapi import UploadFile, File
import csv
import io
app = FastAPI()

# Allow all origins for development. In production, specify your frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["http://localhost:3000"] in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
            if transaction_info.get("deleted_at"):
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
                filtered_data[transaction_id] = {"id": transaction_id, **transaction_info}

        logger.info("Filtered transactions returned %s results for user %s", len(filtered_data), user_id)
        return list(filtered_data.values())
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

# Create a dedicated schema for login requests in your Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/users/login")
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