import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="📘 学生指導用データベース", layout="wide")
st.title("🔍 学生指導用データベース")

# ▼ どこかで df を作った直後に必ず実行
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 目に見えないBOMや全角/半角スペース、改行などを除去
    def _clean(s):
        s = str(s)
        s = s.replace("\ufeff", "")           # BOM
        s = re.sub(r"[\u3000 \t\r\n]+", "", s)  # 全角/半角空白と改行等を除去
        return s
    df = df.copy()
    df.columns = [_clean(c) for c in df.columns]

    # 列名の別名を吸収（存在している方を正式名に寄せる）
    alias_map = {
        # 問題文の候補
        "問題文": ["設問", "問題", "本文"],
        # 選択肢
        "選択肢1": ["選択肢Ａ","選択肢a","A","ａ"],
        "選択肢2": ["選択肢Ｂ","選択肢b","B","ｂ"],
        "選択肢3": ["選択肢Ｃ","選択肢c","C","ｃ"],
        "選択肢4": ["選択肢Ｄ","選択肢d","D","ｄ"],
        "選択肢5": ["選択肢Ｅ","選択肢e","E","ｅ"],
        # 正解
        "正解":   ["解答","答え","ans","answer"],
        # 科目分類
        "科目分類": ["分類","科目","カテゴリ","カテゴリー"]
    }
    colset = set(df.columns)
    for canonical, candidates in alias_map.items():
        if canonical in colset:
            continue
        for c in candidates:
            if c in colset:
                df.rename(columns={c: canonical}, inplace=True)
                colset.add(canonical)
                break
    return df

# 例）読み込み直後に
# df = pd.read_csv("...csv")
# df = normalize_columns(df)

# 以降、列アクセスは .get() で安全に
def get_q(row):
    return row.get("問題文", "")

def get_choice(row, i):
    return row.get(f"選択肢{i}", "")

def get_ans(row):
    return row.get("正解", "")

def get_cat(row):
    return row.get("科目分類", "")

# ---------- ここから保存ボタン周辺の堅牢化 ----------
today = datetime.now().strftime("%m%d")
search = st.session_state.get("search", "")  # どこかで入力している想定
filename_base = f"{(search or 'results')}_{today}"

# filtered_df が未定義/空のとき落ちないように
if "filtered_df" not in locals():
    st.info("検索結果がありません。")
else:
    if filtered_df.empty:
        st.warning("ヒットがありません。")
    else:
        # 念のため列を正規化
        filtered_df = normalize_columns(filtered_df)

        # 文字列化ユーティリティ（NaN安全）
        def _s(x):
            return "" if pd.isna(x) else str(x)

        # .txt 生成（表示用→DLボタン）
        txt_buffer = io.StringIO()
        for _, row in filtered_df.iterrows():
            row = row.to_dict()
            txt_buffer.write(f"問題文: {_s(get_q(row))}\n")
            for i in range(1, 6):
                v = _s(get_choice(row, i))
                if v != "":
                    txt_buffer.write(f"選択肢{i}: {v}\n")
            txt_buffer.write(f"正解: {_s(get_ans(row))}\n")
            txt_buffer.write(f"分類: {_s(get_cat(row))}\n")
            txt_buffer.write("-" * 40 + "\n")

        st.download_button(
            label="📥 ヒット結果を .txt でダウンロード",
            data=txt_buffer.getvalue(),
            file_name=f"{filename_base}.txt",
            mime="text/plain"
        )

        # .csv 生成（列が無ければ追加して出力）
        out_df = filtered_df.copy()
        for c in ["問題文","選択肢1","選択肢2","選択肢3","選択肢4","選択肢5","正解","科目分類"]:
            if c not in out_df.columns:
                out_df[c] = ""
        csv_buffer = io.StringIO()
        out_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 ヒット結果を .csv でダウンロード",
            data=csv_buffer.getvalue(),
            file_name=f"{filename_base}.csv",
            mime="text/csv"
        )
