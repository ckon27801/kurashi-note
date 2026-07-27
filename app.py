import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

api_key = st.secrets["GEMINI_API_KEY"]

client = genai.Client(
    api_key=api_key
)

# ==================================================
# ページ設定
# ==================================================

st.set_page_config(
    page_title="くらしノート",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==================================================
# 基本設定
# ==================================================

DATA_FOLDER = Path("data")
EXPENSES_FILE = DATA_FOLDER / "expenses.csv"
SETTINGS_FILE = DATA_FOLDER / "settings.csv"

CATEGORIES = [
    "食費",
    "交通費",
    "日用品",
    "住居・光熱費",
    "美容・服",
    "趣味",
    "推し活",
    "旅行",
    "勉強",
    "サブスク",
    "交際費",
    "その他",
]

NECESSITIES = [
    "生活に必要",
    "できれば必要",
    "なくても困らない",
]

PRIORITIES = [
    "食事",
    "推し活",
    "旅行",
    "美容",
    "趣味",
    "勉強",
    "家族",
    "貯金",
    "その他",
]

CATEGORY_ICONS = {
    "食費": "🍙",
    "交通費": "🚃",
    "日用品": "🧻",
    "住居・光熱費": "🏠",
    "美容・服": "🧴",
    "趣味": "🎮",
    "推し活": "💚",
    "旅行": "✈️",
    "勉強": "📚",
    "サブスク": "📱",
    "交際費": "☕",
    "その他": "🫧",
}

PRIORITY_CATEGORY_MAP = {
    "食事": "食費",
    "推し活": "推し活",
    "旅行": "旅行",
    "美容": "美容・服",
    "趣味": "趣味",
    "勉強": "勉強",
}


# ==================================================
# 色・見た目
# HTMLの表示には使わず、CSS設定だけに使用
# ==================================================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(
                circle at 10% 5%,
                rgba(199, 241, 232, 0.65),
                transparent 25%
            ),
            radial-gradient(
                circle at 90% 10%,
                rgba(218, 241, 246, 0.75),
                transparent 25%
            ),
            linear-gradient(
                180deg,
                #f8fffd 0%,
                #fffef8 100%
            );
    }

    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: #365751;
    }

    p, label {
        color: #526e69;
    }

    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(102, 200, 181, 0.28);
        border-radius: 22px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(61, 120, 109, 0.08);
    }

    div[data-testid="stMetricLabel"] {
        color: #78918c;
    }

    div[data-testid="stMetricValue"] {
        color: #365751;
    }

    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        width: 100%;
        border: none;
        border-radius: 999px;
        padding: 0.65rem 1.2rem;
        background: linear-gradient(
            135deg,
            #65c8b5,
            #83d6c7
        );
        color: white;
        font-weight: bold;
        box-shadow: 0 7px 18px rgba(54, 159, 140, 0.18);
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(
            135deg,
            #3ea991,
            #65c8b5
        );
        color: white;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        border-radius: 15px;
        background-color: rgba(255, 255, 255, 0.94);
    }

    div[data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(102, 200, 181, 0.25);
        border-radius: 24px;
        padding: 22px;
    }

    div[data-testid="stAlert"] {
        border-radius: 18px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
    }

    div[data-testid="stTabs"] button {
        font-weight: bold;
    }

    hr {
        border-color: rgba(102, 200, 181, 0.25);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# CSVファイルの準備
# ==================================================

def create_files():
    DATA_FOLDER.mkdir(exist_ok=True)

    if not EXPENSES_FILE.exists():
        empty_expenses = pd.DataFrame(
            columns=[
                "id",
                "date",
                "category",
                "content",
                "amount",
                "necessity",
            ]
        )

        empty_expenses.to_csv(
            EXPENSES_FILE,
            index=False,
            encoding="utf-8-sig",
        )

    if not SETTINGS_FILE.exists():
        default_settings = pd.DataFrame(
            [
                {
                    "nickname": "あなた",
                    "monthly_income": 80000,
                    "monthly_saving_goal": 10000,
                    "priority": "推し活",
                    "priority_custom": "",
                }
            ]
        )

        default_settings.to_csv(
            SETTINGS_FILE,
            index=False,
            encoding="utf-8-sig",
        )


def load_expenses():
    create_files()

    try:
        df = pd.read_csv(EXPENSES_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    required_columns = [
        "id",
        "date",
        "category",
        "content",
        "amount",
        "necessity",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    if df.empty:
        return pd.DataFrame(columns=required_columns)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    ).fillna(0).astype(int)

    df["id"] = pd.to_numeric(
        df["id"],
        errors="coerce",
    ).fillna(0).astype(int)

    df = df.dropna(subset=["date"])

    return df


def save_expenses(df):
    save_df = df.copy()

    if not save_df.empty:
        save_df["date"] = pd.to_datetime(
            save_df["date"]
        ).dt.strftime("%Y-%m-%d")

    save_df.to_csv(
        EXPENSES_FILE,
        index=False,
        encoding="utf-8-sig",
    )


def load_settings():
    create_files()

    try:
        df = pd.read_csv(SETTINGS_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    if df.empty:
        return {
            "nickname": "あなた",
            "monthly_income": 80000,
            "monthly_saving_goal": 10000,
            "priority": "推し活",
            "priority_custom": "",
        }

    return df.iloc[0].to_dict()


def save_settings(
    nickname,
    monthly_income,
    monthly_saving_goal,
    priority,
    priority_custom,
):
    settings_df = pd.DataFrame(
        [
            {
                "nickname": nickname,
                "monthly_income": int(monthly_income),
                "monthly_saving_goal": int(
                    monthly_saving_goal
                ),
                "priority": priority,
                "priority_custom": priority_custom,
            }
        ]
    )

    settings_df.to_csv(
        SETTINGS_FILE,
        index=False,
        encoding="utf-8-sig",
    )


# ==================================================
# 便利な関数
# ==================================================

def yen(value):
    return f"¥{int(value):,}"


def get_this_month_data(df):
    if df.empty:
        return df.copy()

    today = pd.Timestamp.today()

    result = df[
        (df["date"].dt.year == today.year)
        & (df["date"].dt.month == today.month)
    ].copy()

    return result


def get_priority_name(settings):
    priority = str(
        settings.get(
            "priority",
            "推し活",
        )
    )

    custom = str(
        settings.get(
            "priority_custom",
            "",
        )
    ).strip()

    if priority == "その他" and custom:
        return custom

    return priority


def get_priority_spending(month_df, priority):
    if month_df.empty:
        return 0

    target_category = PRIORITY_CATEGORY_MAP.get(priority)

    if target_category is None:
        return 0

    total = month_df.loc[
        month_df["category"] == target_category,
        "amount",
    ].sum()

    return int(total)


def get_api_key():
    key = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    try:
        secret_key = st.secrets.get(
            "GEMINI_API_KEY",
            "",
        )

        if secret_key:
            key = secret_key

    except Exception:
        pass

    return key


# ==================================================
# データ読み込み
# ==================================================

create_files()

expenses = load_expenses()
settings = load_settings()
month_df = get_this_month_data(expenses)

nickname = str(
    settings.get(
        "nickname",
        "あなた",
    )
)

income = int(
    settings.get(
        "monthly_income",
        0,
    )
)

saving_goal = int(
    settings.get(
        "monthly_saving_goal",
        0,
    )
)

priority_name = get_priority_name(settings)

monthly_spending = (
    int(month_df["amount"].sum())
    if not month_df.empty
    else 0
)

usable_budget = max(
    income - saving_goal,
    0,
)

remaining_budget = (
    usable_budget - monthly_spending
)

priority_spending = get_priority_spending(
    month_df,
    priority_name,
)


# ==================================================
# タイトル
# ==================================================

st.title("🌿 くらしノート")

st.write(
    f"{nickname}さんの、大切なものを守るAI家計簿"
)

st.caption(
    "無理に我慢するのではなく、"
    "自分が大切にしたいことのために支出を整えます。"
)

st.divider()


# ==================================================
# タブ
# ==================================================

home_tab, input_tab, history_tab, analysis_tab, settings_tab = st.tabs(
    [
        "🏠 ホーム",
        "＋ 支出を記録",
        "📒 履歴",
        "📊 分析・AI",
        "⚙️ 設定",
    ]
)


# ==================================================
# ホーム画面
# ==================================================

with home_tab:

    st.subheader("今月のまとめ")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="今月の支出",
            value=yen(monthly_spending),
        )

    with col2:
        st.metric(
            label="残り使える金額",
            value=yen(remaining_budget),
        )

    with col3:
        st.metric(
            label="大切にしたいもの",
            value=priority_name,
            delta=f"今月 {yen(priority_spending)}",
            delta_color="off",
        )

    with col4:
        st.metric(
            label="今月使える予算",
            value=yen(usable_budget),
        )

    st.write("")

    if remaining_budget < 0:
        st.error(
            f"今月は予算を{yen(abs(remaining_budget))}"
            "超えています。分析画面で見直してみましょう。"
        )

    elif usable_budget > 0:
        remaining_percent = max(
            min(
                remaining_budget / usable_budget,
                1,
            ),
            0,
        )

        st.write("#### 今月の予算残り")

        st.progress(
            remaining_percent,
            text=f"{yen(remaining_budget)} 残っています",
        )

    st.write("")
    st.subheader("最近の記録")

    if month_df.empty:
        st.info(
            "今月の記録はまだありません。"
            "「支出を記録」から追加してみましょう。",
            icon="🫧",
        )

    else:
        recent_df = month_df.sort_values(
            "date",
            ascending=False,
        ).head(5).copy()

        recent_df["日付"] = recent_df[
            "date"
        ].dt.strftime("%m月%d日")

        recent_df["カテゴリー"] = recent_df[
            "category"
        ].apply(
            lambda category: (
                f"{CATEGORY_ICONS.get(category, '🫧')} "
                f"{category}"
            )
        )

        recent_df["内容"] = recent_df["content"]

        recent_df["金額"] = recent_df[
            "amount"
        ].apply(yen)

        st.dataframe(
            recent_df[
                [
                    "日付",
                    "カテゴリー",
                    "内容",
                    "金額",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        category_total = (
            month_df.groupby(
                "category",
                as_index=False,
            )["amount"]
            .sum()
            .sort_values(
                "amount",
                ascending=False,
            )
        )

        top_category = category_total.iloc[0]

        top_name = top_category["category"]
        top_amount = int(top_category["amount"])

        st.info(
    f"今月最も多い支出は「{top_name}」の{yen(top_amount)}です。",
    icon=CATEGORY_ICONS.get(top_name, "🫧"),
)


# ==================================================
# 支出入力画面
# ==================================================

with input_tab:

    st.subheader("支出を記録する")

    st.caption(
        "必要度も記録すると、"
        "AIが見直せる支出を判断しやすくなります。"
    )

    with st.form(
        "expense_form",
        clear_on_submit=True,
    ):

        left, right = st.columns(2)

        with left:

            expense_date = st.date_input(
                "日付",
                value=date.today(),
            )

            category = st.selectbox(
                "カテゴリー",
                CATEGORIES,
            )

            amount = st.number_input(
                "金額",
                min_value=1,
                value=500,
                step=100,
            )

        with right:

            content = st.text_input(
                "内容",
                placeholder="例：大学帰りのカフェ",
            )

            necessity = st.selectbox(
                "必要度",
                NECESSITIES,
            )

            st.write("")

        submitted = st.form_submit_button(
            "この支出を保存する"
        )

    if submitted:

        if not content.strip():

            st.warning(
                "支出の内容を入力してください。"
            )

        else:

            new_id = int(
                datetime.now().timestamp()
                * 1000000
            )

            new_expense = pd.DataFrame(
                [
                    {
                        "id": new_id,
                        "date": pd.Timestamp(
                            expense_date
                        ),
                        "category": category,
                        "content": content.strip(),
                        "amount": int(amount),
                        "necessity": necessity,
                    }
                ]
            )

            updated_expenses = pd.concat(
                [
                    expenses,
                    new_expense,
                ],
                ignore_index=True,
            )

            save_expenses(
                updated_expenses
            )

            st.success(
                "支出を保存しました。",
                icon="🌱",
            )

            st.rerun()


# ==================================================
# 履歴画面
# ==================================================

with history_tab:

    st.subheader("支出履歴")

    if expenses.empty:

        st.info(
            "まだ支出記録がありません。",
            icon="📒",
        )

    else:

        year_month_list = sorted(
            expenses["date"]
            .dt.strftime("%Y-%m")
            .unique(),
            reverse=True,
        )

        filter_col1, filter_col2 = st.columns(
            [
                1,
                2,
            ]
        )

        with filter_col1:

            selected_month = st.selectbox(
                "表示する月",
                year_month_list,
            )

        with filter_col2:

            selected_categories = st.multiselect(
                "カテゴリーで絞り込み",
                CATEGORIES,
            )

        history_df = expenses[
            expenses["date"]
            .dt.strftime("%Y-%m")
            == selected_month
        ].copy()

        if selected_categories:

            history_df = history_df[
                history_df["category"].isin(
                    selected_categories
                )
            ]

        history_df = history_df.sort_values(
            "date",
            ascending=False,
        )

        if history_df.empty:

            st.info(
                "条件に合う記録がありません。"
            )

        else:

            display_df = history_df.copy()

            display_df["日付"] = display_df[
                "date"
            ].dt.strftime("%Y年%m月%d日")

            display_df["カテゴリー"] = display_df[
                "category"
            ].apply(
                lambda category: (
                    f"{CATEGORY_ICONS.get(category, '🫧')} "
                    f"{category}"
                )
            )

            display_df["内容"] = display_df[
                "content"
            ]

            display_df["金額"] = display_df[
                "amount"
            ].apply(yen)

            display_df["必要度"] = display_df[
                "necessity"
            ]

            st.dataframe(
                display_df[
                    [
                        "日付",
                        "カテゴリー",
                        "内容",
                        "金額",
                        "必要度",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            history_total = int(
                history_df["amount"].sum()
            )

            st.metric(
                "表示中の合計",
                yen(history_total),
            )

            st.divider()

            st.write("#### 記録を削除する")

            delete_labels = {}

            for row in history_df.itertuples():

                label = (
                    f"{row.date.strftime('%m月%d日')}"
                    f"｜{row.category}"
                    f"｜{row.content}"
                    f"｜{yen(row.amount)}"
                )

                delete_labels[label] = int(row.id)

            selected_delete = st.selectbox(
                "削除する記録",
                list(delete_labels.keys()),
            )

            delete_confirm = st.checkbox(
                "選んだ記録を削除することを確認しました"
            )

            if st.button(
                "選択した記録を削除"
            ):

                if not delete_confirm:

                    st.warning(
                        "確認欄にチェックしてください。"
                    )

                else:

                    delete_id = delete_labels[
                        selected_delete
                    ]

                    updated_expenses = expenses[
                        expenses["id"] != delete_id
                    ].copy()

                    save_expenses(
                        updated_expenses
                    )

                    st.success(
                        "記録を削除しました。"
                    )

                    st.rerun()

        download_df = expenses.copy()

        download_df["date"] = download_df[
            "date"
        ].dt.strftime("%Y-%m-%d")

        csv_data = download_df.to_csv(
            index=False,
            encoding="utf-8-sig",
        ).encode("utf-8-sig")

        st.download_button(
            label="CSVをダウンロード",
            data=csv_data,
            file_name="kurashi_note_expenses.csv",
            mime="text/csv",
        )


# ==================================================
# 分析・AI画面
# ==================================================

with analysis_tab:

    st.subheader("今月の支出分析")

    if month_df.empty:

        st.info(
            "今月の記録を追加すると、"
            "グラフとAIアドバイスを表示できます。",
            icon="📊",
        )

    else:

        category_summary = (
            month_df.groupby(
                "category",
                as_index=False,
            )["amount"]
            .sum()
            .sort_values(
                "amount",
                ascending=False,
            )
        )

        necessity_summary = (
            month_df.groupby(
                "necessity",
                as_index=False,
            )["amount"]
            .sum()
        )

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:

            bar_chart = px.bar(
                category_summary,
                x="amount",
                y="category",
                orientation="h",
                title="カテゴリー別支出",
                labels={
                    "amount": "金額",
                    "category": "",
                },
            )

            bar_chart.update_traces(
                marker_color="#65c8b5",
                hovertemplate=(
                    "%{y}<br>"
                    "¥%{x:,}"
                    "<extra></extra>"
                ),
            )

            bar_chart.update_layout(
                plot_bgcolor=(
                    "rgba(0,0,0,0)"
                ),
                paper_bgcolor=(
                    "rgba(0,0,0,0)"
                ),
                font_color="#365751",
                yaxis={
                    "categoryorder":
                    "total ascending"
                },
                margin=dict(
                    l=10,
                    r=10,
                    t=50,
                    b=10,
                ),
            )

            st.plotly_chart(
                bar_chart,
                use_container_width=True,
            )

        with chart_col2:

            pie_chart = px.pie(
                necessity_summary,
                values="amount",
                names="necessity",
                hole=0.5,
                title="必要度ごとの割合",
                color_discrete_sequence=[
                    "#65c8b5",
                    "#b8e5de",
                    "#dceff3",
                ],
            )

            pie_chart.update_layout(
                paper_bgcolor=(
                    "rgba(0,0,0,0)"
                ),
                font_color="#365751",
                legend_title_text="",
                margin=dict(
                    l=10,
                    r=10,
                    t=50,
                    b=10,
                ),
            )

            st.plotly_chart(
                pie_chart,
                use_container_width=True,
            )

        daily_summary = month_df.copy()

        daily_summary["day"] = daily_summary[
            "date"
        ].dt.date

        daily_summary = (
            daily_summary.groupby(
                "day",
                as_index=False,
            )["amount"]
            .sum()
        )

        line_chart = px.line(
            daily_summary,
            x="day",
            y="amount",
            markers=True,
            title="日ごとの支出",
            labels={
                "day": "日付",
                "amount": "金額",
            },
        )

        line_chart.update_traces(
            line_color="#3ea991",
            marker_color="#65c8b5",
        )

        line_chart.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#365751",
            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10,
            ),
        )

        st.plotly_chart(
            line_chart,
            use_container_width=True,
        )

        st.divider()

        st.subheader(
            "🌱 AIからのやさしいアドバイス"
        )

        st.info(
            f"「{priority_name}」を大切にしながら、"
            "無理なく見直せる支出をAIが探します。",
            icon="💧",
        )

        if st.button(
            "AIに今月を分析してもらう"
        ):

            api_key = get_api_key()

            if not api_key:

                st.error(
                    "Gemini APIキーが設定されていません。"
                )

            else:

                category_text = "\n".join(
                    [
                        (
                            f"・{row.category}: "
                            f"{int(row.amount):,}円"
                        )
                        for row
                        in category_summary.itertuples()
                    ]
                )

                expense_details = "\n".join(
                    [
                        (
                            f"・{row.date.strftime('%m/%d')} "
                            f"{row.category} "
                            f"{row.content} "
                            f"{int(row.amount):,}円 "
                            f"必要度：{row.necessity}"
                        )
                        for row
                        in month_df.sort_values(
                            "date"
                        ).itertuples()
                    ]
                )

                prompt = f"""
あなたは、利用者の価値観を大切にする
優しい家計アドバイザーです。

利用者が大切にしたいものを守りながら、
無理なく見直せる支出を提案してください。

【利用者の設定】
大切にしたいもの：{priority_name}
1か月の収入・使えるお金：{income:,}円
毎月残したい金額：{saving_goal:,}円
今月使える予算：{usable_budget:,}円
今月の支出：{monthly_spending:,}円
残り使える金額：{remaining_budget:,}円

【カテゴリー別支出】
{category_text}

【支出明細】
{expense_details}

次の見出しを使って、
日本語で分かりやすく回答してください。

### 今月の良かったところ
良かった点を1～2つ書いてください。

### 見直せそうなところ
見直せそうな支出を最大3つ提案してください。
それぞれ、節約できそうな金額の目安も書いてください。

### 大切なものに回せそうな金額
見直した場合、
「{priority_name}」に回せそうな合計金額を書いてください。

### 来月やってみること
無理なく実行できる行動を2つ書いてください。

注意事項：
・「生活に必要」と記録された支出は、
基本的に削減候補にしないでください。
・利用者が大切にしたい
「{priority_name}」を削る提案は避けてください。
・食費や交通費を極端に減らす提案はしないでください。
・データだけでは判断できない場合は、
断定せず「見直せるか確認しましょう」と書いてください。
・説教するような表現は使わないでください。
・親しみやすく優しい文章にしてください。
"""

                try:

                    with st.spinner(
                        "今月の支出を分析しています…"
                    ):

                        client = genai.Client(
                            api_key=api_key
                        )

                        jls_extract_var = contents
                        response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=prompt,
)
                        

                    if response.text:

                        st.success(
                            "分析が完了しました。",
                            icon="🌿",
                        )

                        st.markdown(
                            response.text
                        )

                    else:

                        st.warning(
                            "AIから文章を取得できませんでした。"
                        )

                except Exception as error:

                    st.error(
                        "AI分析中にエラーが発生しました。"
                    )

                    st.code(
                        str(error)
                    )


# ==================================================
# 設定画面
# ==================================================

with settings_tab:

    st.subheader("あなたの設定")

    st.caption(
        "ここで設定した内容を使って、"
        "今月の残り予算とAIアドバイスを作ります。"
    )

    with st.form(
        "settings_form"
    ):

        nickname_input = st.text_input(
            "ニックネーム",
            value=nickname,
        )

        setting_col1, setting_col2 = st.columns(2)

        with setting_col1:

            income_input = st.number_input(
                "1か月の収入・使えるお金",
                min_value=0,
                value=income,
                step=1000,
            )

        with setting_col2:

            saving_input = st.number_input(
                "毎月残したい金額",
                min_value=0,
                value=saving_goal,
                step=1000,
            )

        current_priority = str(
            settings.get(
                "priority",
                "推し活",
            )
        )

        if current_priority in PRIORITIES:
            priority_index = PRIORITIES.index(
                current_priority
            )
        else:
            priority_index = 0

        priority_input = st.selectbox(
            "一番大切にしたいもの",
            PRIORITIES,
            index=priority_index,
        )

        custom_input = st.text_input(
            "「その他」を選んだ場合の内容",
            value=str(
                settings.get(
                    "priority_custom",
                    "",
                )
            ),
            placeholder="例：ペット、健康、スポーツ",
        )

        settings_submit = st.form_submit_button(
            "設定を保存する"
        )

    if settings_submit:

        if saving_input > income_input:

            st.warning(
                "毎月残したい金額は、"
                "収入・使えるお金以下にしてください。"
            )

        elif (
            priority_input == "その他"
            and not custom_input.strip()
        ):

            st.warning(
                "「その他」を選んだ場合は、"
                "内容を入力してください。"
            )

        else:

            save_settings(
                nickname=(
                    nickname_input.strip()
                    or "あなた"
                ),
                monthly_income=income_input,
                monthly_saving_goal=saving_input,
                priority=priority_input,
                priority_custom=custom_input.strip(),
            )

            st.success(
                "設定を保存しました。",
                icon="🌿",
            )

            st.rerun()