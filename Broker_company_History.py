import gzip
import json
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
FLOORSHEET_DIR = BASE_DIR / "Data" / "floorsheet"
OUTPUT_DIR = BASE_DIR / "Data" / "analysis"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_json_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)

    rows = data if isinstance(data, list) else data.get("rows", data.get("data", []))
    df = pd.DataFrame(rows)

    if "securityName" in df.columns:
        df = df.drop(columns=["securityName"])

    return df


def normalize(df):
    for col in [
        "stockSymbol",
        "buyerMemberId",
        "sellerMemberId",
        "contractQuantity",
        "contractRate",
        "contractAmount",
    ]:
        if col not in df.columns:
            df[col] = None

    df["buyerMemberId"] = pd.to_numeric(df["buyerMemberId"], errors="coerce").fillna(0).astype(int)
    df["sellerMemberId"] = pd.to_numeric(df["sellerMemberId"], errors="coerce").fillna(0).astype(int)
    df["contractQuantity"] = pd.to_numeric(df["contractQuantity"], errors="coerce").fillna(0)
    df["contractRate"] = pd.to_numeric(df["contractRate"], errors="coerce").fillna(0)
    df["contractAmount"] = pd.to_numeric(df["contractAmount"], errors="coerce").fillna(0)

    return df


def load_all():
    frames = []
    
    for file in sorted(FLOORSHEET_DIR.glob("*.json.gz")):
        # tqdm(range(1, len(sorted(FLOORSHEET_DIR.glob("*.json.gz")))), desc="Downloading Floorsheet")
        date = file.name.replace(".json.gz", "")
        print(f"Loading {file.name}")

        df = read_json_gz(file)
        df = normalize(df)
        df["date"] = date

        frames.append(df)

    if not frames:
        raise RuntimeError("No .json.gz floorsheet files found.")

    return pd.concat(frames, ignore_index=True)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved {path}")


def broker_daily_top_companies(df, top_n=5):
    """
    For each broker and each day:
    - top 5 companies bought
    - top 5 companies sold
    """

    output = {}

    brokers = sorted(
        set(df["buyerMemberId"].dropna().astype(int).tolist())
        | set(df["sellerMemberId"].dropna().astype(int).tolist())
    )

    for broker in brokers:
        if broker == 0:
            continue

        broker_result = []

        for date, day_df in df.groupby("date"):
            buy_df = day_df[day_df["buyerMemberId"] == broker]
            sell_df = day_df[day_df["sellerMemberId"] == broker]

            top_buy = (
                buy_df.groupby("stockSymbol")
                .agg(
                    trades=("stockSymbol", "count"),
                    quantity=("contractQuantity", "sum"),
                    amount=("contractAmount", "sum"),
                    avg_rate=("contractRate", "mean"),
                )
                .reset_index()
                .sort_values("amount", ascending=False)
                .head(top_n)
            )

            top_sell = (
                sell_df.groupby("stockSymbol")
                .agg(
                    trades=("stockSymbol", "count"),
                    quantity=("contractQuantity", "sum"),
                    amount=("contractAmount", "sum"),
                    avg_rate=("contractRate", "mean"),
                )
                .reset_index()
                .sort_values("amount", ascending=False)
                .head(top_n)
            )

            if top_buy.empty and top_sell.empty:
                continue

            broker_result.append({
                "date": date,
                "top_buy": top_buy.to_dict(orient="records"),
                "top_sell": top_sell.to_dict(orient="records"),
            })

        output[str(broker)] = broker_result

        save_json(
            OUTPUT_DIR / "broker_daily_top" / f"{broker}.json",
            broker_result
        )

    save_json(OUTPUT_DIR / "broker_daily_top.json", output)


