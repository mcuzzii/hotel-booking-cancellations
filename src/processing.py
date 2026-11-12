import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter, PercentFormatter
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
    categories: list | None = None,
    other: str | None = None,
    ci: float = 95
):

    if categories:
        categories_mask = (
            df[feature].isin(categories)
            | (
                df[feature].isna()
                if 'Missing' in categories
                else False
            )
        )

    summary = (
        (
            (
                df.assign(**{feature: df[feature].where(categories_mask, other)})
                if other
                else df.loc[categories_mask]
            )
            if categories
            else df
        )
        .groupby([feature, groups], dropna=False)
        .agg(
            n=(target, 'size'),
            k=(target, 'sum')
        )
        .assign(n_total=lambda d: d.groupby(level=feature)['n'].sum())
    )

    if no_prop:
        return summary

    summary = get_prop_summary(summary, ci)
    summary = summary.sort_values(by='n_total', ascending=False)

    if other:
        other_mask = summary.index.get_level_values(feature) == other
        summary = pd.concat([summary.loc[~other_mask], summary.loc[other_mask]])

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
    rolling_interval_width: int | None = None,
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

    if rolling_interval_width is not None and rolling_interval_width > 0:
        legend_title = f"{legend_title} ({rolling_interval_width}-point Rolling %)"

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
    categories: list | None = None,
    other: str | None = None,
    ci: float = 95
):

    summary = get_summary(
        df,
        feature,
        groups,
        target,
        categories=categories,
        other=other,
        ci=ci
    )

    summary.index = pd.MultiIndex.from_arrays(
        [
            summary.index
            .get_level_values(i)
            .astype(str)
            .to_series()
            .fillna('Missing')
            .to_numpy()
            for i in range(summary.index.nlevels)
        ],
        names=summary.index.names
    )

    plot_data = summary.reset_index()
    hue_order = plot_data[groups].drop_duplicates()

    ax = sns.barplot(
        data=plot_data,
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
                xerr=[
                    [np.clip(row['prop'] - row['lower'], 0, 1)],
                    [np.clip(row['upper'] - row['prop'], 0, 1)]
                ],
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

def get_rolling_sums(
    summary: pd.DataFrame,
    feature: str,
    rolling_interval_width: int,
    datetime_unit: str,
    ci: float
):

    n_cumsum = np.cumsum(summary['n'].to_numpy())
    k_cumsum = np.cumsum(summary['k'].to_numpy())

    idx = (
        getattr((summary[feature] - summary[feature].min()).dt, datetime_unit)
        if str(summary[feature].dtype).startswith('datetime64')
        else summary[feature]
    )

    lb_idx = np.searchsorted(idx, idx - rolling_interval_width, 'right') - 1
    lb_idx_clipped = np.clip(lb_idx, 0, None)
    lb_mask = lb_idx >= 0

    summary['n'] = n_cumsum - np.where(lb_mask, n_cumsum[lb_idx_clipped], 0)
    summary['k'] = k_cumsum - np.where(lb_mask, k_cumsum[lb_idx_clipped], 0)

    summary = get_prop_summary(summary, ci)

    return summary 

def grouped_lineplot(
    df: pd.DataFrame,
    feature: str,
    target: str,
    groups: str,
    title: str | None = None,
    legend_title: str | None = None,
    feature_ax_title: str | None = None,
    target_ax_title: str | None = None,
    rolling_interval_width: int | None = None,
    datetime_unit: str | None = None,
    ci: float = 95,
    remove_year: bool = False,
    custom_labels: dict | None = None,
    xlim: tuple | None = None
):
    summary = get_summary(
        df,
        feature,
        groups,
        target,
        no_prop=rolling_interval_width is not None and rolling_interval_width > 0,
        ci=ci
    ).reset_index().sort_values(by=feature, ignore_index=True)

    if rolling_interval_width is not None and rolling_interval_width > 0:

        summary = summary.groupby(groups).apply(
            get_rolling_sums,
            feature=feature,
            rolling_interval_width=rolling_interval_width,
            datetime_unit=datetime_unit,
            ci=ci
        ).reset_index()

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
        rolling_interval_width=rolling_interval_width
    )

    if xlim:
        ax.set_xlim(xlim[0], xlim[1])

    if pd.api.types.is_datetime64_any_dtype(df[feature]):
        ax.figure.autofmt_xdate()

    if remove_year:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

    if custom_labels:
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda x, _: custom_labels.get(x, str(x)))
        )
    
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    sns.despine(ax=ax)

    plt.show()