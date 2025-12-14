import streamlit as st
import pandas as pd
import io

# ページ設定
st.set_page_config(page_title="出荷重量計算システム", layout="wide")

st.title("🚛 出荷重量計算 & パレット割付")

# --- 1. ファイル読込 ---
st.subheader("1. 出荷データ(Excel/CSV)の読み込み")
uploaded_file = st.file_uploader("ファイルをアップロード", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    try:
        # 拡張子で読み込み方を分ける
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
            name_col = st.selectbox("製品名の列を選択", columns, index=0)
            weight_col = st.selectbox("重量の列を選択", columns, index=min(1, len(columns)-1))
        
        with col2:
            # パレット設定
            max_weight = st.number_input("1パレットの最大積載量 (kg)", value=500, step=50)
            
        # 計算実行ボタン
        if st.button("計算・割付実行", type="primary"):
            
            # --- 3. 割付ロジック ---
            df_result = df.copy()
            
            # 重量を数値に変換（エラー回避）
            df_result[weight_col] = pd.to_numeric(df_result[weight_col], errors='coerce').fillna(0)
            
            pallet_no = 1
            current_weight = 0
            allocations = [] # 各行のパレット番号を保存
            
            for index, row in df_result.iterrows():
                w = row[weight_col]
                
                # 単体で最大重量を超えている場合
                if w > max_weight:
                    allocations.append(f"エラー:重量超過 ({pallet_no})")
                    # 次のパレットへ
                    pallet_no += 1
                    current_weight = 0
                    continue

                # 積載可能かチェック
                if current_weight + w <= max_weight:
                    # 積める
                    allocations.append(pallet_no)
                    current_weight += w
                else:
                    # 積めない -> 次のパレットへ
                    pallet_no += 1
                    allocations.append(pallet_no)
                    current_weight = w
            
            # 結果をデータフレームに追加
            df_result["パレットNo"] = allocations
            
            # --- 4. 結果表示 ---
            st.success("計算完了！")
            
            # パレットごとの集計
            summary = df_result.groupby("パレットNo")[weight_col].sum().reset_index()
            summary.columns = ["パレットNo", "総重量(kg)"]
            
            # グラフ表示
            st.subheader("3. パレット別積載状況")
            col_res1, col_res2 = st.columns([2, 1])
            
            with col_res1:
                # 棒グラフ
                st.bar_chart(summary.set_index("パレットNo"))
            
            with col_res2:
                # 集計表
                st.dataframe(summary)
                # 重量オーバーチェック
                over_pallets = summary[summary["総重量(kg)"] > max_weight]
                if not over_pallets.empty:
                    st.error(f"⚠️ 重量オーバーのパレットがあります: {over_pallets['パレットNo'].tolist()}")
                else:
                    st.info("✅ すべて制限内です")

            # 詳細リスト
            with st.expander("▼ 割付後の詳細リストを見る"):
                st.dataframe(df_result)

            # --- 5. Excel出力 ---
            st.subheader("4. 印刷用ファイルのダウンロード")
            
            # Excel作成
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_result.to_excel(writer, index=False, sheet_name='パレット割付表')
                
                # Excelのフォーマット調整（列幅など）
                workbook = writer.book
                worksheet = writer.sheets['パレット割付表']
                format1 = workbook.add_format({'num_format': '#,##0.0'})
                worksheet.set_column('A:Z', 15, format1) # 幅広めに

            output.seek(0)
            
            st.download_button(
                label="📥 結果Excelをダウンロード (印刷用)",
                data=output,
                file_name="パレット割付結果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.write("ファイル形式を確認してください。")

else:
    st.info("👆 上記ボタンからデータファイルをアップロードしてください。")
