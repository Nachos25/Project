from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
import pandas as pd
from . import models, schemas
from .database import get_db, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get(
    "/user_credits/{user_id}",
    response_model=schemas.UserCredits
)
def get_user_credits(
    user_id: int,
    db: Session = Depends(get_db)
):
    logger.info(f"Getting credits for user_id: {user_id}")
    credits = (
        db.query(models.Credit)
        .filter(models.Credit.user_id == user_id)
        .all()
    )
    logger.info(f"Found credits: {credits}")

    if not credits:
        logger.warning(f"No credits found for user_id: {user_id}")
        raise HTTPException(
            status_code=404,
            detail="User credits not found"
        )

    result = []
    for credit in credits:
        logger.info(f"Processing credit: {credit.id}")
        payments = (
            db.query(models.Payment)
            .filter(models.Payment.credit_id == credit.id)
            .all()
        )
        logger.info(f"Found payments: {len(payments)}")
        total_payments = sum(payment.sum for payment in payments)

        is_closed = credit.actual_return_date is not None
        base_credit = {
            "issuance_date": credit.issuance_date,
            "is_closed": is_closed,
            "body": credit.body,
            "percent": credit.percent
        }

        if is_closed:
            result.append(
                schemas.ClosedCredit(
                    **base_credit,
                    actual_return_date=credit.actual_return_date,
                    total_payments=total_payments
                )
            )
        else:
            # Предполагаем, что type_id=1 для тела кредита
            body_payments = sum(
                p.sum for p in payments if p.type_id == 1
            )
            # type_id=2 для процентов
            percent_payments = sum(
                p.sum for p in payments if p.type_id == 2
            )

            overdue_days = 0
            if date.today() > credit.return_date:
                overdue_days = (
                    date.today() - credit.return_date
                ).days

            result.append(
                schemas.OpenCredit(
                    **base_credit,
                    return_date=credit.return_date,
                    overdue_days=overdue_days,
                    body_payments=body_payments,
                    percent_payments=percent_payments
                )
            )

    return schemas.UserCredits(credits=result)


@app.post("/plans_insert")
async def insert_plans(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        if not file.filename.endswith('.xlsx'):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files are allowed"
            )

        df = pd.read_excel(file.file)
        required_columns = ['month', 'category', 'sum']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format"
            )

        # Проверка на пустые значения в столбце sum
        if df['sum'].isnull().any():
            raise HTTPException(
                status_code=400,
                detail="Sum column contains empty values"
            )

        for _, row in df.iterrows():
            try:
                # Конвертация даты с учетом разных форматов
                if isinstance(row['month'], str):
                    try:
                        plan_date = datetime.strptime(row['month'], '%d.%m.%Y')
                    except ValueError:
                        plan_date = pd.to_datetime(row['month'])
                else:
                    plan_date = pd.to_datetime(row['month'])

                if plan_date.day != 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Plan date must be the first day of month. Got: {plan_date.date()}"
                    )

                # Получаем id категории
                category = (
                    db.query(models.Dictionary)
                    .filter(models.Dictionary.name == row['category'])
                    .first()
                )
                if not category:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Category {row['category']} not found"
                    )

                # Проверка на существующий план
                existing_plan = (
                    db.query(models.Plan)
                    .filter(
                        models.Plan.period == plan_date.date(),
                        models.Plan.category_id == category.id
                    )
                    .first()
                )

                if existing_plan:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Plan for {plan_date.date()} and "
                            f"category {row['category']} already exists"
                        )
                    )

                # Создаем новый план
                new_plan = models.Plan(
                    period=plan_date.date(),
                    sum=float(row['sum']),
                    category_id=category.id
                )
                db.add(new_plan)

            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error processing row: {row.to_dict()}. Error: {str(e)}"
                )

        db.commit()
        return {"message": "Plans successfully inserted"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error inserting plans: {str(e)}"
        )


