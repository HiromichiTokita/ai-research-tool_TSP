import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# 初期設定
# ==========================================
# 取得したAPIキーをここに貼り付けてください
API_KEY = "AIzaSyCUyxUUpADh-UBtMxAiC6YV3C-ifqKx234"
client = genai.Client(api_key=API_KEY)

# ==========================================
# セッション状態（会話履歴）の管理
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.theme = ""
    st.session_state.proposals = []
    st.session_state.selected_proposal = ""
    st.session_state.extra_request = ""

st.title("NotebookLM向け 深掘りリサーチツール 📚🌍")

# ==========================================
# UIと処理の分岐
# ==========================================

# 【ステップ1】リサーチしたいテーマを入力
if st.session_state.step == 1:
    theme = st.text_input("どのようなテーマについて最新情報をリサーチ・整理したいですか？", placeholder="例: 日本の科学技術予算の推移")
    
    if st.button("次へ"):
        if theme:
            st.session_state.theme = theme
            with st.spinner('最適なリサーチの切り口を考えています...'):
                prompt = f"""
                「{theme}」について最新情報をリサーチし、NotebookLM用のまとめ資料を作成します。
                ユーザーがワンクリックで選べるように、リサーチの「切り口（アプローチの方向性）」を異なる視点で3つ提案してください。
                【厳守】出力は必ず3行のみ（1行につき1提案）とし、挨拶や箇条書きの記号（1. や * など）は一切含めないでください。
                """
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                proposals = response.text.strip().split('\n')
                st.session_state.proposals = [p.strip() for p in proposals if p.strip()]
                st.session_state.step = 2
                st.rerun()

# 【ステップ2】AIからの提案を選択する
elif st.session_state.step == 2:
    st.write(f"**テーマ:** {st.session_state.theme}")
    st.write("---")
    st.write("AIが3つのリサーチ方針を提案しました。最も目的に近いものを1つ選んでください。")
    
    selected = st.radio("リサーチ方針（選択してください）:", st.session_state.proposals)
    
    st.write("---")
    extra = st.text_area("追加の要望があれば入力してください（任意）", placeholder="例：2025年以降の最新データも必ず入れてほしい、など")
    
    if st.button("Google検索を実行して深掘り資料を生成する"):
        st.session_state.selected_proposal = selected
        st.session_state.extra_request = extra
        st.session_state.step = 3
        st.rerun()

# 【ステップ3】レポート本文とURLリストの完全分離出力
elif st.session_state.step == 3:
    st.success("方針が決定しました！世界中のウェブから情報を収集し、深掘りレポートを生成します。")
    
    with st.spinner('🌐 英語・日本語の文献を検索し、詳細なレポートを執筆中です...（1分ほどかかります）'):
        user_info = f"【テーマ】\n{st.session_state.theme}\n\n【選択したリサーチ方針】\n{st.session_state.selected_proposal}\n\n【追加の要望】\n{st.session_state.extra_request}"

        # ▼▼▼ 変更：URLだけを独立したタグ [URLS] に出力させる ▼▼▼
        prompt = f"""
        あなたは世界トップクラスのシニアリサーチャーです。以下のユーザーの要望をもとに、Google検索を駆使して「極めて詳細で深掘りされた」プロレベルのレポートを作成してください。
        
        【厳守するリサーチの条件】
        1. 情報源の言語割合: 必ず「海外（英語）のソースを7割」、「日本（日本語）のソースを3割」の比率で情報を集めてください。
        2. 情報の深さとボリューム: 表面的な概要は不要です。背景、根本原因、具体的なデータ（数値や統計）、専門家の意見、今後の予測まで深く掘り下げ、可能な限り長文で情報量の多いレポートにしてください。

        【厳守する出力形式】
        出力は必ず以下の2つの[ ]で囲まれたタグを使用した形式としてください。

        [CONTENT]
        （ここにマークダウン形式で極めて詳細なレポート本文を記述する。本文内にはURLを書かないこと。）

        [URLS]
        （ここに参考にしたWebサイトのURL「だけ」を改行区切りでリストアップする。タイトルや箇条書きの記号（*や-など）も一切不要。純粋なURL文字列のみを並べること。）

        【ユーザーの情報】
        {user_info}
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            raw_text = response.text.strip()
            
            # ▼▼▼ 変更：AIの出力を「本文」と「URLリスト」に切り分ける ▼▼▼
            if '[CONTENT]' in raw_text and '[URLS]' in raw_text:
                content_text = raw_text.split('[CONTENT]')[1].split('[URLS]')[0].strip()
                urls_text = raw_text.split('[URLS]')[1].strip()
            else:
                content_text = raw_text
                urls_text = "URLをうまく抽出できませんでした。本文内をご確認ください。"

            # 本文の表示とダウンロード
            st.write("---")
            st.subheader("📝 海外ソース中心の深掘りリサーチ資料")
            st.markdown(content_text)

            st.write("---")
            st.download_button(
                label="📥 レポート本文(.txt)をダウンロード",
                data=content_text,
                file_name="notebooklm_deep_research.txt",
                mime="text/plain"
            )

            # ▼▼▼ 追加：ワンクリックでコピーできるURL専用ボックス ▼▼▼
            st.write("---")
            st.subheader("🔗 NotebookLM入力用 ソースURLリスト")
            st.info("💡 右上の「コピー」アイコン（📋）を押すと、下のURLリストをすべてコピーできます！")
            
            # st.code を使うと、プログラミングコードのように表示され、自動でコピーボタンが付きます
            st.code(urls_text, language="text")

        except Exception as e:
            st.error("データの生成または解析に失敗しました。もう一度お試しください。")
            st.write("エラー詳細:", e)
    
    st.write("---")
    if st.button("最初からやり直す"):
        st.session_state.step = 1
        st.session_state.theme = ""
        st.session_state.proposals = []
        st.session_state.selected_proposal = ""
        st.session_state.extra_request = ""
        st.rerun()