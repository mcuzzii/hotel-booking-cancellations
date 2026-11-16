import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter, PercentFormatter
from matplotlib.patches import Patch
from matplotlib.artist import Artist
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import seaborn as sns
from statsmodels.stats.proportion import proportion_confint
import itertools
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

def get_unique_sorted_values(
    df: pd.DataFrame,
    var: str,
    fill_value: str | None = None
):
    
    out = df[var].sort_values().unique()

    if fill_value:
        return [fill_value if pd.isna(x) else x for x in out]

    return out

def order_values(
    vals: list,
    order: list
):
    
    order_in_vals = [x for x in order if x in vals]
    return order_in_vals + [x for x in vals if x not in order_in_vals]

def get_group_ticks_and_margin(
    centers: np.array,
    margin: float,
    num_ticks: int,
    tick_margin_factor: float = 0.9,
    flattened: bool = True
):
    
    ticks = np.linspace(
        centers + margin,
        centers - margin,
        2 * num_ticks,
        endpoint=False
    )[np.arange(num_ticks) * 2 + 1]

    tick_margin = tick_margin_factor * (ticks[0][0] - ticks[1][0]) / 2

    if flattened:
        ticks = ticks.T.flatten()

    return ticks, tick_margin

def get_renderer(
    fig: Figure
):
    fig.canvas.draw()
    return fig.canvas.get_renderer()

def get_bbox(
    ax: Axes,
    element: Artist,
    renderer: RendererBase
):
    return (
        ax
        .transData
        .inverted()
        .transform_bbox(element.get_window_extent(renderer=renderer))
    )

def min_max_scale(
    arr: np.array
):
    return (arr - arr.min()) / (arr.max() - arr.min())

def grouped_stacked_barplot(
    df: pd.DataFrame,
    groups_var: str,
    subgroups_var: str,
    stacks_var: str,
    hues_vars: list,
    stacks_ordering: list | None = None,
    hues_ordering: list | None = None,
    width_per_plot: float = 6,
    plot_height: float = 8,
    fill_value: str | None = None,
    margin_factor: float = 0.9,
    stack_label_font_size: float = 5,
    grouping_label_spacing: float = 0.02,
    max_legend_items: int = 5,
    legend_width_factor: float = 1
):

    num_hues_vars = len(hues_vars)

    fig, axes = plt.subplots(
        nrows=1,
        ncols=num_hues_vars,
        figsize=(width_per_plot * num_hues_vars, plot_height)
    )
    axes = np.atleast_1d(axes)

    for g, (ax, hues_var), in enumerate(zip(axes, hues_vars)):

        summary = (
            df
            .groupby([groups_var, subgroups_var, stacks_var], dropna=False)[hues_var]
            .value_counts(normalize=True, dropna=False)
            .rename('p')
            .reset_index()
        )

        group_values = get_unique_sorted_values(summary, groups_var, fill_value)
        subgroup_values = get_unique_sorted_values(summary, subgroups_var, fill_value)
        stack_values = get_unique_sorted_values(summary, stacks_var, fill_value)
        hue_values = get_unique_sorted_values(summary, hues_var, fill_value)

        summary = summary.fillna(fill_value)

        hues_var_mean_props = df[hues_var].fillna(fill_value).value_counts(normalize=True)

        if stacks_ordering:
            stack_values = order_values(stack_values, stacks_ordering)
        if hues_ordering[g]:
            hue_values = order_values(hue_values, hues_ordering[g])
        
        num_stacks = len(stack_values)
        
        cmap = plt.colormaps['viridis']
        color_mapping = {
            k: cmap(int(256 * v))
            for k, v in min_max_scale(
                hues_var_mean_props.reindex(hue_values).cumsum()
            ).to_dict().items()
        }

        y_indices = list(itertools.product(group_values, subgroup_values))

        group_ticks, group_margin = get_group_ticks_and_margin(
            np.array([0.5]),
            0.5,
            len(group_values),
            tick_margin_factor=margin_factor
        )
        subgroup_ticks, subgroup_margin = get_group_ticks_and_margin(
            group_ticks,
            group_margin,
            len(subgroup_values),
            tick_margin_factor=margin_factor
        )
        stack_ticks, stack_margin = get_group_ticks_and_margin(
            subgroup_ticks,
            subgroup_margin,
            num_stacks,
            tick_margin_factor=1,
            flattened=False
        )

        for i, stack_value in enumerate(stack_values):

            left = np.zeros(len(y_indices))

            for j, hue_value in enumerate(hue_values):

                values = (
                    summary.loc[
                        (summary[stacks_var] == stack_value)
                        & (summary[hues_var] == hue_value)
                    ]
                    .set_index([groups_var, subgroups_var])['p']
                    .reindex(y_indices, fill_value=0)
                )
                    
                ax.barh(
                    y=stack_ticks[i],
                    width=values,
                    height=2 * stack_margin,
                    left=left,
                    color=color_mapping[hue_value]
                )

                left += values

        if g == 0:
            ax.set_yticks(stack_ticks.T.flatten())
            ax.set_yticklabels(stack_values * len(y_indices), size=stack_label_font_size)
        else:
            ax.get_yaxis().set_visible(False)
        
        xlab = ax.set_xlabel('Composition')

        renderer = get_renderer(fig)
        xlabel_y = get_bbox(ax, xlab, renderer).y0

        if g == 0:

            ylabels_x = min(
                get_bbox(ax, label, renderer).x0
                for label in ax.get_yticklabels()
            )

            for i, group in enumerate(group_values):

                for j, canceled_status in enumerate(subgroup_values):

                    text = ax.text(
                        x=ylabels_x - grouping_label_spacing,
                        y=subgroup_ticks[2 * i + j],
                        s=canceled_status,
                        rotation=90,
                        verticalalignment='center',
                        horizontalalignment='right'
                    )

                renderer = get_renderer(fig)
                subgroup_labels_x = get_bbox(ax, text, renderer).x0

                ax.text(
                    x=subgroup_labels_x - grouping_label_spacing,
                    y=group_ticks[i],
                    s=group,
                    rotation=90,
                    verticalalignment='center',
                    horizontalalignment='right'
                )

        handles = [
            Patch(facecolor=color, label=label)
            for label, color in color_mapping.items()
            if label in (
                hues_var_mean_props
                .sort_values(ascending=False)
                .head(max_legend_items)
                .index
            )
        ]

        if len(hue_values) > max_legend_items:
            handles.append(Patch(facecolor="none", edgecolor="none", label="..."))

        ncols = len(handles)
        ax_width = ax.get_window_extent(renderer).width

        while ncols >= 1:

            leg = ax.legend(
                handles=handles,
                loc='upper left',
                bbox_to_anchor=(0, xlabel_y),
                ncols=ncols,
                frameon=True
            )

            renderer = get_renderer(fig)
            legend_width = leg.get_window_extent(renderer).width

            if legend_width <= ax_width * legend_width_factor:
                break

            ncols -= 1

        ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
        ax.set_title(clean_text(hues_var))

        sns.despine(ax=ax)

    fig.suptitle(
        'Composition of Selected Features '
        f'Segmented by {clean_text(stacks_var)}'
    )
    fig.tight_layout()
    fig.show()