@app.get(
    "/plans_performance/{check_date}",
    response_model=list[schemas.PlanPerformance]
)
def get_plans_performance(
    check_date: date,
    db: Session = Depends(get_db)
):
    check_date = datetime.combine(check_date, datetime.min.time())
    result = []

    plans = db.query(models.Plan).all()
    for plan in plans:
        category = (
            db.query(models.Dictionary)
            .filter(models.Dictionary.id == plan.category_id)
            .first()
        )

        # Определяем начало месяца плана
        start_date = plan.period

        if category.name == "видача":
            actual_sum = (
                db.query(models.Credit)
                .filter(
                    models.Credit.issuance_date >= start_date,
                    models.Credit.issuance_date <= check_date
                )
                .with_entities(func.sum(models.Credit.body))
                .scalar() or 0
            )
        else:  # "збір"
            actual_sum = (
                db.query(models.Payment)
                .filter(
                    models.Payment.payment_date >= start_date,
                    models.Payment.payment_date <= check_date
                )
                .with_entities(func.sum(models.Payment.sum))
                .scalar() or 0
            )

        performance = (
            (actual_sum / plan.sum * 100)
            if plan.sum > 0 else 0
        )

        result.append(
            schemas.PlanPerformance(
                plan_month=plan.period,
                category=category.name,
                plan_sum=plan.sum,
                actual_sum=actual_sum,
                performance_percent=performance
            )
        )

    return result


@app.get(
    "/year_performance/{year}",
    response_model=schemas.YearPerformance
)
def get_year_performance(year: int, db: Session = Depends(get_db)):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    # Получаем общие суммы за год для расчета процентов
    total_year_issuance = (
        db.query(models.Credit)
        .filter(
            models.Credit.issuance_date >= start_date,
            models.Credit.issuance_date <= end_date
        )
        .with_entities(func.sum(models.Credit.body))
        .scalar() or 0
    )

    total_year_payments = (
        db.query(models.Payment)
        .filter(
            models.Payment.payment_date >= start_date,
            models.Payment.payment_date <= end_date
        )
        .with_entities(func.sum(models.Payment.sum))
        .scalar() or 0
    )

    result = []
    for month in range(1, 13):
        month_start = date(year, month, 1)
        month_end = (
            date(year, month + 1, 1)
            if month < 12
            else date(year + 1, 1, 1)
        )

        # Данные по выдачам
        issuance_data = (
            db.query(
                func.count(models.Credit.id),
                func.sum(models.Credit.body)
            )
            .filter(
                models.Credit.issuance_date >= month_start,
                models.Credit.issuance_date < month_end
            )
            .first()
        )

        issuance_count = issuance_data[0] or 0
        issuance_sum = issuance_data[1] or 0

        # Данные по платежам
        payment_data = (
            db.query(
                func.count(models.Payment.id),
                func.sum(models.Payment.sum)
            )
            .filter(
                models.Payment.payment_date >= month_start,
                models.Payment.payment_date < month_end
            )
            .first()
        )

        payment_count = payment_data[0] or 0
        payment_sum = payment_data[1] or 0

        # Получаем планы на месяц
        issuance_plan = (
            db.query(models.Plan)
            .join(models.Dictionary)
            .filter(
                models.Plan.period == month_start,
                models.Dictionary.name == "видача"
            )
            .with_entities(models.Plan.sum)
            .scalar() or 0
        )

        payment_plan = (
            db.query(models.Plan)
            .join(models.Dictionary)
            .filter(
                models.Plan.period == month_start,
                models.Dictionary.name == "збір"
            )
            .with_entities(models.Plan.sum)
            .scalar() or 0
        )

        # Расчет процентов выполнения планов
        issuance_performance = (
            (issuance_sum / issuance_plan * 100)
            if issuance_plan > 0 else 0
        )
        payment_performance = (
            (payment_sum / payment_plan * 100)
            if payment_plan > 0 else 0
        )

        # Расчет процентов от годовых сумм
        issuance_year_percent = (
            (issuance_sum / total_year_issuance * 100)
            if total_year_issuance > 0 else 0
        )
        payment_year_percent = (
            (payment_sum / total_year_payments * 100)
            if total_year_payments > 0 else 0
        )

        result.append(
            schemas.YearPerformanceMonth(
                month_year=month_start,
                issuance_count=issuance_count,
                issuance_plan=issuance_plan,
                issuance_sum=issuance_sum,
                issuance_performance=issuance_performance,
                payment_count=payment_count,
                payment_plan=payment_plan,
                payment_sum=payment_sum,
                payment_performance=payment_performance,
                issuance_year_percent=issuance_year_percent,
                payment_year_percent=payment_year_percent
            )
        )

    return schemas.YearPerformance(performance=result)
