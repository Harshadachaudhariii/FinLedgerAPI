from fastapi import FastAPI, HTTPException, Path, Query 
from datetime import date
import json
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from fastapi.responses import JSONResponse

app = FastAPI()
def load_data():
    with open("transactions.json", "r") as f:
        data = json.load(f)
        return data
    
def save_data(data):
    with open('transactions.json','w') as f:
        json.dump(data, f, indent=4)
        
class Transaction(BaseModel):
    user_id: str = Field(..., description="ID of the user who owns the transaction")
    type: str=Field(..., description="Type of transaction: income or expense")
    category: str=Field(..., description="Category of transaction")
    amount: float=Field(..., description="Amount of transaction")
    currency: str=Field(..., description="Currency of transaction")
    dates: date=Field(..., description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")

class TransactionUpdate(BaseModel):
    user_id: Optional[str] = Field(
    None,
    description="ID of the user who owns the transaction"
)
    type: Optional[str]=Field(None, description="Type of transaction: income or expense")
    category: Optional[str]=Field(None, description="Category of transaction")
    amount: Optional[float]=Field(None, description="Amount of transaction")
    currency: Optional[str]=Field(None, description="Currency of transaction")
    dates: Optional[date]=Field(None, description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")
    
class User(BaseModel):
    username: str=Field(..., description="Username of the user")
    password: str=Field(..., description="Password of the user")

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
def view_transactions():
    data = load_data()
    return data

@app.get("/transactions/{transaction_id}")
def view_transaction(transaction_id: str):
    data =load_data()
    if transaction_id in data["transactions"]:
        return data["transactions"][transaction_id]  
    raise HTTPException(status_code=404, detail="Transaction ID not found.")  

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
            if value["password_hash"] == users.password:
                 return JSONResponse(
                            status_code=200,
                            content={
                                    "message": "User login successfully.",
                                    "user_id": user_id
                                }
                            )
    raise HTTPException(status_code=401, detail="Invalid username and password")
    
    


    

    
    
    
    