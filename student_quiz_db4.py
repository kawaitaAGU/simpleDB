# app.py  —  学生指導用データベース（堅牢版）
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# ===== 基本設定 =====
st.set_page_config(page_title="📘 学生指導用データベース", layout="wide")
st.title("🔍 学生指導用データベース")

# ===== ユーティリティ =====
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """BOM/空白/改行を除去し、よくある別名を正規名へ寄せる"""
    def _clean(s):
        s = str(s).replace("\ufeff", "")          # BOM
        return re.sub(r"[\u3000 \t\r\n]+", "", s) # 全半角空白と改行
    df = df.copy()
    df.columns = [_clean(c) for c in df.columns]

    alias = {
        "問題文":  ["設問", "問題", "本文"],
        "選択肢1": ["選択肢Ａ","選択肢a","A","ａ"],
        "選択肢2": ["選択肢Ｂ","選択肢b","B","ｂ"],
        "選択肢3": ["選択肢Ｃ","選択肢c","C","ｃ"],
        "選択肢4": ["選択肢Ｄ","選択肢d","D","ｄ"],
        "選択肢5": ["選択肢Ｅ","選択肢e","E","ｅ"],
        "正解":    ["解答","答え","ans","answer"],
        "科目分類": ["分類","科目","カテゴリ","カテゴリー"],
    }
    existing = set(df.columns)
    for canon, cands in alias.items():
        if canon in existing:
            continue
        for c in cands:
            if c in existing:
                df.rename(columns={c: canon}, inplace=True)
                existing.add(canon)
                break
    return df

def safe_get(row: pd.Series | dict, keys, default=""):
    """Series/辞書から、安全に列値を取得（別名フォールバック付き）"""
    if isinstance(row, pd.Series):
        row = row.to_dict()
    for k in keys:
        v = row.get(k, None)
        if v is not None:
            s = str(v).strip()
            if s != "":
                return s
    # 予備：列名の空白/BOMを除去して「問題文」っぽいものを拾う
    for k, v in row.items():
        kk = re.sub(r"\s", "", str(k).replace("\ufeff", ""))
        if kk.endswith("問題文") and v is not None and str(v).strip() != "":
            return str(v).strip()
    return default

def ensure_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """出力CSVに必須列が無ければ空列を足す"""
    need = ["問題文","選択肢1","選択肢2","選択肢3","選択肢4","選択肢5","正解","科目分類"]
    out = df.copy()
    for c in need:
        if c not in out.columns:
            out[c] = ""
    return out

def build_text_block(row: pd.Series | dict) -> str:
    """1問題ぶんのテキスト整形"""
    q = safe_get(row, ["問題文","設問","問題","本文"]) or "（問題文なし）"
    lines = [f"問題文: {q}"]
    for i in range(1, 6):
        val = safe_get(row, [f"選択肢{i}"])
        if val:
            lines.append(f"選択肢{i}: {val}")
    ans = safe_get(row, ["正解","解答","答え"])
    cat = safe_get(row, ["科目分類","分類","科目"])
    lines.append(f"正解: {ans}")
    lines.append(f"分類: {cat}")
    lines.append("-" * 40)
    return "\n".join(lines)

# ===== データ読込（アップロード or 既定パス）=====
with st.sidebar:
    st.header("📥 データ読み込み")
    up = st.file_uploader("CSV を選択（UTF-8 推奨）", type=["csv"])
    default_path = st.text_input("ローカル既定パス（任意）", value="")
    load_btn = st.button("読み込む")

@st.cache_data(show_spinner=False)
def load_df(file_like, path_hint: str):
    if file_like is not None:
        df = pd.read_csv(file_like, dtype=str, encoding="utf-8-sig")
    elif path_hint:
        df = pd.read_csv(path_hint, dtype=str, encoding="utf-8-sig")
    else:
        raise FileNotFoundError("CSV が未指定です。左のアップロードかパス入力を使ってください。")
    df = normalize_columns(df.fillna(""))
    return df

if load_btn:
    try:
        df = load_df(up, default_path)
        st.success(f"読み込み成功：{len(df)} 行")
        st.session_state.df = df
    except Exception as e:
        st.error(f"読み込み失敗：{e}")

if "df" not in st.session_state:
    st.info("左サイドバーから CSV を読み込んでください。")
    st.stop()

df = st.session_state.df

# ===== 検索 =====
st.subheader("🔎 検索")
search = st.text_input("問題文・選択肢・分類で検索（スペース区切りで AND）", value="")
def contains_all(hay: str, terms: list[str]) -> bool:
    hay = (hay or "").lower()
    return all(t.lower() in hay for t in terms)

terms = [t for t in search.split() if t.strip()]
# 検索対象テキストを合成
def row_text(r: pd.Series) -> str:
    parts = [
        safe_get(r, ["問題文","設問","問題","本文"]),
        *[safe_get(r, [f"選択肢{i}"]) for i in range(1,6)],
        safe_get(r, ["正解","解答","答え"]),
        safe_get(r, ["科目分類","分類","科目"]),
    ]
    return " ".join([p for p in parts if p])

if terms:
    mask = df.apply(lambda r: contains_all(row_text(r), terms), axis=1)
    filtered_df = df[mask].reset_index(drop=True)
else:
    filtered_df = df.copy().reset_index(drop=True)

st.success(f"{len(filtered_df)} 件ヒットしました")

# ===== レコード閲覧 =====
if len(filtered_df) == 0:
    st.stop()

col_idx, _ = st.columns([1,3])
with col_idx:
    rec_no = st.number_input("表示するレコード番号:", min_value=0, max_value=max(0, len(filtered_df)-1), value=0, step=1)

record = filtered_df.iloc[rec_no]

st.markdown("### 🧪 問題文")
st.markdown(f"**{safe_get(record, ['問題文','設問','問題','本文']) or '（問題文なし）'}**")

st.markdown("### ✅ 選択肢")
for i in range(1, 6):
    v = safe_get(record, [f"選択肢{i}"])
    if v:
        st.write(f"- 選択肢{i}: {v}")

st.markdown("### 🏁 正解・分類")
st.write(f"**正解**: {safe_get(record, ['正解','解答','答え'])}")
st.write(f"**分類**: {safe_get(record, ['科目分類','分類','科目'])}")

# ===== コメント欄（任意メモ。保存先は実装していません）=====
st.text_area("💬 コメントを記録", "")

# ===== ダウンロード =====
today = datetime.now().strftime("%m%d")
filename_base = f"{(search or 'results')}_{today}"

# .txt まとめ出力
txt_buffer = io.StringIO()
for _, row in filtered_df.iterrows():
    txt_buffer.write(build_text_block(row) + "\n")

st.download_button(
    label="📥 ヒット結果を .txt でダウンロード",
    data=txt_buffer.getvalue(),
    file_name=f"{filename_base}.txt",
    mime="text/plain"
)

# .csv 出力（必須列をそろえる）
csv_buffer = io.StringIO()
ensure_output_columns(filtered_df).to_csv(csv_buffer, index=False, encoding="utf-8-sig")
st.download_button(
    label="📥 ヒット結果を .csv でダウンロード",
    data=csv_buffer.getvalue(),
    file_name=f"{filename_base}.csv",
    mime="text/csv"
)

# ===== デバッグ補助（必要なら開く）=====
with st.expander("🔧 現在の列名（正規化後）を見る"):
    st.write(list(filtered_df.columns))
