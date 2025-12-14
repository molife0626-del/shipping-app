import streamlit as st
import pandas as pd
import io
import openpyxl # Excelテンプレート操作用
from datetime import datetime

# ページ設定
st.set_page_config(page_title="出荷重量計算システム(印刷対応版)", layout="wide")

# ==========================================
# 🔐 パスワード認証
# ==========================================
def check_password():
    SECRET_PASSWORD = "mbss3457" 
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.title("🔒 ログイン")
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == SECRET_PASSWORD:
                st.session_state.password_correct = True
                st.rerun()
        st.stop()

check_password()

# ==========================================
# 🚛 メインアプリ
# ==========================================
st.title("🚛 出荷重量計算システム (印刷対応版)")

if 'master_df' not in st.session_state:
    st.session_state.master_df = None

# --- STEP 1: マスター登録 (変更なし) ---
st.header("❶ 単重マスターの登録")
master_file = st.file_uploader("単重マスター(Excel/CSV)", type=['xlsx','xls','csv'], key="m")
if master_file:
    try:
        if master_file.name.endswith('.csv'): df_m = pd.read_csv(master_file)
        else: df_m = pd.read_excel(master_file)
        st.dataframe(df_m.head(3))
        cols_m = df_m.columns.tolist()
        c1,c2,c3 = st.columns(3)
        def_n, def_w = 0, 0
        for i,c in enumerate(cols_m):
            if "品名" in str(c): def_n=i
            if "(Kg)" in str(c) or "単重" in str(c): def_w=i
        m_n = c1.selectbox("製品名", cols_m, index=def_n)
        m_w = c2.selectbox("重量", cols_m, index=def_w)
        unit = c3.radio("単位", ["kg", "g"], index=0)
        if st.button("登録"):
            cm = df_m[[m_n, m_w]].copy()
            cm.columns = ["製品名","単重"]
            cm["単重"] = pd.to_numeric(cm["単重"], errors='coerce').fillna(0)
            if unit=="g": cm["単重"]=cm["単重"]/1000.0
            st.session_state.master_df = cm.drop_duplicates("製品名")
            st.success("登録完了")
    except Exception as e: st.error(e)
st.divider()

# --- STEP 2: 計算 (変更なし) ---
st.header("❷ 出荷指示計算")
if not st.session_state.master_df: st.stop()
ship_file = st.file_uploader("出荷指示(Excel/CSV)", type=['xlsx','xls','csv'], key="s")
if ship_file:
    try:
        if ship_file.name.endswith('.csv'): df_s = pd.read_csv(ship_file)
        else: df_s = pd.read_excel(ship_file)
        st.dataframe(df_s.head(3))
        cols_s = df_s.columns.tolist()
        c1,c2,c3 = st.columns(3)
        def_sn, def_sq = 0,0
        for i,c in enumerate(cols_s):
            if "品名" in str(c): def_sn=i
            if "数量" in str(c) or "数" in str(c): def_sq=i
        s_n = c1.selectbox("製品名", cols_s, index=def_sn)
        s_q = c2.selectbox("数量", cols_s, index=def_sq)
        max_w = c3.number_input("1パレット上限(kg)", value=500, step=50)

        if st.button("計算実行", type="primary"):
            merged = pd.merge(df_s, st.session_state.master_df, left_on=s_n, right_on="製品名", how="left")
            merged[s_q] = pd.to_numeric(merged[s_q], errors='coerce').fillna(0)
            merged["総重量"] = merged[s_q] * merged["単重"]
            
            pid, cur_w, alloc = 1, 0, []
            for _,r in merged.iterrows():
                w = r["総重量"]
                if w>max_w: alloc.append("超過"); continue
                if cur_w+w<=max_w: alloc.append(pid); cur_w+=w
                else: pid+=1; alloc.append(pid); cur_w=w
            merged["パレットNo"] = alloc
            res_df = merged[["パレットNo", s_n, s_q, "単重", "総重量"]].rename(columns={s_n:"製品名", s_q:"数量"})
            
            valid = res_df[pd.to_numeric(res_df["パレットNo"], errors='coerce').notnull()]
            summary = valid.groupby("パレットNo")["総重量"].sum().reset_index()
            
            st.success("計算完了")
            c_r1, c_r2 = st.columns([1,2])
            c_r1.dataframe(summary, hide_index=True)
            c_r2.dataframe(res_df, hide_index=True)

            # ---------------------------------------------------------
            # STEP 3: 印刷用Excel出力 (ここを大幅変更)
            # ---------------------------------------------------------
            st.divider()
            st.header("❸ 印刷用ファイルの出力")
            st.caption("テンプレートに計算結果を埋め込んだExcelをダウンロードします。")

            # テンプレート読み込み
            template_path = "template.xlsx" # GitHubにアップロードしたファイル名
            try:
                wb = openpyxl.load_workbook(template_path)
                ws = wb.active # 最初のシートを選択

                # --- データ書き込み処理 ---
                # 1. 日付 (今日の日付)
                now = datetime.now()
                ws['C2'] = now.year  # 年
                ws['E2'] = now.month # 月
                ws['G2'] = now.day   # 日

                # 2. パレットごとの重量
                # summaryデータフレームを辞書に変換 {パレットNo: 重量, ...}
                summary_dict = dict(zip(summary["パレットNo"], summary["総重量"]))

                # 各セルに書き込む（パレットが存在しなければ0kg）
                # ※ 以下のセル番地('H5'など)は、実際のテンプレートに合わせて修正してください
                ws['H5'] = summary_dict.get(1, 0) # No.1
                ws['H6'] = summary_dict.get(2, 0) # No.2
                ws['H7'] = summary_dict.get(3, 0) # No.3
                ws['H8'] = summary_dict.get(4, 0) # No.4
                ws['H16'] = summary_dict.get(5, 0)# No.5 (キャリア)
                ws['H12'] = summary_dict.get(6, 0)# No.6 (Fサイクロ)

                # 3. 合計重量
                total_weight = summary["総重量"].sum()
                ws['H20'] = total_weight # TOTAL

                # --- 保存とダウンロード ---
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)

                st.download_button(
                    label="📄 受領証Excelをダウンロード",
                    data=output,
                    file_name=f"受領証_{now.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except FileNotFoundError:
                st.error("エラー: 'template.xlsx' が見つかりません。GitHubにアップロードしてください。")
            except Exception as e:
                st.error(f"Excel作成エラー: {e}")

    except Exception as e: st.error(f"エラー: {e}")
