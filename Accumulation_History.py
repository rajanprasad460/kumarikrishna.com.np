import gzip
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
FLOORSHEET_DIR = BASE_DIR / "Data" / "floorsheet"
OUTPUT_DIR = BASE_DIR / "Data" / "analysis"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_json_gz(file_path: Path) -> pd.DataFrame:
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        data = json.load(f)

    rows = data if isinstance(data, list) else data.get("rows", data.get("data", []))

    df = pd.DataFrame(rows)

    if "securityName" in df.columns:
        df = df.drop(columns=["securityName"])

    return df


def save_json(file_name, data):
    path = OUTPUT_DIR / file_name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Saved {path}")


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "stockSymbol",
        "buyerMemberId",
        "sellerMemberId",
        "contractQuantity",
        "contractRate",
        "contractAmount",
    ]

    for col in required:
        if col not in df.columns:
            df[col] = None

    df["buyerMemberId"] = pd.to_numeric(df["buyerMemberId"], errors="coerce").fillna(0).astype(int)
    df["sellerMemberId"] = pd.to_numeric(df["sellerMemberId"], errors="coerce").fillna(0).astype(int)
    df["contractQuantity"] = pd.to_numeric(df["contractQuantity"], errors="coerce").fillna(0)
    df["contractRate"] = pd.to_numeric(df["contractRate"], errors="coerce").fillna(0)
    df["contractAmount"] = pd.to_numeric(df["contractAmount"], errors="coerce").fillna(0)

    return df


def load_all_floorsheets():
    records = []

    files = sorted(FLOORSHEET_DIR.glob("*.json.gz"))

    for file in files:
        date = file.name.replace(".json.gz", "")
        print(f"Loading {file.name}")

        df = read_json_gz(file)
        df = normalize_df(df)
        df["date"] = date

        records.append(df)

    if not records:
        raise RuntimeError("No .json.gz floorsheet files found.")

    return pd.concat(records, ignore_index=True)


def build_company_daily_summary(df):
    grouped = (
        df.groupby(["date", "stockSymbol"])
        .agg(
            trades=("stockSymbol", "count"),
            quantity=("contractQuantity", "sum"),
            turnover=("contractAmount", "sum"),
            high_rate=("contractRate", "max"),
            low_rate=("contractRate", "min"),
        )
        .reset_index()
    )

    grouped["vwap"] = grouped["turnover"] / grouped["quantity"]
    grouped["vwap"] = grouped["vwap"].fillna(0)

    return grouped.sort_values(["date", "turnover"], ascending=[True, False])


def build_broker_daily_summary(df):
    buyer = (
        df.groupby(["date", "buyerMemberId"])
        .agg(
            buy_trades=("buyerMemberId", "count"),
            buy_quantity=("contractQuantity", "sum"),
            buy_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"buyerMemberId": "broker"})
    )

    seller = (
        df.groupby(["date", "sellerMemberId"])
        .agg(
            sell_trades=("sellerMemberId", "count"),
            sell_quantity=("contractQuantity", "sum"),
            sell_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"sellerMemberId": "broker"})
    )

    merged = buyer.merge(seller, on=["date", "broker"], how="outer").fillna(0)

    merged["net_amount"] = merged["buy_amount"] - merged["sell_amount"]
    merged["net_quantity"] = merged["buy_quantity"] - merged["sell_quantity"]
    merged["turnover"] = merged["buy_amount"] + merged["sell_amount"]

    return merged.sort_values(["date", "turnover"], ascending=[True, False])


def build_company_broker_daily_flow(df):
    buy = (
        df.groupby(["date", "stockSymbol", "buyerMemberId"])
        .agg(
            buy_quantity=("contractQuantity", "sum"),
            buy_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"buyerMemberId": "broker"})
    )

    sell = (
        df.groupby(["date", "stockSymbol", "sellerMemberId"])
        .agg(
            sell_quantity=("contractQuantity", "sum"),
            sell_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"sellerMemberId": "broker"})
    )

    merged = buy.merge(
        sell,
        on=["date", "stockSymbol", "broker"],
        how="outer"
    ).fillna(0)

    total_by_company = (
        df.groupby(["date", "stockSymbol"])
        .agg(
            total_quantity=("contractQuantity", "sum"),
            total_amount=("contractAmount", "sum"),
            min_price=("contractRate", "min"),
            max_price=("contractRate", "max"),
        )
        .reset_index()
    )

    merged = merged.merge(total_by_company, on=["date", "stockSymbol"], how="left")

    merged["net_amount"] = merged["buy_amount"] - merged["sell_amount"]
    merged["net_quantity"] = merged["buy_quantity"] - merged["sell_quantity"]
    merged["broker_turnover"] = merged["buy_amount"] + merged["sell_amount"]

    merged["pct_of_company_turnover"] = (
        merged["broker_turnover"] / merged["total_amount"] * 100
    ).fillna(0)

    return merged.sort_values(
        ["date", "stockSymbol", "broker_turnover"],
        ascending=[True, True, False]
    )


