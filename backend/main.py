from fastapi import FastAPI, HTTPException, Path, Query , Header
from datetime import date
import json
from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from enum import Enum

app = FastAPI()
def load_data():
    with open("transactions.json", "r") as f:
        data = json.load(f)
        return data
    
def save_data(data):
    with open('transactions.json','w') as f:
        json.dump(data, f, indent=4)

class TransactionPaymentMethod(str, Enum):
    DebitCard= "Debit Card"
    CreditCard= "Credit Card"
    UPI="UPI"
    CASH="Cash"
    BankTransfer="Bank Transfer"

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

class TransactionMerchant(str, Enum):
    EmployerPayroll ="Employer Payroll"
    ApartmentManagement="Apartment Management"
    LocalGroceryRestaurant= "Local Grocery & Restaurant"
    LocalTransport="Local Transport"
    UtilityProvider ="Utility Provider"
    FreelanceClient ="Freelance Client"
    EntertainmentService ="Entertainment Service"
    HealthcareProvider ="Healthcare Provider"
    RetailStore= "Retail Store"
    OnlineLearningPlatform ="Online Learning Platform"
    FAMILY = "Family"

class TransactionStatus(str, Enum):
    COMPLETED = "completed"  
    PENDING="pending"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
class Transaction(BaseModel):
    type: Annotated[Literal["income", "expense"], Field(..., description="Type of transaction: income or expense")]
    category: Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(..., description="Amount of transaction", gt=0)
    currency: str=Field(..., description="Currency of transaction")
    dates: date=Field(..., description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")
    merchant: Annotated[Optional[str], Field(None, max_length=100, description="Description of where user spend money")]
    payment_method: TransactionPaymentMethod=None
    status: Optional[TransactionStatus]=None
    notes:Optional[str]=None

class TransactionUpdate(BaseModel):
    type: Optional[Literal["income", "expense"]]=Field(None, description="Type of transaction: income or expense")
    category: Optional[TransactionCategory]=Field(None, description="Category of transaction")
    amount: Optional[float]=Field(None, description="Amount of transaction", gt=0)
    currency: Optional[str]=Field(None, description="Currency of transaction")
    dates: Optional[date]=Field(None, description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")
    merchant: Annotated[Optional[TransactionMerchant], Field(None,max_length=100, description="Description of where user spend money")]
    payment_method: Optional[TransactionPaymentMethod] =None
    status: Optional[TransactionStatus]=None
    notes:Optional[str]=None
    
    
class User(BaseModel):
    username: str=Field(..., description="Username of the user")
    password: str=Field(..., description="Password of the user")
    created_at: Optional[date]=Field(default=date.today(), description="Date of user creation")

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
    user_id: str = Header(...)):
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
        if match:
            filtered_data[transaction_id] = transaction_info
    
    return filtered_data

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
    data["users"][new_user_id] = users.model_dump(mode="json", exclude_unset=True)
    save_data(data)
    return JSONResponse(status_code=201,content={"message": "User registered successfully.", "id": new_user_id})

@app.post("/users/login")
def verify_user(users:User):
    data = load_data()
    
    for user_id, value in data["users"].items():
         if value["username"] == users.username:
            if value["password"] == users.password:
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
    transactions_id = generate_transaction_id(data, user_id)
    if user_id not in data["users"]:
        raise HTTPException(status_code=404, detail="User ID not found.")
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
    return JSONResponse(status_code=201, content={"message":"Transaction updated successfully.", "user_id":user_id, "application":data["transactions"][transaction_id]})
    
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
    

    