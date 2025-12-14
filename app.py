import streamlit as st
import pandas as pd
import io
import openpyxl
from datetime import datetime

# ページ設定
st.set_page_config(page_title="出荷重量計算システム(印刷対応版)", layout="wide")

# ==========================================
# 🔐 パスワード認証
# ==========================================
def check_password():
    SECRET_PASSWORD = "1234" 
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

# --- STEP 1: マスター登録 ---
st.header("❶ 単重マスターの登録")
master_file = st.file_uploader("単重マスター(Excel/CSV)", type=None, key="m")

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
            
    except Exception as e: st.error("エラー: ファイル形式を確認してください")
st.divider()

# --- STEP 2: 計算 ---
st.header("❷ 出荷指示計算")

# ★★★ 修正箇所：ここを書き換えました ★★★
if st.session_state.master_df is None:
    st.info("先にマスターを登録してください")
    st.stop()

ship_file = st.file_uploader("出荷指示(Excel/CSV)", type=None, key="s")

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
            # 計算ロジック
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
            
            # 結果保存
            st.session_state.res_df = merged[["パレットNo", s_n, s_q, "単重", "総重量"]].rename(columns={s_n:"製品名", s_q:"数量"})
            
            # 集計
            valid = st.session_state.res_df[pd.to_numeric(st.session_state.res_df["パレットNo"], errors='coerce').notnull()]
            st.session_state.summary = valid.groupby("パレットNo")["総重量"].sum().reset_index()
            
            st.success("計算完了！下にスクロールして印刷用ファイルを作成してください。")
            
            c_r1, c_r2 = st.columns([1,2])
            c_r1.write("集計結果")
            c_r1.dataframe(st.session_state.summary, hide_index=True)
            c_r2.write("詳細リスト")
            c_r2.dataframe(st.session_state.res_df, hide_index=True)

    except Exception as e: st.error(f"エラー: {e}")

# --- STEP 3: 印刷 (テンプレート読込方式) ---
st.divider()
st.header("❸ 印刷用ファイルの出力")

if 'summary' in st.session_state:
    st.markdown("作成した「受領証の雛形（テンプレートExcel）」をここでアップロードしてください。")
    
    template_file = st.file_uploader("テンプレートExcelを選択", type=None, key="tpl")

    if template_file:
        try:
            wb = openpyxl.load_workbook(template_file)
            ws = wb.active

            now = datetime.now()
            
            # 日付
            if ws['C2'].value is None: ws['C2'] = now.year
            if ws['E2'].value is None: ws['E2'] = now.month
            if ws['G2'].value is None: ws['G2'] = now.day

            # 重量の書き込み
            summary_dict = dict(zip(st.session_state.summary["パレットNo"], st.session_state.summary["総重量"]))

            ws['H5'] = summary_dict.get(1, 0)
            ws['H6'] = summary_dict.get(2, 0)
            ws['H7'] = summary_dict.get(3, 0)
            ws['H8'] = summary_dict.get(4, 0)
            
            # 合計
            total_w = st.session_state.summary["総重量"].sum()
            ws['H20'] = total_w

            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            st.download_button(
                label="📄 完成した受領証をダウンロード",
                data=output,
                file_name=f"受領証_{now.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
        except Exception as e:
            st.error(f"テンプレート読み込みエラー: {e}")
else:
    st.info("計算を実行すると、ここに印刷メニューが表示されます。")
