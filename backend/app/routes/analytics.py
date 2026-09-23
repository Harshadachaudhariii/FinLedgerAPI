from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import date

from typing import Optional
from fastapi.responses import JSONResponse
from app.utils.data import load_data, save_data
from app.utils.security import get_current_user
from app.utils.logger import logger

router = APIRouter()

def get_filtered_expenses(data, user_id, start_date, end_date):
    filtered_expenses = []

    for transaction_id, transaction_info in data["transactions"].items():

        # Check user ownership
        if transaction_info["user_id"] != user_id:
            continue

        # Only expenses
        if transaction_info["type"] != "expense":
            continue

        # Convert transaction date string to date
        transaction_date = date.fromisoformat(transaction_info["dates"])

        # Check date range
        if transaction_date < start_date:
            continue

        if transaction_date > end_date:
            continue

        # All conditions passed
        filtered_expenses.append(transaction_info)

    return filtered_expenses

@router.get("/average-daily-spend")
def daily_average_spent(start_date: Optional[date] = Query(None, 
    description="Start date for daily spending average"),
    end_date: Optional[date] = Query(None, description="End date for daily spending average"),
    user_id:str=Depends(get_current_user)):
    try:
        data = load_data()

        total_expense =0.0

        today = date.today()
        if start_date is None:
            start_date = today.replace(day=1)

        if end_date is None:
            end_date = today

        days_in_period = (end_date - start_date).days + 1
        filtered_expenses = get_filtered_expenses(
            data,
            user_id,
            start_date,
            end_date
        )

        for transaction in filtered_expenses:
            total_expense += transaction["amount"]

        average_daily_spend = total_expense/days_in_period
        logger.info("Calculated average daily spend for user %s: %s", user_id, average_daily_spend)
        return JSONResponse(status_code=200, content={
            "user_id":user_id,
            "period":{
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_expenses":total_expense,
            "days_in_periods":days_in_period,
            "average_daily_spend":average_daily_spend
        })
    except Exception:
        logger.exception("Failed to calculate average daily spend for user %s", user_id)
        raise

@router.get("/month-over-month")
def month_over_month_comparing(
    target_month: Optional[str] = Query(
        None,
        description="Target month in YYYY-MM format"
    ),
    user_id: str = Depends(get_current_user)
):
    try:
        data = load_data()

        # 1. Set target month
        if target_month is None:
            target_month = date.today().strftime("%Y-%m")

        # 2. Calculate previous month
        year, month = map(int, target_month.split("-"))

        if month == 1:
            previous_year = year - 1
            previous_month = 12
        else:
            previous_year = year
            previous_month = month - 1

        previous_month_str = f"{previous_year:04d}-{previous_month:02d}"

        # 3. Calculate current month's start and end date
        current_start_date = date(year, month, 1)

        if month == 12:
            current_end_date = date(year + 1, 1, 1) - date.resolution
        else:
            current_end_date = date(year, month + 1, 1) - date.resolution

        # 4. Calculate previous month's start and end date
        previous_start_date = date(previous_year, previous_month, 1)

        if previous_month == 12:
            previous_end_date = date(previous_year + 1, 1, 1) - date.resolution
        else:
            previous_end_date = date(
                previous_year,
                previous_month + 1,
                1
            ) - date.resolution

        # 5. Filter current month expenses
        current_expenses = get_filtered_expenses(
            data,
            user_id,
            current_start_date,
            current_end_date
        )

        # 6. Filter previous month expenses
        previous_expenses = get_filtered_expenses(
            data,
            user_id,
            previous_start_date,
            previous_end_date
        )

        # 7. Calculate current month spending
        current_month_spending = 0.0

        for transaction in current_expenses:
            current_month_spending += transaction["amount"]

        # 8. Calculate previous month spending
        previous_month_spending = 0.0

        for transaction in previous_expenses:
            previous_month_spending += transaction["amount"]

        # 9. Calculate growth percentage and trend
        if current_month_spending == 0:
            growth_percentage = None
            trend = "No data for current month"

        elif previous_month_spending == 0:
            growth_percentage = None
            trend = "No data for previous month"

        else:
            growth_percentage = (
                (current_month_spending - previous_month_spending)
                / previous_month_spending
            ) * 100

            # 10. Calculate trend
            if growth_percentage > 0:
                trend = "increased"

            elif growth_percentage < 0:
                trend = "decreased"

            else:
                trend = "stable"

        logger.info("Month-over-month analytics generated for user %s: month=%s, growth=%s", user_id, target_month, growth_percentage)
        return JSONResponse(
            status_code=200,
            content={
                "user_id": user_id,
                "current_month": target_month,
                "previous_month": previous_month_str,
                "current_month_spending": current_month_spending,
                "previous_month_spending": previous_month_spending,
                "growth_percentage": growth_percentage,
                "trend": trend
            }
        )
    except Exception:
        logger.exception("Failed to generate month-over-month analytics for user %s", user_id)
        raise
    
@router.get("/highest-spending-day")
def highest_spending_in_day(start_date: Optional[date] = Query(None,
    description="Start date for highest spending day"),
    end_date: Optional[date] = Query(None,
    description="End date for highest spending day"),user_id: str = Depends(get_current_user)):
    try:
        data = load_data()

        daily_totals = {}
        daily_counts = {}

        for transaction_id, transaction_info in data["transactions"].items():

            # Check user
            if transaction_info["user_id"] != user_id:
                continue

            # Convert transaction date from string to date
            transaction_date = date.fromisoformat(transaction_info["dates"])

            # Date range filter
            if start_date is not None and transaction_date < start_date:
                continue

            if end_date is not None and transaction_date > end_date:
                continue

            # Only expenses
            if transaction_info["type"] != "expense":
                continue

            amount = transaction_info["amount"]
            transaction_day = transaction_date.isoformat()

            # Calculate daily total
            if transaction_day in daily_totals:
                daily_totals[transaction_day] += amount
                daily_counts[transaction_day] += 1
            else:
                daily_totals[transaction_day] = amount
                daily_counts[transaction_day] = 1

        # No expenses found
        if not daily_totals:
            logger.warning("No expenses found for highest spending day analytics for user %s", user_id)
            raise HTTPException(
                status_code=404,
                detail="No expenses found for the selected period.")

        # Find highest spending day
        highest_spending_date = max(
            daily_totals,
            key=daily_totals.get)
        amount_spent = round(daily_totals[highest_spending_date],2)
        transaction_count = daily_counts[highest_spending_date]
        logger.info("Highest spending day calculated for user %s: %s with total %s", user_id, highest_spending_date, amount_spent)
        return JSONResponse(
            status_code=200,
            content={
                "user_id": user_id,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "highest_spending_date": highest_spending_date,
                "amount_spent": amount_spent,
                "transaction_count_on_that_day": transaction_count
            }
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to calculate highest spending day for user %s", user_id)
        raise
