import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="📘 学生指導用データベース", layout="wide")
st.title("🔍 学生指導用データベース")

# 📁 ファイルアップロード（CSVのみ）
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is None:
    st.warning("📂 CSVファイルをアップロードしてください")
    st.stop()

# ✅ データ読み込み
df = pd.read_csv(uploaded_file)
df.fillna("", inplace=True)

# 🔍 検索ボックス
search = st.text_input("問題文・選択肢・分類で検索:", "")

# 🔎 検索処理
if search:
    filtered_df = df[df.apply(
        lambda row: search in str(row["問題文"]) or
                    any(search in str(row.get(f"選択肢{i}", "")) for i in range(1, 6)) or
                    search in str(row.get("科目分類", "")),
        axis=1)]
else:
    filtered_df = df

# 🔢 ヒット件数を表示
st.info(f"{len(filtered_df)} 件ヒットしました")

# ⚠️ ヒットなし
if filtered_df.empty:
    st.warning("該当するレコードがありません。")
    st.stop()

# 🔢 表示するレコード番号
record_idx = st.number_input("表示するレコード番号:", 0, len(filtered_df)-1, 0)

# 📄 該当レコードの取得
record = filtered_df.iloc[record_idx]

# 📌 表示内容
st.markdown("---")
st.markdown(f"### 🧪 問題文")
st.markdown(f"**{record['問題文']}**")

st.markdown("### ✏️ 選択肢")
for i in range(1, 6):
    label = f"選択肢{i}"
    if label in record and pd.notna(record[label]) and record[label].strip() != "":
        st.markdown(f"- {record[label]}")

st.markdown(f"### ✅ 正解: **{record.get('正解', 'N/A')}**")
st.markdown(f"### 🏷️ 分類: **{record.get('科目分類', 'N/A')}**")

# 💬 コメント欄
st.text_area("💬 コメントを記録", "")

# 📥 ダウンロード用ファイル生成
today = datetime.now().strftime("%m%d")
if search:
    filename_base = f"{search}_{today}"

    # .txt 形式
    txt_buffer = io.StringIO()
    for _, row in filtered_df.iterrows():
        txt_buffer.write(f"問題文: {row['問題文']}\n")
        for i in range(1, 6):
            label = f"選択肢{i}"
            if label in row and pd.notna(row[label]) and row[label].strip() != "":
                txt_buffer.write(f"{label}: {row[label]}\n")
        txt_buffer.write(f"正解: {row.get('正解', '')}\n")
        txt_buffer.write(f"分類: {row.get('科目分類', '')}\n")
        txt_buffer.write("-" * 40 + "\n")

    # 📥 download_button（.txt）
    st.download_button(
        label="📥 ヒット結果を .txt でダウンロード",
        data=txt_buffer.getvalue(),
        file_name=f"{filename_base}.txt",
        mime="text/plain"
    )

    # 📥 download_button（.csv）
    csv_buffer = io.StringIO()
    filtered_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 ヒット結果を .csv でダウンロード",
        data=csv_buffer.getvalue(),
        file_name=f"{filename_base}.csv",
        mime="text/csv"
    )
