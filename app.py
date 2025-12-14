import streamlit as st
import pandas as pd
import io

# ページ設定
st.set_page_config(page_title="出荷重量計算システム", layout="wide")

# ==========================================
# 🔐 パスワード認証設定
# ==========================================
def check_password():
    """パスワード認証を行う関数"""
    # ----------------------------------------------------
    # ▼ ここに好きなパスワードを設定してください（今は 1234 にしています）
    SECRET_PASSWORD = "mbss3457" 
    # ----------------------------------------------------

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.title("🔒 ログイン")
        st.caption("関係者専用アプリです")
        password_input = st.text_input("パスワードを入力してください", type="password")
        
        if st.button("ログイン"):
            if password_input == SECRET_PASSWORD:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()

# 認証実行（これを通過しないと下の画面は見えません）
check_password()

# ==========================================
# 🚛 メインアプリ画面
# ==========================================
st.title("🚛 出荷重量計算 & パレット割付")

# --- 1. ファイル読込 ---
st.subheader("1. 出荷データ(Excel/CSV)の読み込み")
uploaded_file = st.file_uploader("ファイルをアップロード", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    try:
        # 拡張子判別
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.write("▼ 読み込んだデータ（最初の5行）")
        st.dataframe(df.head())

        # --- 2. 設定 ---
        st.subheader("2. 計算設定")
        
        col1, col2 = st.columns(2)
        with col1:
            # 列の選択
            columns = df.columns.tolist()
            # エラー回避のため、それっぽい列があれば自動選択
            default_w_index = 0
            for i, col in enumerate(columns):
                if "重量" in str(col) or "weight" in str(col).lower():
                    default_w_index = i
            
            name_col = st.selectbox("製品名の列", columns, index=0)
            weight_col = st.selectbox("重量の列", columns, index=default_w_index)
        
        with col2:
            # パレット設定
            max_weight = st.number_input("1パレットの最大積載量 (kg)", value=500, step=50)
            
        # 計算ボタン
        if st.button("計算・割付実行", type="primary"):
            
            # --- 3. 割付ロジック ---
            df_result = df.copy()
            # 重量を数値化
            df_result[weight_col] = pd.to_numeric(df_result[weight_col], errors='coerce').fillna(0)
            
            pallet_no = 1
            current_weight = 0
            allocations = [] 
            
            for index, row in df_result.iterrows():
                w = row[weight_col]
                
                # 単体で重量オーバーの場合
                if w > max_weight:
                    allocations.append(f"エラー:重量超過 ({pallet_no})")
                    pallet_no += 1
                    current_weight = 0
                    continue

                if current_weight + w <= max_weight:
                    allocations.append(pallet_no)
                    current_weight += w
                else:
                    pallet_no += 1
                    allocations.append(pallet_no)
                    current_weight = w
            
            df_result["パレットNo"] = allocations
            
            # --- 4. 結果表示 ---
            st.success("計算完了！")
            
            # 集計
            # エラー文字列が入っていると計算できないので、数値のみ抽出して集計
            valid_rows = df_result[pd.to_numeric(df_result["パレットNo"], errors='coerce').notnull()]
            summary = valid_rows.groupby("パレットNo")[weight_col].sum().reset_index()
            summary.columns = ["パレットNo", "総重量(kg)"]
            
            st.subheader("3. パレット別積載状況")
            col_res1, col_res2 = st.columns([2, 1])
            
            with col_res1:
                # パレット番号を文字列にしてグラフ表示（1.0, 2.0とならないように）
                chart_data = summary.copy()
                chart_data["パレットNo"] = chart_data["パレットNo"].astype(int).astype(str)
                st.bar_chart(chart_data.set_index("パレットNo"))
            
            with col_res2:
                st.dataframe(summary)
                # 重量チェック
                if not summary.empty:
                    over_pallets = summary[summary["総重量(kg)"] > max_weight]
                    if not over_pallets.empty:
                        st.error(f"⚠️ 重量オーバー: {over_pallets['パレットNo'].tolist()}")
                    else:
                        st.info("✅ 全て制限内です")

            with st.expander("▼ 詳細リストを見る"):
                st.dataframe(df_result)

            # --- 5. Excel出力 ---
            st.subheader("4. 結果ダウンロード")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_result.to_excel(writer, index=False, sheet_name='パレット割付表')
                workbook = writer.book
                worksheet = writer.sheets['パレット割付表']
                format1 = workbook.add_format({'num_format': '#,##0.0'})
                worksheet.set_column('A:Z', 15, format1)

            output.seek(0)
            
            st.download_button(
                label="📥 結果Excelをダウンロード",
                data=output,
                file_name="パレット割付結果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"エラー: {e}")
        st.info("ファイル形式や列の選択を確認してください。")

else:
    st.info("👆 ファイルをアップロードしてください")
