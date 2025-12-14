import streamlit as st

# ページ設定（必ず一番最初に書く）
# st.set_page_config(...) があればそのままでOK

# ==========================================
# 🔐 パスワード認証ブロック (ここから)
# ==========================================
def check_password():
    """パスワード認証を行う関数"""
    # ----------------------------------------------------
    # ▼ ここに好きなパスワードを設定してください
    SECRET_PASSWORD = "mbss3457" 
    # ----------------------------------------------------

    # セッションに認証状態がなければ初期化
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # ログインフォーム
    if not st.session_state.password_correct:
        st.title("🔒 ログイン")
        password_input = st.text_input("パスワードを入力してください", type="password")
        
        if st.button("ログイン"):
            if password_input == SECRET_PASSWORD:
                st.session_state.password_correct = True
                st.rerun() # 画面をリロードしてアプリを表示
            else:
                st.error("パスワードが違います")
        
        # 認証されるまではここで処理をストップ（下のコードを読み込ませない）
        st.stop()

# アプリの冒頭で認証を実行
check_password()
# ==========================================
# 🔐 パスワード認証ブロック (ここまで)
# ==========================================

# ↓↓↓ ここから下にいつものアプリのコードを書く ↓↓↓
st.title("メインのアプリ画面")
# ...
