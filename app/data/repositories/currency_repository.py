from datetime import datetime, timedelta

from sqlalchemy import Column, Date, Float
from sqlalchemy.orm import sessionmaker

from app.data.base import Base, engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class CurrencyRatesORM(Base):
    __tablename__ = "currency_rates"
    date = Column(Date, nullable=False, primary_key=True)
    EURO = Column(Float, nullable=False)  # Exchange rate: 1 CNY = X EURO
    USD = Column(Float, nullable=False)  # Exchange rate: 1 CNY = X USD


def create_currency_rates_table():
    Base.metadata.create_all(bind=engine)


def get_currency_rates(db, date: datetime):
    return (
        db.query(CurrencyRatesORM).filter(CurrencyRatesORM.date == date.date()).first()
    )


def set_currency_rates(db, date: datetime, euro_rate: float, usd_rate: float):
    obj = (
        db.query(CurrencyRatesORM).filter(CurrencyRatesORM.date == date.date()).first()
    )
    if obj:
        obj.EURO = euro_rate
        obj.USD = usd_rate
    else:
        obj = CurrencyRatesORM(date=date.date(), EURO=euro_rate, USD=usd_rate)
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_rates_from_api(db, api_result: dict):
    rates = api_result.get("rates", {})
    start_date = datetime.strptime(api_result["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(api_result["end_date"], "%Y-%m-%d").date()
    current_date = start_date
    last_euro = last_usd = None

    # Prepare a sorted list of available dates
    rates_by_date = {
        datetime.strptime(d, "%Y-%m-%d").date(): v for d, v in rates.items()
    }

    while current_date <= end_date:
        # Find rate for current_date or fallback to last known
        if current_date in rates_by_date:
            euro = rates_by_date[current_date].get("EUR")
            usd = rates_by_date[current_date].get("USD")
            last_euro = euro
            last_usd = usd
        else:
            euro = last_euro
            usd = last_usd
        if euro is not None and usd is not None:
            # Convert current_date (date) to datetime for set_currency_rates
            set_currency_rates(
                db, datetime.combine(current_date, datetime.min.time()), euro, usd
            )
        current_date += timedelta(days=1)


def has_currency_data_for_range(db, start_date: datetime, end_date: datetime) -> bool:
    """
    Returns True if currency data exists for all dates in
    the range [start_date, end_date], else False.
    """
    # Convert to date objects
    start = start_date.date()
    end = end_date.date()
    total_days = (end - start).days + 1
    # Query for all dates in range
    rows = (
        db.query(CurrencyRatesORM)
        .filter(CurrencyRatesORM.date >= start, CurrencyRatesORM.date <= end)
        .count()
    )
    return rows == total_days
