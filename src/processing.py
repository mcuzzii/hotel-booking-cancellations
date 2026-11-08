import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import PercentFormatter
import matplotlib.dates as mdates
import seaborn as sns
from statsmodels.stats.proportion import proportion_confint
import re

def clean_text(s: str):
    return re.sub(
        r'\s+',
        ' ',
        s.strip().lower().replace('_', ' ')
    ).title()

def get_prop_summary(
    summary: pd.DataFrame,
    ci: float = 95
):
    summary['prop'] = summary['k'] / summary['n']
    summary[['lower', 'upper']] = summary.apply(
        lambda r: proportion_confint(
            r['k'],
            r['n'],
            method='wilson',
            alpha=1 - ci / 100
        ),
        axis=1,
        result_type='expand'
    )

    return summary

def get_summary(
    df: pd.DataFrame,
    feature: str,
    groups: str,
    target: str,
    no_prop: bool = False,
    ci: float = 95
):
    summary = (
        df
        .groupby([feature, groups], dropna=False)
        .agg(
            n=(target, 'size'),
            k=(target, 'sum')
        )
    )

    if no_prop:
        return summary

    summary = get_prop_summary(summary, ci)

    return summary

def plot_labels(
    ax: Axes,
    feature: str,
    target: str,
    groups: str,
    title: str | None = None,
    legend_title: str | None = None,
    feature_ax_title: str | None = None,
    target_ax_title: str | None = None,
    rolling_period: int | None = None,
    switch_axes: bool = False
):

    if not legend_title:
        legend_title = clean_text(groups)
    if not feature_ax_title:
        feature_ax_title = clean_text(feature)
    if not target_ax_title:
        target_ax_title = clean_text(target)
    if not title:
        title = f"Rates of '{clean_text(target)}' by '{clean_text(feature)}'"

    if rolling_period is not None and rolling_period > 0:
        legend_title = f"{legend_title} ({rolling_period}-point Rolling %)"

    ax.set_title(title)
    ax.get_legend().set_title(legend_title)
    ax.set_ylabel(feature_ax_title if switch_axes else target_ax_title)
    ax.set_xlabel(target_ax_title if switch_axes else feature_ax_title)

def grouped_barplot(
    df: pd.DataFrame,
    feature: str,
    target: str,
    groups: str,
    title: str | None = None,
    legend_title: str | None = None,
    feature_ax_title: str | None = None,
    target_ax_title: str | None = None,
    ci: float = 95
):

    summary = get_summary(df, feature, groups, target, ci=ci)

    plot_data = summary.reset_index()
    hue_order = plot_data[groups].drop_duplicates()

    ax = sns.barplot(
        data=summary,
        x='prop',
        y=feature,
        hue=groups,
        hue_order=hue_order,
        order=plot_data[feature].drop_duplicates(),
        errorbar=None
    )

    for container, hue in zip(ax.containers[:len(hue_order)], hue_order):
        for bar, segment in zip(
            container,
            plot_data.loc[plot_data[groups] == hue, feature].drop_duplicates()
        ):
            if (segment, hue) not in summary.index:
                continue

            row = summary.loc[(segment, hue)]

            ax.errorbar(
                x=bar.get_width(),
                y=bar.get_y() + bar.get_height() / 2,
                xerr=[[row['prop'] - row['lower']], [row['upper'] - row['prop']]],
                fmt='none',
                color='#444444',
                capsize=0
            )

    plot_labels(
        ax,
        feature,
        target,
        groups,
        title,
        legend_title,
        feature_ax_title,
        target_ax_title,
        switch_axes=True
    )
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
    sns.despine(ax=ax)

    plt.show()

def grouped_lineplot(
    df: pd.DataFrame,
    feature: str,
    target: str,
    groups: str,
    title: str | None = None,
    legend_title: str | None = None,
    feature_ax_title: str | None = None,
    target_ax_title: str | None = None,
    rolling_period: int | None = None,
    ci: float = 95,
    remove_year: bool = False,
    xlim: tuple | None = None
):
    summary = get_summary(
        df,
        feature,
        groups,
        target,
        no_prop=rolling_period is not None and rolling_period > 0,
        ci=ci
    ).reset_index().sort_values(by=feature)

    if rolling_period is not None and rolling_period > 0:
        summary[['n', 'k']] = summary.groupby(groups)[['n', 'k']].transform(lambda s: s.rolling(rolling_period).sum())
        summary = get_prop_summary(summary, ci)

    ax = sns.lineplot(
        summary,
        x=feature,
        y='prop',
        hue=groups
    )
    for line in ax.lines:
        group_summary = summary.loc[summary[groups] == line.get_label()]
        ax.fill_between(
            x=group_summary[feature],
            y1=group_summary['lower'],
            y2=group_summary['upper'],
            alpha=0.2,
            color=line.get_color()
        )

    plot_labels(
        ax,
        feature,
        target,
        groups,
        title,
        legend_title,
        feature_ax_title,
        target_ax_title,
        rolling_period=rolling_period
    )

    if xlim:
        ax.set_xlim(xlim[0], xlim[1])

    if pd.api.types.is_datetime64_any_dtype(df[feature]):
        ax.figure.autofmt_xdate()

    if remove_year:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    sns.despine(ax=ax)

    plt.show()