def company_period_top_brokers(df, top_n=5):
    """
    For the whole available data period:
    For each company:
    - top 5 buyer brokers
    - top 5 seller brokers
    """

    output = {}

    for symbol, symbol_df in df.groupby("stockSymbol"):
        if pd.isna(symbol):
            continue

        top_buyers = (
            symbol_df.groupby("buyerMemberId")
            .agg(
                trades=("buyerMemberId", "count"),
                quantity=("contractQuantity", "sum"),
                amount=("contractAmount", "sum"),
                avg_rate=("contractRate", "mean"),
            )
            .reset_index()
            .rename(columns={"buyerMemberId": "broker"})
            .sort_values("amount", ascending=False)
            .head(top_n)
        )

        top_sellers = (
            symbol_df.groupby("sellerMemberId")
            .agg(
                trades=("sellerMemberId", "count"),
                quantity=("contractQuantity", "sum"),
                amount=("contractAmount", "sum"),
                avg_rate=("contractRate", "mean"),
            )
            .reset_index()
            .rename(columns={"sellerMemberId": "broker"})
            .sort_values("amount", ascending=False)
            .head(top_n)
        )

        result = {
            "symbol": symbol,
            "top_buyers": top_buyers.to_dict(orient="records"),
            "top_sellers": top_sellers.to_dict(orient="records"),
        }

        output[str(symbol)] = result

        safe_symbol = str(symbol).replace("/", "_")
        save_json(
            OUTPUT_DIR / "company_period_top" / f"{safe_symbol}.json",
            result
        )

    save_json(OUTPUT_DIR / "company_period_top.json", output)


def make_index(df):
    index = {
        "dates": sorted(df["date"].unique().tolist()),
        "companies": sorted(df["stockSymbol"].dropna().unique().tolist()),
        "brokers": sorted(
            list(
                set(df["buyerMemberId"].dropna().astype(int).tolist())
                | set(df["sellerMemberId"].dropna().astype(int).tolist())
            )
        ),
        "files": {
            "broker_daily_top": "Data/analysis/broker_daily_top/{BROKER_ID}.json",
            "company_period_top": "Data/analysis/company_period_top/{SYMBOL}.json",
        }
    }

    save_json(OUTPUT_DIR / "index.json", index)




def build_single_broker_daily_company(df, broker_id=58):
    buy = (
        df[df["buyerMemberId"] == broker_id]
        .groupby(["date", "stockSymbol"])
        .agg(
            buy_trades=("stockSymbol", "count"),
            buy_quantity=("contractQuantity", "sum"),
            buy_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"stockSymbol": "symbol"})
    )

    sell = (
        df[df["sellerMemberId"] == broker_id]
        .groupby(["date", "stockSymbol"])
        .agg(
            sell_trades=("stockSymbol", "count"),
            sell_quantity=("contractQuantity", "sum"),
            sell_amount=("contractAmount", "sum"),
        )
        .reset_index()
        .rename(columns={"stockSymbol": "symbol"})
    )

    merged = buy.merge(
        sell,
        on=["date", "symbol"],
        how="outer"
    ).fillna(0)

    merged["broker"] = broker_id

    merged["net_quantity"] = merged["buy_quantity"] - merged["sell_quantity"]
    merged["net_amount"] = merged["buy_amount"] - merged["sell_amount"]

    merged["total_quantity"] = merged["buy_quantity"] + merged["sell_quantity"]
    merged["total_amount"] = merged["buy_amount"] + merged["sell_amount"]

    # Average prices
    merged["buy_avg_price"] = merged.apply(
        lambda r: r["buy_amount"] / r["buy_quantity"]
        if r["buy_quantity"] > 0 else 0,
        axis=1
    )

    merged["sell_avg_price"] = merged.apply(
        lambda r: r["sell_amount"] / r["sell_quantity"]
        if r["sell_quantity"] > 0 else 0,
        axis=1
    )

    # Overall broker VWAP for that company/day
    merged["avg_price"] = merged.apply(
        lambda r: r["total_amount"] / r["total_quantity"]
        if r["total_quantity"] > 0 else 0,
        axis=1
    )

    merged = merged.sort_values(
        ["date", "total_amount"],
        ascending=[True, False]
    )

    return merged



def save_single_broker_daily_company(data, broker_id=58):
    out_dir = OUTPUT_DIR / "broker_daily_company"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / f"{broker_id}.json"

    records = data.to_dict(orient="records")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved {path}")








def main():
    df = load_all()

    broker_daily_top_companies(df, top_n=5)
    company_period_top_brokers(df, top_n=5)
    make_index(df)
    
    broker_58_daily = build_single_broker_daily_company(df, broker_id=58)
    save_single_broker_daily_company(broker_58_daily, broker_id=58)


    print("Analysis complete.")


if __name__ == "__main__":
    main()