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
    # New optional columns (nullable=True to ease existing deployments/migrations)
    JPY = Column(Float, nullable=False)  # 1 CNY = X JPY
    KRW = Column(Float, nullable=False)  # 1 CNY = X KRW
    VND = Column(Float, nullable=False)  # 1 CNY = X VND
    MYR = Column(Float, nullable=False)  # 1 CNY = X MYR
    HKD = Column(Float, nullable=False)  # 1 CNY = X HKD


def create_currency_rates_table():
    Base.metadata.create_all(bind=engine)


def get_currency_rates(db, date: datetime):
    return (
        db.query(CurrencyRatesORM).filter(CurrencyRatesORM.date == date.date()).first()
    )


def set_currency_rates(
    db,
    date: datetime,
    euro_rate: float,
    usd_rate: float,
    jpy_rate: float,
    krw_rate: float,
    myr_rate: float,
    hkd_rate: float,
):
    obj = (
        db.query(CurrencyRatesORM).filter(CurrencyRatesORM.date == date.date()).first()
    )
    if obj:
        if euro_rate is not None:
            obj.EURO = euro_rate
        if usd_rate is not None:
            obj.USD = usd_rate
        if jpy_rate is not None:
            obj.JPY = jpy_rate
        if krw_rate is not None:
            obj.KRW = krw_rate
        if myr_rate is not None:
            obj.MYR = myr_rate
        if hkd_rate is not None:
            obj.HKD = hkd_rate
        obj.VND = 3746.2  # Keep VND fixed as per original code
        db.commit()
        db.refresh(obj)
        return obj

    # create with whatever values provided (others default to None)
    obj = CurrencyRatesORM(
        date=date.date(),
        EURO=euro_rate if euro_rate is not None else None,
        USD=usd_rate if usd_rate is not None else None,
        JPY=jpy_rate,
        KRW=krw_rate,
        VND=3746.2,
        MYR=myr_rate,
        HKD=hkd_rate,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_rates_from_api(db, api_result: dict):
    rates = api_result.get("rates", {})
    start_date = datetime.strptime(api_result["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(api_result["end_date"], "%Y-%m-%d").date()
    current_date = start_date
    last_euro = last_usd = last_jpy = last_krw = last_myr = last_hkd = None

    # Prepare a sorted list of available dates
    rates_by_date = {
        datetime.strptime(d, "%Y-%m-%d").date(): v for d, v in rates.items()
    }

    while current_date <= end_date:
        # Find rate for current_date or fallback to last known
        if current_date in rates_by_date:
            r = rates_by_date[current_date]
            euro = r.get("EUR")
            usd = r.get("USD")
            jpy = r.get("JPY")
            krw = r.get("KRW")
            myr = r.get("MYR")
            hkd = r.get("HKD")
            if euro is not None:
                last_euro = euro
            if usd is not None:
                last_usd = usd
            if jpy is not None:
                last_jpy = jpy
            if krw is not None:
                last_krw = krw
            if myr is not None:
                last_myr = myr
            if hkd is not None:
                last_hkd = hkd
        else:
            euro = last_euro
            usd = last_usd
            jpy = last_jpy
            krw = last_krw
            # vnd = last_vnd
            myr = last_myr
            hkd = last_hkd
        # Persist if we have at least one known rate
        if (
            euro is not None
            or usd is not None
            or jpy is not None
            or krw is not None
            or myr is not None
            or hkd is not None
        ):
            # Convert current_date (date) to datetime for set_currency_rates
            set_currency_rates(
                db,
                datetime.combine(current_date, datetime.min.time()),
                euro,
                usd,
                jpy,
                krw,
                myr,
                hkd,
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
