from enum import Enum

class TransactionPaymentMethod(str, Enum):
    DebitCard= "Debit Card"
    CreditCard= "Credit Card"
    UPI="UPI"
    CASH="Cash"
    BankTransfer="Bank Transfer"


class TransactionCategory(str, Enum):
    # --- HOUSING & UTILITIES ---
    RENT = "Rent"
    MORTGAGE = "Mortgage"
    UTILITIES = "Utilities"
    INTERNET_PHONE = "Internet & Phone"
    HOME_MAINTENANCE = "Home Maintenance"
    INSURANCE = "Insurance"

    # --- FOOD & DINING ---
    FOOD = "Food"
    GROCERIES = "Groceries"
    DINING_OUT = "Dining Out"
    COFFEE_SHOPS = "Coffee Shops"

    # --- TRANSPORTATION ---
    TRANSPORT = "Transport"
    FUEL = "Fuel"
    CAR_MAINTENANCE = "Car Maintenance"
    TAXI_RIDE_SHARE = "Taxi & Ride Share"
    PUBLIC_TRANSIT = "Public Transit"

    # --- SHOPPING & PERSONAL ---
    SHOPPING = "Shopping"
    CLOTHING = "Clothing"
    PERSONAL_CARE = "Personal Care"
    ELECTRONICS = "Electronics"
    HOUSEHOLD_SUPPLIES = "Household Supplies"

    # --- HEALTH & WELLNESS ---
    HEALTH = "Health"
    PHARMACY = "Pharmacy"
    GYM_FITNESS = "Gym & Fitness"
    DENTAL_VISION = "Dental & Vision"

    # --- ENTERTAINMENT & LIFESTYLE ---
    ENTERTAINMENT = "Entertainment"
    SUBSCRIPTIONS = "Subscriptions"
    TRAVEL = "Travel"
    HOBBIES = "Hobbies"
    GAMING = "Gaming"

    # --- FINANCIAL & DEBT ---
    SAVINGS = "Savings"
    INVESTMENTS = "Investments"
    DEBT_REPAYMENT = "Debt Repayment"
    CREDIT_CARD_PAYMENT = "Credit Card Payment"
    TAXES = "Taxes"
    CHARITY = "Charity"

    # --- EDUCATION & FAMILY ---
    EDUCATION = "Education"
    CHILDCARE = "Childcare"
    PETS = "Pets"
    DONATIONS = "Donations"
    GIFT = "Gift"

    # --- INCOME ---
    SALARY = "Salary"
    FREELANCE = "Freelance"
    BONUS = "Bonus"
    GIFT_RECEIVED = "Gift Received"
    DIVIDENDS = "Dividends"
    INTEREST = "Interest"
    REFUNDS = "Refunds"
    BUSINESS_INCOME = "Business Income"
    RENTAL_INCOME = "Rental Income"

    # --- OTHER ---
    OTHER = "Other"

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
    
