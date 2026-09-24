from fastapi import HTTPException, Path, Query, Header, APIRouter, Depends
from datetime import date
from typing import Optional
from fastapi.responses import JSONResponse
from app.utils.data import load_data, save_data
from app.model.budget import *
from app.enums.budget import BudgetStatusType, TransactionCategory
from app.utils.security import get_current_user
from app.utils.logger import logger
from datetime import datetime

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
                logger.warning("Invalid budget key format encountered: %s", key)

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
    # FIX: Removed `data = load_data()` so it uses the passed parameter
    total_spent = 0.0
    for transaction_id, transaction_info in data.get("transactions", {}).items():
        if transaction_info.get("user_id") == user_id and transaction_info.get("type") == "expense":
            if transaction_info.get("category") == category:
                transaction_month = date.fromisoformat(transaction_info["dates"]).strftime("%Y-%m")
                if transaction_month == month:
                    total_spent += transaction_info["amount"]
    return total_spent

@router.get("")
def get_budgets(user_id: str = Depends(get_current_user), month: Optional[str] = Query(None)):
    try:
        data = load_data()
        budgets = []
        for budgets_id, budgets_info in data["budgets"].items():
            if budgets_info["user_id"] != user_id:
                continue

            if month is not None and budgets_info["month"] != month:
                continue
            budgets.append(budgets_info)
        logger.info("Fetched budgets for user %s, month=%s", user_id, month)
        return budgets
    except Exception:
        logger.exception("Failed to fetch budgets for user %s", user_id)
        raise

@router.get("/{budget_id}", tags=["Budgets"])
def get_single_budget(budget_id: str,current_user_id: str = Depends(get_current_user)):
    logger.info("Fetching budget: %s for user: %s",budget_id,current_user_id)

    try:
        data = load_data()
        budget = data.get("budgets", {}).get(budget_id)

        if not budget:
            logger.warning("Budget not found: %s for user: %s",budget_id,current_user_id)
            raise HTTPException(status_code=404,detail="Budget not found")

        if budget.get("user_id") != current_user_id:
            logger.warning("Unauthorized budget access attempt: budget=%s | user=%s",budget_id,current_user_id)
            raise HTTPException(status_code=404,detail="Budget not found")

        logger.info("Budget retrieved successfully: %s for user: %s",budget_id,current_user_id)
        return budget

    except HTTPException:
        raise

    except Exception:
        logger.exception("Failed to retrieve budget: %s for user: %s",budget_id,current_user_id)
        raise

@router.get("/status", tags=["Budgets"])
def get_budget_status(user_id: str = Depends(get_current_user),month: Optional[str] = Query(None)):
    logger.info("Fetching budget status for user: %s | month=%s",user_id,month)
    try:
        data = load_data()
        if month is None:
            month = date.today().strftime("%Y-%m")
            logger.info("No month provided. Using current month: %s",month)
        budget_statuses = []
        for budgets_id, budgets_info in data.get("budgets", {}).items():
            if budgets_info.get("user_id") != user_id:
                continue
            if budgets_info.get("month") != month:
                continue
            budgeted_amount = budgets_info["amount"]
            spent_amount = calculate_category_spending(
                data,
                user_id,
                budgets_info["category"],
                month
            )
            remaining = budgeted_amount - spent_amount

            percentage_used = (spent_amount / budgeted_amount * 100
                if budgeted_amount > 0 else 0.0
            )

            if percentage_used < 90:
                status = "on_track"
            elif percentage_used < 100:
                status = "warning"
            else:
                status = "exceeded"

            budget_statuses.append({
                "budget_id": budgets_id,
                "category": budgets_info["category"],
                "month": month,
                "budget_amount": budgeted_amount,
                "spent_amount": spent_amount,
                "remaining_amount": remaining,
                "percentage_used": round(percentage_used, 2),
                "status": status
            })

            logger.info(
                "Budget status calculated: budget_id=%s | category=%s | status=%s | percentage_used=%.2f",
                budgets_id,budgets_info["category"],status,percentage_used)

        logger.info("Budget status retrieved successfully for user: %s | month=%s | budgets_found=%s",
            user_id,month,len(budget_statuses))

        return {
            "user_id": user_id,
            "month": month,
            "budgets_status": budget_statuses
        }

    except Exception:
        logger.exception("Failed to retrieve budget status for user: %s | month=%s",user_id,month)
        raise
            
@router.post("/create")
def create_budget(budget: BudgetCreate, user_id: str = Depends(get_current_user)):
    try:
        data = load_data()
        for budget_id, budget_info in data["budgets"].items():
            if (
                budget_info["user_id"] == user_id
                and budget_info["category"] == budget.category
                and budget_info["month"] == budget.month
            ):
                logger.warning("Duplicate budget creation attempt by user %s for category %s, month %s", user_id, budget.category, budget.month)
                raise HTTPException(status_code=409, detail="Budget already exists")
        budget_id = generate_budget_id(data,user_id)
        budget_data = budget.model_dump(mode="json", exclude_unset=True)
        budget_data["user_id"] = user_id
        data["budgets"][budget_id] = budget_data
        save_data(data)
        logger.info("Budget created successfully for user %s with ID %s", user_id, budget_id)
        return JSONResponse(status_code=201, content={"message":"Budget created successfully.","user_id":user_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while creating budget for user %s", user_id)
        raise

@router.put("/update/{budget_id}")
def update_budget(budget_id: str, budget_update: BudgetUpdate, user_id: str = Depends(get_current_user)):
    try:
        data = load_data()
        if budget_id not in data["budgets"]:
            logger.warning("Budget update failed: budget_id %s not found for user %s", budget_id, user_id)
            raise HTTPException(
                    status_code=404,
                    detail="budget_id ID not found"
                )
        if data["budgets"][budget_id]["user_id"] != user_id:
            logger.warning("Budget update forbidden for user %s on budget %s", user_id, budget_id)
            raise HTTPException(status_code=403, detail="You haven't ownership to this budgets")
        existing_budget_info = data["budgets"][budget_id]
        update_budgets_info = budget_update.model_dump(mode="json", exclude_unset=True)
        existing_budget_info.update(update_budgets_info)
        data["budgets"][budget_id] = existing_budget_info

        save_data(data)
        logger.info("Budget updated successfully for user %s and budget %s", user_id, budget_id)
        return JSONResponse(status_code=200, content={"message":"budgets updated successfully.", "user_id":user_id, "budgets":data["budgets"][budget_id]})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while updating budget %s for user %s", budget_id, user_id)
        raise

@router.delete("/delete/{budget_id}")
def delete_budget(budget_id: str, user_id:str=Depends(get_current_user)):
    try:
        data = load_data()

        if budget_id not in data["budgets"]:
                logger.warning("Budget delete failed: budget_id %s not found for user %s", budget_id, user_id)
                raise HTTPException(
                    status_code=404,
                    detail="Budget ID not found"
                )
        if data["budgets"][budget_id]["user_id"] != user_id:
            logger.warning("Budget delete forbidden for user %s on budget %s", user_id, budget_id)
            raise HTTPException(status_code=403, detail="You don't have ownership of this budgets")

        data["budgets"][budget_id]["deleted_at"] = datetime.now().isoformat()

        save_data(data)
        logger.info("Budget deleted successfully: %s for user %s", budget_id, user_id)

        return JSONResponse(status_code=200, content={"message":"Budgets deleted successfully.","budget_id":budget_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while deleting budget %s for user %s", budget_id, user_id)
        raise
        