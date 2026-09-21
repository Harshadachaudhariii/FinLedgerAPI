from fastapi import FastAPI, HTTPException, Path, Query , Header
from datetime import date
import json
from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from fastapi.responses import JSONResponse
from enum import Enum

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

class BudgetCreate(BaseModel):
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(...,description="Amount of transaction", gt=0)
    month: str = Field(...,description="Month of transaction in YYYY-MM format",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    
class Budget(BaseModel):
    # category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    # amount: float=Field(...,description="Amount of transaction", gt=0)
    # period: 
    # month: str = Field(...,description="Month of transaction in YYYY-MM format",
    #         pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    # created_at:
    pass
        
class BudgetStatus(BaseModel):
    pass

 