def add_rolling_signals(flow_df, window=3):
    df = flow_df.copy()
    df = df.sort_values(["stockSymbol", "broker", "date"])

    df["net_amount_roll_3"] = (
        df.groupby(["stockSymbol", "broker"])["net_amount"]
        .rolling(window)
        .sum()
        .reset_index(level=[0, 1], drop=True)
    ).fillna(0)

    df["net_quantity_roll_3"] = (
        df.groupby(["stockSymbol", "broker"])["net_quantity"]
        .rolling(window)
        .sum()
        .reset_index(level=[0, 1], drop=True)
    ).fillna(0)

    def classify(x):
        if x > 0:
            return "ACCUMULATION"
        if x < 0:
            return "DISTRIBUTION"
        return "NEUTRAL"

    df["amount_signal"] = df["net_amount_roll_3"].apply(classify)
    df["quantity_signal"] = df["net_quantity_roll_3"].apply(classify)

    return df


def build_top_trades(df, top_n=100):
    cols = [
        "date",
        "contractId",
        "stockSymbol",
        "contractQuantity",
        "contractRate",
        "contractAmount",
        "buyerMemberId",
        "sellerMemberId",
    ]

    available_cols = [c for c in cols if c in df.columns]

    return (
        df.sort_values("contractAmount", ascending=False)
        .head(top_n)[available_cols]
    )


def split_by_company(flow_df):
    company_dir = OUTPUT_DIR / "company"
    company_dir.mkdir(exist_ok=True)

    for symbol, sub in flow_df.groupby("stockSymbol"):
        safe_symbol = str(symbol).replace("/", "_")
        records = sub.to_dict(orient="records")

        with open(company_dir / f"{safe_symbol}.json", "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, separators=(",", ":"))


def split_by_broker(flow_df):
    broker_dir = OUTPUT_DIR / "broker"
    broker_dir.mkdir(exist_ok=True)

    for broker, sub in flow_df.groupby("broker"):
        records = sub.to_dict(orient="records")

        with open(broker_dir / f"{int(broker)}.json", "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, separators=(",", ":"))


def main():
    df = load_all_floorsheets()

    company_daily = build_company_daily_summary(df)
    broker_daily = build_broker_daily_summary(df)
    company_broker_flow = build_company_broker_daily_flow(df)
    company_broker_flow = add_rolling_signals(company_broker_flow, window=3)
    top_trades = build_top_trades(df, top_n=100)

    save_json("company_daily_summary.json", company_daily.to_dict(orient="records"))
    save_json("broker_daily_summary.json", broker_daily.to_dict(orient="records"))
    save_json("company_broker_flow.json", company_broker_flow.to_dict(orient="records"))
    save_json("top_trades.json", top_trades.to_dict(orient="records"))

    split_by_company(company_broker_flow)
    split_by_broker(company_broker_flow)

    index = {
        "floorsheet_days": sorted(df["date"].unique().tolist()),
        "companies": sorted(df["stockSymbol"].dropna().unique().tolist()),
        "brokers": sorted([int(x) for x in pd.unique(
            pd.concat([df["buyerMemberId"], df["sellerMemberId"]])
        ) if int(x) != 0]),
        "files": {
            "company_daily_summary": "Data/analysis/company_daily_summary.json",
            "broker_daily_summary": "Data/analysis/broker_daily_summary.json",
            "company_broker_flow": "Data/analysis/company_broker_flow.json",
            "top_trades": "Data/analysis/top_trades.json",
            "company_folder": "Data/analysis/company/{SYMBOL}.json",
            "broker_folder": "Data/analysis/broker/{BROKER_ID}.json"
        }
    }

    save_json("index.json", index)

    print("Analysis complete.")


if __name__ == "__main__":
    main()