from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, PercentFormatter

from src.config import FIGURES_DIR

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "blues", ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT_SECONDARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 14,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "font.size": 10,
            "legend.frameon": False,
        }
    )


def currency_formatter(decimals: int = 0) -> FuncFormatter:
    def format_value(value, _position=None):
        magnitude = abs(value)
        if magnitude >= 1_000_000:
            return f"£{value / 1_000_000:.{max(decimals, 1)}f}M"
        if magnitude >= 10_000:
            return f"£{value / 1_000:.0f}K"
        if magnitude >= 1_000:
            return f"£{value / 1_000:.{decimals}f}K"
        return f"£{value:,.0f}"

    return FuncFormatter(format_value)


THOUSANDS = FuncFormatter(lambda value, _position=None: f"{value:,.0f}")


def format_currency(value: float) -> str:
    return currency_formatter(1)(value)


def _save(figure: plt.Figure, name: str, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path


def _subtitle(axis: plt.Axes, text: str) -> None:
    axis.text(0, 1.02, text, transform=axis.transAxes, color=TEXT_SECONDARY, fontsize=10, va="bottom")


def _horizontal_bars(axis: plt.Axes, labels, values, value_labels, color=SERIES[0]) -> None:
    positions = np.arange(len(labels))
    axis.barh(positions, values, color=color, height=0.68)
    axis.set_yticks(positions, labels)
    axis.invert_yaxis()
    axis.grid(axis="y", visible=False)
    axis.tick_params(axis="y", length=0)
    limit = max(values) if len(values) else 1
    for position, value, text in zip(positions, values, value_labels):
        axis.text(value + limit * 0.01, position, text, va="center", color=TEXT_PRIMARY, fontsize=9)
    axis.set_xlim(0, limit * 1.18)


def plot_monthly_revenue(
    monthly: pd.DataFrame, partial_months: pd.Series, subtitle: str, output_dir: Path = FIGURES_DIR
) -> Path:
    figure, axis = plt.subplots(figsize=(11, 5))
    is_partial = monthly["month"].isin(partial_months)
    complete = monthly[~is_partial]
    axis.plot(complete["month"], complete["revenue"], color=SERIES[0], linewidth=2, marker="o", markersize=6)
    if is_partial.any():
        bridge = monthly[monthly.index >= monthly[is_partial].index.min() - 1]
        axis.plot(bridge["month"], bridge["revenue"], color=SERIES[0], linewidth=2, linestyle="--")
        partial = monthly[is_partial]
        axis.scatter(
            partial["month"], partial["revenue"], s=48, facecolor=SURFACE, edgecolor=SERIES[0], linewidth=2, zorder=3
        )
        for _, row in partial.iterrows():
            axis.annotate(
                "partial month",
                (row["month"], row["revenue"]),
                xytext=(0, -18),
                textcoords="offset points",
                ha="center",
                color=TEXT_SECONDARY,
                fontsize=9,
            )
    peak = complete.loc[complete["revenue"].idxmax()]
    axis.annotate(
        format_currency(peak["revenue"]),
        (peak["month"], peak["revenue"]),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        color=TEXT_PRIMARY,
        fontsize=9,
        fontweight="bold",
    )
    axis.yaxis.set_major_formatter(currency_formatter())
    axis.set_ylim(0, monthly["revenue"].max() * 1.15)
    axis.set_xticks(monthly["month"], monthly["month"].dt.strftime("%b\n%Y"))
    axis.set_ylabel("Revenue (GBP)")
    axis.set_title("Monthly revenue", pad=26)
    _subtitle(axis, subtitle)
    return _save(figure, "monthly_revenue_trend.png", output_dir)


def plot_new_vs_returning_customers(activity: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    figure, axis = plt.subplots(figsize=(11, 5))
    labels = activity["month"].dt.strftime("%b\n%Y")
    axis.bar(
        labels,
        activity["returning_customers"],
        color=SERIES[0],
        width=0.7,
        label="Returning customers",
        edgecolor=SURFACE,
        linewidth=1,
    )
    axis.bar(
        labels,
        activity["new_customers"],
        bottom=activity["returning_customers"],
        color=SERIES[1],
        width=0.7,
        label="New customers",
        edgecolor=SURFACE,
        linewidth=1,
    )
    axis.grid(axis="x", visible=False)
    axis.yaxis.set_major_formatter(THOUSANDS)
    axis.set_ylabel("Active customers")
    axis.legend(loc="upper left", ncol=2)
    axis.set_ylim(0, activity["active_customers"].max() * 1.15)
    axis.set_title("Monthly active customers: new vs returning", pad=26)
    _subtitle(
        axis, "A customer is new in the month of their first order and returning in any later month with an order"
    )
    return _save(figure, "monthly_new_vs_returning_customers.png", output_dir)


def plot_segment_distribution(summary: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    ordered = summary.sort_values("customers", ascending=False)
    figure, axis = plt.subplots(figsize=(10, 6))
    texts = [f"{count:,}  ({share:.1%})" for count, share in zip(ordered["customers"], ordered["customer_share"])]
    _horizontal_bars(axis, ordered["segment"], ordered["customers"], texts)
    axis.xaxis.set_major_formatter(THOUSANDS)
    axis.set_xlabel("Customers")
    axis.set_title("Customers by RFM segment", pad=26)
    _subtitle(axis, f"{int(summary['customers'].sum()):,} customers scored at the snapshot date")
    return _save(figure, "customer_segment_distribution.png", output_dir)


def plot_revenue_by_segment(summary: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    ordered = summary.sort_values("revenue", ascending=False)
    figure, axis = plt.subplots(figsize=(10, 6))
    texts = [
        f"{format_currency(value)}  ({share:.1%})" for value, share in zip(ordered["revenue"], ordered["revenue_share"])
    ]
    _horizontal_bars(axis, ordered["segment"], ordered["revenue"], texts)
    axis.xaxis.set_major_formatter(currency_formatter())
    axis.set_xlabel("Revenue (GBP)")
    axis.set_title("Revenue by RFM segment", pad=26)
    _subtitle(axis, "Total revenue over the full period, grouped by each customer's segment at the snapshot date")
    return _save(figure, "revenue_by_segment.png", output_dir)


def plot_repeat_vs_one_time(breakdown: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    colors = {"One-time": SERIES[1], "Returning": SERIES[0]}
    panels = (
        ("customer_share", "customers", "Share of customers", lambda value: f"{int(value):,} customers"),
        ("revenue_share", "revenue", "Share of revenue", format_currency),
    )
    for axis, (share_column, value_column, title, formatter) in zip(axes, panels):
        bars = axis.bar(
            breakdown["customer_type"],
            breakdown[share_column],
            color=[colors[name] for name in breakdown["customer_type"]],
            width=0.6,
        )
        for bar, share, value in zip(bars, breakdown[share_column], breakdown[value_column]):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                share + 0.02,
                f"{share:.1%}\n{formatter(value)}",
                ha="center",
                va="bottom",
                color=TEXT_PRIMARY,
                fontsize=9,
            )
        axis.set_title(title, fontsize=12)
        axis.yaxis.set_major_formatter(PercentFormatter(1.0))
        axis.set_ylim(0, 1.18)
        axis.grid(axis="x", visible=False)
    figure.suptitle(
        "Repeat vs one-time customers", x=0.07, ha="left", fontsize=14, fontweight="bold", color=TEXT_PRIMARY
    )
    figure.text(
        0.07, 0.905, "Returning customers placed two or more distinct orders", color=TEXT_SECONDARY, fontsize=10
    )
    figure.subplots_adjust(top=0.78)
    return _save(figure, "repeat_vs_one_time_customers.png", output_dir)


def plot_rfm_segment_comparison(rfm: pd.DataFrame, segment_order: list[str], output_dir: Path = FIGURES_DIR) -> Path:
    means = rfm.groupby("segment")[["r_score", "f_score", "m_score"]].mean()
    means = means.reindex([name for name in segment_order if name in means.index])
    raw = rfm.groupby("segment")[["recency_days", "frequency", "monetary"]].median().reindex(means.index)
    annotations = np.empty(means.shape, dtype=object)
    for row, segment in enumerate(means.index):
        annotations[row, 0] = f"{means.iloc[row, 0]:.1f}\n{raw.loc[segment, 'recency_days']:.0f} days"
        orders = raw.loc[segment, "frequency"]
        annotations[row, 1] = f"{means.iloc[row, 1]:.1f}\n{orders:.0f} {'order' if orders == 1 else 'orders'}"
        annotations[row, 2] = f"{means.iloc[row, 2]:.1f}\n{format_currency(raw.loc[segment, 'monetary'])}"
    figure, axis = plt.subplots(figsize=(9, 8))
    sns.heatmap(
        means,
        annot=annotations,
        fmt="",
        cmap=SEQUENTIAL,
        vmin=1,
        vmax=5,
        linewidths=2,
        linecolor=SURFACE,
        cbar_kws={"label": "Mean score (1 = lowest, 5 = best)"},
        ax=axis,
        annot_kws={"fontsize": 9},
    )
    axis.grid(False)
    axis.set_xticklabels(["Recency score", "Frequency score", "Monetary score"], rotation=0)
    axis.set_ylabel("")
    axis.set_xlabel("")
    axis.tick_params(length=0)
    axis.set_title("RFM profile by segment", pad=26)
    _subtitle(axis, "Cell value: mean score; second line: segment median of the underlying metric")
    return _save(figure, "rfm_segment_comparison.png", output_dir)


def plot_top_products(products: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    figure, axis = plt.subplots(figsize=(10, 6))
    labels = [name.title() if len(name) <= 36 else name[:34].title() + "..." for name in products["product_name"]]
    texts = [format_currency(value) for value in products["revenue"]]
    _horizontal_bars(axis, labels, products["revenue"], texts)
    axis.xaxis.set_major_formatter(currency_formatter())
    axis.set_xlabel("Revenue (GBP)")
    axis.set_title(f"Top {len(products)} products by revenue", pad=26)
    _subtitle(axis, "Net of matched cancellations")
    return _save(figure, "top_products_by_revenue.png", output_dir)


def plot_country_revenue(countries: pd.DataFrame, top_n: int = 10, output_dir: Path = FIGURES_DIR) -> Path:
    top = countries.head(top_n)
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1.3]})
    share_texts = [f"{share:.1%}" for share in top["revenue_share"]]
    _horizontal_bars(axes[0], top["country"], top["revenue_share"], share_texts)
    axes[0].xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axes[0].set_xlabel("Share of total revenue")
    axes[0].set_title("Revenue share", fontsize=12)
    international = top.iloc[1:]
    texts = [format_currency(value) for value in international["revenue"]]
    _horizontal_bars(axes[1], international["country"], international["revenue"], texts)
    axes[1].xaxis.set_major_formatter(currency_formatter())
    axes[1].set_xlabel("Revenue (GBP)")
    axes[1].set_title(f"Revenue outside {top.iloc[0]['country']}", fontsize=12)
    figure.suptitle(
        f"Top {top_n} countries by revenue", x=0.06, ha="left", fontsize=14, fontweight="bold", color=TEXT_PRIMARY
    )
    figure.subplots_adjust(top=0.84, wspace=0.45)
    return _save(figure, "country_revenue.png", output_dir)


def plot_revenue_concentration(curve: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> Path:
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(curve["customer_share"], curve["cumulative_revenue_share"], color=SERIES[0], linewidth=2)
    axis.plot([0, 1], [0, 1], color=TEXT_SECONDARY, linewidth=1, linestyle=":")
    for share in (0.1, 0.2):
        position = int(np.ceil(len(curve) * share)) - 1
        value = curve["cumulative_revenue_share"].iloc[position]
        axis.scatter([share], [value], s=48, color=SERIES[0], edgecolor=SURFACE, linewidth=2, zorder=3)
        axis.annotate(
            f"Top {share:.0%} of customers: {value:.1%} of revenue",
            (share, value),
            xytext=(12, -14),
            textcoords="offset points",
            color=TEXT_PRIMARY,
            fontsize=9,
        )
    axis.text(0.62, 0.55, "equal distribution", color=TEXT_SECONDARY, fontsize=9, rotation=36)
    axis.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1.02)
    axis.set_xlabel("Customers ranked by revenue (cumulative share)")
    axis.set_ylabel("Cumulative share of revenue")
    axis.set_title("Revenue concentration across customers", pad=26)
    _subtitle(axis, "Cumulative revenue curve, highest-revenue customers first")
    return _save(figure, "revenue_concentration.png", output_dir)


def plot_cohort_retention(retention: pd.DataFrame, subtitle: str, output_dir: Path = FIGURES_DIR) -> Path:
    table = retention.drop(columns=0).dropna(how="all")
    table.index = pd.to_datetime(table.index).strftime("%b %Y")
    figure, axis = plt.subplots(figsize=(12, 7))
    sns.heatmap(
        table,
        annot=True,
        fmt=".0%",
        cmap=SEQUENTIAL,
        vmin=0,
        vmax=0.5,
        linewidths=1.5,
        linecolor=SURFACE,
        cbar_kws={"label": "Share of cohort placing an order", "format": PercentFormatter(1.0, decimals=0)},
        annot_kws={"fontsize": 8},
        ax=axis,
    )
    axis.grid(False)
    axis.set_xlabel("Months since first purchase")
    axis.set_ylabel("Acquisition cohort (month of first purchase)")
    axis.tick_params(length=0)
    axis.set_title("Monthly cohort retention", pad=26)
    _subtitle(axis, subtitle)
    return _save(figure, "cohort_retention_heatmap.png", output_dir)
