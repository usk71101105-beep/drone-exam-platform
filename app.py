import streamlit as st
import pandas as pd
import json
import os
import random
import re
import time
from datetime import datetime

# ==========================================
# 1. ページ基本設定
# ==========================================
st.set_page_config(
    page_title="ドローン国家資格 対策プラットフォーム",
    page_icon="🚁",
    layout="wide"
)

# ==========================================
# 2. 管理者・会員リストおよびJSON成績の永続化管理
# ==========================================
MASTER_ADMIN = "usk71101105@gmail.com"
RESULTS_JSON_FILE = "exam_results.json"
ADMINS_JSON_FILE = "admins.json"
MEMBERS_JSON_FILE = "members.json"
EXCEL_FILENAME = "drone_exam_questions_detailed_calc.xlsx"

# 管理者リストのロード・セーブ関数（氏名も含む構造化データ）
def load_admins():
    admins_dict = {MASTER_ADMIN: {"role": "master", "appointed_by": None, "name": "内藤祐介"}}
    if os.path.exists(ADMINS_JSON_FILE):
        try:
            with open(ADMINS_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        k_clean = str(k).strip().lower()
                        if k_clean:
                            if isinstance(v, dict):
                                admins_dict[k_clean] = v
                            else:
                                admins_dict[k_clean] = {"role": "admin", "appointed_by": MASTER_ADMIN, "name": ""}
                elif isinstance(data, list):
                    for a in data:
                        a_clean = str(a).strip().lower()
                        if a_clean and a_clean not in admins_dict:
                            admins_dict[a_clean] = {"role": "admin", "appointed_by": MASTER_ADMIN, "name": ""}
        except:
            pass
    if MASTER_ADMIN not in admins_dict:
        admins_dict[MASTER_ADMIN] = {"role": "master", "appointed_by": None, "name": "内藤祐介"}
    return admins_dict

def save_admins(admins_dict):
    with open(ADMINS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(admins_dict, f, ensure_ascii=False, indent=2)

# 会員リストのロード・セーブ関数（JSON永続化）
def load_association_members_json():
    members_dict = {MASTER_ADMIN: "内藤 祐介"}
    if os.path.exists(MEMBERS_JSON_FILE):
        try:
            with open(MEMBERS_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        k_clean = str(k).strip().lower()
                        if k_clean:
                            members_dict[k_clean] = str(v).strip()
        except:
            pass
    if MASTER_ADMIN not in members_dict:
        members_dict[MASTER_ADMIN] = "内藤 祐介"
    return members_dict

def save_association_members_json(members_dict):
    with open(MEMBERS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(members_dict, f, ensure_ascii=False, indent=2)

def get_user_display_name(email, email_to_name, admins_dict):
    """管理者名（admins.json優先）、次に名簿、なければメールアドレスを返す"""
    e_low = email.strip().lower()
    if e_low in admins_dict and admins_dict[e_low].get("name"):
        return admins_dict[e_low]["name"]
    return email_to_name.get(e_low, email)

# 成績JSONのロード・セーブ関数
def load_exam_results():
    if os.path.exists(RESULTS_JSON_FILE):
        try:
            with open(RESULTS_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "activity_history" not in data:
                        data["activity_history"] = []
                    return data
                elif isinstance(data, list):
                    return {"exam_history": data, "category_stats": {}, "incorrect_pool": {}, "activity_history": []}
        except:
            pass
    return {"exam_history": [], "category_stats": {}, "incorrect_pool": {}, "activity_history": []}

def save_exam_results(data):
    with open(RESULTS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "app_storage" not in st.session_state:
    st.session_state.app_storage = load_exam_results()

if "last_system_msg" not in st.session_state:
    st.session_state.last_system_msg = "システム正常稼働中"

# ==========================================
# 3. 問題データのロード
# ==========================================
@st.cache_data
def load_exam_data():
    if os.path.exists(EXCEL_FILENAME):
        try:
            return pd.read_excel(EXCEL_FILENAME)
        except Exception as e:
            st.session_state.last_system_msg = f"Excel読込エラー: {str(e)[:30]}"
            return None
    else:
        st.session_state.last_system_msg = "Excelファイル未検出"
        return None

df_questions = load_exam_data()

# ==========================================
# 4. 認証・ログイン状態の管理（厳格ガード仕様）
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# サイドバー上部（協会名＆アプリタイトル）
st.sidebar.markdown("<p style='font-size:12px; font-weight:bold; color:#ff4b4b; margin-bottom:0px;'>一般社団法人 東京多摩ドローン協会</p>", unsafe_allow_html=True)
st.sidebar.title("🚁 ドローン国家資格 対策アプリ")
st.sidebar.markdown("---")

email_to_name = load_association_members_json()
member_emails = list(email_to_name.keys())
admins_dict = load_admins()
registered_admins = list(admins_dict.keys())

if not st.session_state.logged_in:
    st.sidebar.subheader("ログイン / 会員認証")
    input_email = st.sidebar.text_input("メールアドレスを入力", placeholder="user@example.com")
    
    if st.sidebar.button("ログイン"):
        input_email = input_email.strip().lower()
        if input_email and "@" in input_email:
            if input_email in registered_admins or input_email in member_emails:
                st.session_state.logged_in = True
                st.session_state.user_email = input_email
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                storage = st.session_state.app_storage
                if "activity_history" not in storage:
                    storage["activity_history"] = []
                
                storage["activity_history"].append({
                    "timestamp": now_str,
                    "user_email": input_email,
                    "action": "ログイン",
                    "details": "システムログイン"
                })
                save_exam_results(storage)
                
                st.session_state.last_system_msg = "ログイン成功"
                st.success("ログインしました！")
                st.rerun()
            else:
                st.sidebar.error("❌ 登録されていないメールアドレスです。アクセスが拒否されました。")
        else:
            st.sidebar.warning("有効なメールアドレスを入力してください。")
            
    st.stop()

current_user = st.session_state.user_email
current_user_name = get_user_display_name(current_user, email_to_name, admins_dict)
is_admin = current_user in registered_admins

st.sidebar.write(f"👤 ログイン中: `{current_user_name}`")
if is_admin:
    st.sidebar.markdown("🛠️ **【管理者権限】**")

# ==========================================
# サイドバー: ログインユーザーの常時成績確認（一等・二等模試切替対応）
# ==========================================
with st.sidebar.expander("📊 あなたの成績・レポート確認", expanded=False):
    storage_sb = st.session_state.app_storage
    cat_stats_sb = storage_sb.get("category_stats", {}).get(current_user, {})
    history_sb = [h for h in storage_sb.get("exam_history", []) if h["user_email"] == current_user]
    
    st.markdown(f"**📁 カテゴリー別成績（累計）**")
    if df_questions is not None:
        for cat in df_questions["category"].unique():
            stats = cat_stats_sb.get(cat, {"total": 0, "correct": 0})
            t = stats["total"]
            c = stats["correct"]
            rate_str = f"{(c / t * 100):.1f}% ({c}/{t})" if t > 0 else "未実施"
            st.markdown(f"- `{cat}`: **{rate_str}**")
    
    st.markdown("---")
    st.markdown(f"**🎯 本番模試レポート（種別選択）**")
    exam_type_choice_sb = st.selectbox("模試種別を選択", ["二等 本番模擬試験", "一等 本番模擬試験"], key="sb_exam_type_sel")
    
    filtered_history_sb = [h for h in history_sb if exam_type_choice_sb in h.get("exam_type", "")]
    
    if filtered_history_sb:
        total_att = len(filtered_history_sb)
        passed_att = sum(1 for h in filtered_history_sb if h["passed"])
        avg_rt = sum(h["rate"] for h in filtered_history_sb) / total_att
        st.markdown(f"- 総受験回数: **{total_att} 回**")
        st.markdown(f"- 合格回数: **{passed_att} 回**")
        st.markdown(f"- 平均正解率: **{avg_rt:.1f}%**")
    else:
        st.info(f"「{exam_type_choice_sb}」の受験履歴はまだありません。")

st.sidebar.markdown("---")

if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.last_system_msg = "ログアウトしました"
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 5. メイン画面のルーティング
# ==========================================
menu_options = ["📝 問題演習・模擬テスト"]
if is_admin:
    menu_options.append("🛠️ 管理者ダッシュボード")

app_mode = st.sidebar.radio("メニュー", menu_options)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<p style='font-size:11px; color:gray;'><b>ステータスログ:</b> {st.session_state.last_system_msg}</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size:11px; color:gray; text-align:right; margin-top:20px;'><b>開発：内藤祐介</b></p>", unsafe_allow_html=True)

if df_questions is None:
    st.error("問題データが読み込まれていません。管理者ダッシュボードからExcelファイルをアップロードしてください。")
    st.stop()

# ------------------------------------------
# モードA: 問題演習・模擬テスト
# ------------------------------------------
if app_mode == "📝 問題演習・模擬テスト":
    try:
        st.title("📚 ドローン国家資格 試験対策プラットフォーム")
        st.write("一等・二等の各分野演習、長文事例問題、本番模試、および間違えた問題を克服する**弱点克服モード**に挑戦できます。（※スマートフォンやタブレットからの閲覧・受験にも完全対応しています）")
        
        def reset_quiz_state():
            for key in ["current_quiz", "user_answers", "submitted", "exam_mode", "start_time", "time_limit", "is_review_mode"]:
                if key in st.session_state:
                    del st.session_state[key]

        storage = st.session_state.app_storage
        incorrect_pool_dict = storage.get("incorrect_pool", {})
        user_incorrect_indices = incorrect_pool_dict.get(current_user, [])
        
        exam_course_options = [
            "二等 資格試験対策（通常・練習）", 
            "一等 資格試験対策（通常・練習）",
            "🎯 【本番模試】二等 本番模擬試験（50問 / 30分 / 80%合格）",
            "🎯 【本番模試】一等 本番模擬試験（70問 / 75分 / 90%合格）"
        ]

        if len(user_incorrect_indices) > 0:
            st.info(f"🔥 現在、間違えた問題が **{len(user_incorrect_indices)}問** ストックされています。")
            if st.button(f"🔥 【弱点克服モード】間違えた問題の再挑戦を開始する ({len(user_incorrect_indices)}問)", key="start_review_btn"):
                reset_quiz_state()
                st.session_state.is_review_mode = True
                target_df = df_questions.iloc[user_incorrect_indices].reset_index(drop=True)
                st.session_state.current_quiz = target_df.sample(frac=1).reset_index(drop=True)
                st.session_state.user_answers = {}
                st.session_state.submitted = False
                st.session_state.last_system_msg = "弱点克服モード開始"
                st.rerun()
            st.markdown("---")

        exam_course = st.radio(
            "受験する試験コースを選択してください", 
            exam_course_options,
            key="exam_course_radio"
        )
        
        two_categories = [
            "【二等】分野1：規則",
            "【二等】分野2：システム",
            "【二等】分野3：操縦者",
            "【二等】分野4：リスク管理",
            "【二等】計算問題・バッテリー",
            "【二等】長文事例"
        ]
        
        is_official_exam = "【本番模試】" in exam_course
        
        if is_official_exam:
            if "二等" in exam_course:
                target_df = df_questions[df_questions["category"].isin(two_categories)].reset_index(drop=True)
                exam_config = {"count": 50, "time_min": 30, "pass_rate": 80, "name": "二等 本番模擬試験"}
            else:
                target_df = df_questions.copy().reset_index(drop=True)
                exam_config = {"count": 70, "time_min": 75, "pass_rate": 90, "name": "一等 本番模擬試験"}
            
            st.warning(f"⚠️ **{exam_config['name']}モード**：制限時間 **{exam_config['time_min']}分** / 出題数 **{exam_config['count']}問** / 合格基準 **正答率 {exam_config['pass_rate']}%以上** です。途中終了も可能です。")
            
            if st.button("🚀 本番模擬試験を開始する", key="start_official_exam_btn"):
                reset_quiz_state()
                st.session_state.exam_mode = exam_config
                st.session_state.start_time = time.time()
                st.session_state.time_limit = exam_config["time_min"] * 60
                
                temp_pool = target_df.copy()
                chosen_rows = []
                
                def get_core_theme(q_text):
                    clean = re.sub(r"【第\d+問】\s*", "", q_text)
                    clean = re.sub(r"【事例\d+-\d+】\s*", "", clean)
                    clean = re.sub(r"【追加事例\d+】\s*", "", clean)
                    clean = re.sub(r"\s*\(V\d+\)", "", clean)
                    clean = re.sub(r"\s*\(パターン\d+\)", "", clean)
                    clean = re.sub(r"\s*\(計算パターン\d+\)", "", clean)
                    clean = re.sub(r"\s*\(計算シミュレーション\d+\)", "", clean)
                    return clean.strip()

                temp_pool["core_theme"] = temp_pool["question"].apply(get_core_theme)
                unique_themes = temp_pool["core_theme"].unique().tolist()
                random.shuffle(unique_themes)
                
                chosen_themes = unique_themes[:exam_config["count"]]
                for theme in chosen_themes:
                    sub_df = temp_pool[temp_pool["core_theme"] == theme]
                    chosen_rows.append(sub_df.sample(n=1))
                
                if len(chosen_rows) > 0:
                    final_quiz_df = pd.concat(chosen_rows).reset_index(drop=True)
                    st.session_state.current_quiz = final_quiz_df.sample(frac=1).reset_index(drop=True)
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.session_state.last_system_msg = f"{exam_config['name']}開始"
                    st.rerun()
                else:
                    st.error("問題の抽出に失敗しました。データ量を確認してください。")

        else:
            if "二等" in exam_course:
                target_df = df_questions[df_questions["category"].isin(two_categories)].reset_index(drop=True)
                st.info("💡 **二等資格（長文事例問題を含む）**の試験範囲から出題されます。")
            else:
                target_df = df_questions.copy().reset_index(drop=True)
                st.info("💡 **一等資格（総合模試・長文事例問題含む）**の試験範囲として、専門範囲に二等の基礎範囲もすべて自動的にミックスして出題されます。")
            
            st.markdown("---")
            
            test_type = st.radio(
                "出題方法を選択", 
                ["特定カテゴリーから出題", "コース全体からランダム総合模試"], 
                horizontal=True,
                key="test_type_radio"
            )
            
            if test_type == "特定カテゴリーから出題":
                available_cats = target_df["category"].unique().tolist()
                selected_category = st.selectbox("出題カテゴリーを選択してください", available_cats, key="cat_select")
                current_pool = target_df[target_df["category"] == selected_category].reset_index(drop=True)
            else:
                current_pool = target_df
                
            st.write(f"選択中の出題プール対象問題数: **{len(current_pool)} 問**")
            
            num_questions = st.slider("出題数を選択", min_value=5, max_value=min(30, len(current_pool)), value=10, key="num_q_slider")
            
            if st.button("テストを開始する", key="start_practice_btn"):
                reset_quiz_state()
                temp_pool = current_pool.copy()
                chosen_rows = []
                
                def get_core_theme(q_text):
                    clean = re.sub(r"【第\d+問】\s*", "", q_text)
                    clean = re.sub(r"【事例\d+-\d+】\s*", "", clean)
                    clean = re.sub(r"【追加事例\d+】\s*", "", clean)
                    clean = re.sub(r"\s*\(V\d+\)", "", clean)
                    clean = re.sub(r"\s*\(パターン\d+\)", "", clean)
                    clean = re.sub(r"\s*\(計算パターン\d+\)", "", clean)
                    clean = re.sub(r"\s*\(計算シミュレーション\d+\)", "", clean)
                    return clean.strip()

                temp_pool["core_theme"] = temp_pool["question"].apply(get_core_theme)
                unique_themes = temp_pool["core_theme"].unique().tolist()
                random.shuffle(unique_themes)
                
                chosen_themes = unique_themes[:num_questions]
                for theme in chosen_themes:
                    sub_df = temp_pool[temp_pool["core_theme"] == theme]
                    chosen_rows.append(sub_df.sample(n=1))
                    
                if chosen_rows:
                    final_quiz_df = pd.concat(chosen_rows).reset_index(drop=True)
                    st.session_state.current_quiz = final_quiz_df.sample(frac=1).reset_index(drop=True)
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.session_state.last_system_msg = "テスト生成完了"
                    st.rerun()
                else:
                    st.warning("問題の抽出に失敗しました。出題数を調整してください。")
            
        if "current_quiz" in st.session_state:
            st.markdown("---")
            
            if st.session_state.get("exam_mode") and not st.session_state.get("submitted", False):
                elapsed = time.time() - st.session_state.start_time
                remaining = st.session_state.time_limit - elapsed
                
                if remaining <= 0:
                    st.warning("⏰ 制限時間が終了しました！自動的に採点を行います。")
                    st.session_state.submitted = True
                    st.rerun()
                
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                
                st.markdown(
                    f"""
                    <style>
                        header {{visibility: visible;}}
                        #fixed-timer-bar {{
                            position: fixed !important;
                            top: 0 !important;
                            left: 0 !important;
                            width: 100vw !important;
                            background-color: #111111 !important;
                            border-bottom: 3px solid #ff4b4b !important;
                            padding: 14px 0 !important;
                            z-index: 999999 !important;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.7) !important;
                            text-align: center !important;
                        }}
                    </style>
                    <div id="fixed-timer-bar">
                        <span style="font-size: 22px; font-weight: bold; color: #ff4b4b; letter-spacing: 1px;">
                            ⏱️ 本番模試 残り時間: {mins:02d}分 {secs:02d}秒
                        </span>
                    </div>
                    <div style="height: 50px;"></div>
                    """,
                    unsafe_allow_html=True
                )
            
            st.subheader("📝 テスト実施中")
            
            quiz_df = st.session_state.current_quiz
            if "user_answers" not in st.session_state:
                st.session_state.user_answers = {}
            
            for idx, row in quiz_df.iterrows():
                raw_q = str(row['question'])
                cleaned_q = re.sub(r"【第\d+問】\s*", "", raw_q)
                cleaned_q = re.sub(r"【事例\d+-\d+】\s*", "", cleaned_q)
                cleaned_q = re.sub(r"【追加事例\d+】\s*", "", cleaned_q)
                cleaned_q = re.sub(r"\s*\(V\d+\)", "", cleaned_q)
                cleaned_q = re.sub(r"\s*\(パターン\d+\)", "", cleaned_q)
                cleaned_q = re.sub(r"\s*\(計算パターン\d+\)", "", cleaned_q)
                cleaned_q = re.sub(r"\s*\(計算シミュレーション\d+\)", "", cleaned_q)
                
                st.markdown(f"**Q{idx+1}. [{row['category']}] {cleaned_q}**")
                opts = [row["option_a"], row["option_b"], row["option_c"]]
                
                current_val = st.session_state.user_answers.get(idx, None)
                
                choice = st.radio(
                    f"選択肢 (Q{idx+1})",
                    options=[0, 1, 2],
                    format_func=lambda x: opts[x],
                    index=current_val,
                    key=f"q_{idx}"
                )
                st.session_state.user_answers[idx] = choice
                st.markdown("---")
                
            btn_label = "🏁 テスト終了して採点する" if st.session_state.get("exam_mode") else "回答を提出して採点する"
            if st.button(btn_label, key="submit_quiz_btn"):
                unanswered = [i+1 for i in range(len(quiz_df)) if st.session_state.user_answers.get(i) is None]
                if unanswered and not st.session_state.get("exam_mode"):
                    st.warning(f"未回答の問題があります (Q{', '.join(map(str, unanswered))})。すべての問題に回答してください！")
                else:
                    score = 0
                    total = len(quiz_df)
                    
                    session_results = {}
                    current_incorrect_indices = []
                    
                    for idx, row in quiz_df.iterrows():
                        cat = row["category"]
                        user_ans = st.session_state.user_answers.get(idx)
                        correct_ans = int(row["correct"])
                        
                        orig_idx = df_questions[df_questions["question"] == row["question"]].index
                        orig_idx_val = orig_idx[0] if len(orig_idx) > 0 else None

                        if user_ans == correct_ans:
                            score += 1
                        else:
                            if orig_idx_val is not None:
                                current_incorrect_indices.append(orig_idx_val)

                        if cat not in session_results:
                            session_results[cat] = {"total": 0, "correct": 0}
                        session_results[cat]["total"] += 1
                        if user_ans == correct_ans:
                            session_results[cat]["correct"] += 1
                    
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    storage = st.session_state.app_storage
                    
                    if "incorrect_pool" not in storage:
                        storage["incorrect_pool"] = {}
                    if current_user not in storage["incorrect_pool"]:
                        storage["incorrect_pool"][current_user] = []
                    
                    user_inc_list = storage["incorrect_pool"][current_user]
                    if st.session_state.get("is_review_mode"):
                        for idx, row in quiz_df.iterrows():
                            orig_idx = df_questions[df_questions["question"] == row["question"]].index
                            if len(orig_idx) > 0:
                                o_val = orig_idx[0]
                                user_ans = st.session_state.user_answers.get(idx)
                                correct_ans = int(row["correct"])
                                if user_ans == correct_ans and o_val in user_inc_list:
                                    user_inc_list.remove(o_val)
                    else:
                        for inc_idx in current_incorrect_indices:
                            if inc_idx not in user_inc_list:
                                user_inc_list.append(inc_idx)
                    
                    test_name_label = "練習・カテゴリー演習" if not st.session_state.get("exam_mode") else st.session_state.exam_mode["name"]
                    new_record = {
                        "timestamp": now_str,
                        "user_email": current_user,
                        "exam_type": test_name_label,
                        "score": score,
                        "total": total,
                        "rate": round((score / total * 100), 1) if total > 0 else 0,
                        "passed": (score / total >= 0.8) if total > 0 else False
                    }
                    if "exam_history" not in storage:
                        storage["exam_history"] = []
                    storage["exam_history"].append(new_record)
                    
                    if not st.session_state.get("exam_mode"):
                        if "category_stats" not in storage:
                            storage["category_stats"] = {}
                        if current_user not in storage["category_stats"]:
                            storage["category_stats"][current_user] = {}
                            
                        user_cat_stats = storage["category_stats"][current_user]
                        for cat, res in session_results.items():
                            if cat not in user_cat_stats:
                                user_cat_stats[cat] = {"total": 0, "correct": 0, "last_total": 0, "last_correct": 0}
                            
                            user_cat_stats[cat]["last_total"] = res["total"]
                            user_cat_stats[cat]["last_correct"] = res["correct"]
                            user_cat_stats[cat]["total"] += res["total"]
                            user_cat_stats[cat]["correct"] += res["correct"]
                        
                        save_exam_results(storage)
                    else:
                        save_exam_results(storage)

                    st.session_state.submitted = True
                    st.session_state.last_system_msg = "採点完了"
                    st.rerun()
                    
            if st.session_state.get("submitted", False):
                st.subheader("🎯 採点結果 & 詳細解説")
                score = 0
                total = len(quiz_df)
                
                for idx, row in quiz_df.iterrows():
                    user_ans = st.session_state.user_answers.get(idx)
                    correct_ans = int(row["correct"])
                    is_correct = (user_ans == correct_ans)
                    
                    if is_correct:
                        score += 1
                        st.success(f"Q{idx+1}: 正解！ 🎉")
                    else:
                        st.error(f"Q{idx+1}: 不正解... ❌ (弱点克服モードに登録されました)")
                        
                    opt_list = [row["option_a"], row["option_b"], row["option_c"]]
                    user_ans_text = opt_list[user_ans] if user_ans is not None else "未回答"
                    st.write(f"あなたの回答: {user_ans_text}")
                    st.write(f"正解: {opt_list[correct_ans]}")
                    
                    with st.expander("📖 詳しい解説・計算プロセスを見る"):
                        st.markdown(row["explanation"])
                    st.markdown("---")
                
                rate = int(score / total * 100) if total > 0 else 0
                
                if st.session_state.get("exam_mode"):
                    config = st.session_state.exam_mode
                    passed = rate >= config["pass_rate"]
                    if passed:
                        st.balloons()
                        st.success(f"🏆 **合否判定: 合格です！おめでとうございます！** (正答率 {rate}% / 基準 {config['pass_rate']}%以上)")
                    else:
                        st.error(f"💥 **合否判定: 不合格です。** (正答率 {rate}% / 基準 {config['pass_rate']}%以上が必要です)")
                
                st.metric(label="総合スコア", value=f"{score} / {total} 問正解 ({rate}%)")
            
            if st.session_state.get("exam_mode") and not st.session_state.get("submitted", False):
                time.sleep(1)
                st.rerun()

    except Exception as e:
        st.session_state.last_system_msg = f"例外発生: {str(e)[:25]}"

# ------------------------------------------
# モードC: 管理者ダッシュボード
# ------------------------------------------
elif app_mode == "🛠️ 管理者ダッシュボード":
    if not is_admin:
        st.error("🔒 この画面にアクセスする権限がありません。")
        st.stop()
        
    st.title("🛠️ 管理者ダッシュボード")
    st.write("システム全体の管理、メンバーの利用状況確認、問題データ更新、および管理者権限の管理を行います。")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👑 管理者権限", "👥 会員リスト管理", "👥 会員認証状況", "📊 データ・システム情報", "⚙️ 成績・問題データ管理"])
    
    with tab1:
        st.subheader("👑 管理者ユーザーの追加・削除・名前編集")
        st.write("新しい管理者を追加したり、登録名の変更、既存の管理者権限の解除を行えます。")
        
        new_admin_input = st.text_input("追加する管理者のメールアドレス", placeholder="new_admin@example.com", key="new_admin_email_input")
        new_admin_name = st.text_input("追加する管理者の氏名（表示名）", placeholder="山田 太郎", key="new_admin_name_input")
        
        if st.button("管理者として追加する", key="add_admin_btn"):
            email_clean = new_admin_input.strip().lower()
            name_clean = new_admin_name.strip()
            if email_clean and "@" in email_clean:
                if email_clean not in admins_dict:
                    admins_dict[email_clean] = {"role": "admin", "appointed_by": current_user, "name": name_clean}
                    save_admins(admins_dict)
                    st.success(f"🎉 `{email_clean}` ({name_clean}) を管理者に追加しました！")
                    st.rerun()
                else:
                    st.warning("すでに管理者に登録されているメールアドレスです。")
            else:
                st.warning("有効なメールアドレスを入力してください。")
                
        st.markdown("---")
        st.write("**現在の登録管理者一覧 & 氏名編集:**")
        
        can_remove_admins = (current_user == MASTER_ADMIN) or (admins_dict.get(current_user, {}).get("appointed_by") == MASTER_ADMIN)
        
        for adm, info in admins_dict.items():
            adm_name = info.get("name", "")
            role = info.get("role", "admin")
            
            with st.container():
                col_n1, col_n2, col_n3 = st.columns([3, 2, 1])
                col_n1.write(f"📧 `{adm}` {'*(マスター)*' if role == 'master' else ''}")
                
                updated_name = col_n2.text_input(f"氏名 ({adm})", value=adm_name, key=f"name_input_{adm}", label_visibility="collapsed")
                if updated_name != adm_name:
                    admins_dict[adm]["name"] = updated_name
                    save_admins(admins_dict)
                    st.success("氏名を更新しました！")
                    st.rerun()
                
                if can_remove_admins and adm != current_user and role != "master":
                    # --- 安全確認用チェックボックスを追加 ---
                    confirm_del_adm = col_n3.checkbox("削除確認", key=f"chk_adm_{adm}")
                    if confirm_del_adm:
                        if col_n3.button("権限解除", key=f"del_adm_{adm}"):
                            del admins_dict[adm]
                            save_admins(admins_dict)
                            st.success(f"`{adm}` の管理者権限を解除しました。")
                            st.rerun()
                else:
                    col_n3.write("")
            st.markdown("---")

    with tab2:
        st.subheader("👥 協会員の追加・一括登録・管理")
        st.write("個別追加のほか、ヘッダー（列名）のない名簿ファイル（1列目：氏名、2列目：メールアドレスなど）や通常のエクセル・CSVファイルをアップロードして一括登録できます。")
        
        # --- 一括アップロード機能（ヘッダーなし・あり両対応） ---
        st.markdown("#### 📂 会員名簿ファイルの一括アップロード")
        member_uploaded_file = st.file_uploader("ExcelまたはCSVファイルをアップロード", type=["xlsx", "csv"], key="member_file_uploader")
        
        if member_uploaded_file is not None:
            try:
                if member_uploaded_file.name.endswith(".csv"):
                    df_upload = pd.read_csv(member_uploaded_file, header=None)
                else:
                    df_upload = pd.read_excel(member_uploaded_file, header=None)
                
                added_count = 0
                for _, row in df_upload.iterrows():
                    row_vals = [str(val).strip() for val in row.values if pd.notna(val)]
                    email_val = None
                    name_val = ""
                    
                    for idx, val in enumerate(row_vals):
                        val_low = val.lower()
                        if "@" in val_low and "." in val_low and " " not in val_low:
                            email_val = val_low
                            if idx > 0 and not ("@" in row_vals[idx-1]):
                                name_val = row_vals[idx-1]
                            break
                    
                    if email_val:
                        if not name_val or name_val.lower() == "nan":
                            name_val = email_val
                        if email_val not in email_to_name:
                            added_count += 1
                        email_to_name[email_val] = name_val
                
                if added_count > 0 or len(email_to_name) > 1:
                    save_association_members_json(email_to_name)
                    st.success(f"🎉 ファイルから新たに **{added_count}名** の会員を追加しました！（総登録数: {len(email_to_name)}名）")
                    if st.button("🔄 画面を更新する", key="reload_members_upload"):
                        st.rerun()
                else:
                    st.error("❌ アップロードされたファイルから有効なメールアドレスが見つかりませんでした。ファイルの内容をご確認ください。")
            except Exception as e:
                st.error(f"ファイル読込エラー: {e}")

        st.markdown("---")
        st.markdown("#### 👤 個別追加登録")
        new_member_email = st.text_input("追加する会員のメールアドレス", placeholder="member@example.com", key="new_member_email_input")
        new_member_name = st.text_input("追加する会員の氏名（表示名）", placeholder="鈴木 一郎", key="new_member_name_input")
        
        if st.button("協会員として登録する", key="add_member_btn"):
            m_email_clean = new_member_email.strip().lower()
            m_name_clean = new_member_name.strip()
            if m_email_clean and "@" in m_email_clean:
                if m_email_clean not in email_to_name:
                    email_to_name[m_email_clean] = m_name_clean if m_name_clean else m_name_clean
                    save_association_members_json(email_to_name)
                    st.success(f"🎉 協会員 `{m_email_clean}` を登録しました！")
                    st.rerun()
                else:
                    st.warning("すでに登録されているメールアドレスです。")
            else:
                st.warning("有効なメールアドレスを入力してください。")
                
        st.markdown("---")
        st.write("**現在の登録協会員一覧:**")
        
        for mem_email, mem_name in list(email_to_name.items()):
            with st.container():
                col_m1, col_m2, col_m3 = st.columns([3, 2, 1])
                col_m1.write(f"📧 `{mem_email}`")
                
                up_m_name = col_m2.text_input(f"氏名 ({mem_email})", value=mem_name, key=f"mem_name_{mem_email}", label_visibility="collapsed")
                if up_m_name != mem_name:
                    email_to_name[mem_email] = up_m_name
                    save_association_members_json(email_to_name)
                    st.success("会員名を更新しました！")
                    st.rerun()
                
                if mem_email != MASTER_ADMIN:
                    # --- 安全確認用チェックボックスを追加 ---
                    confirm_del_mem = col_m3.checkbox("削除確認", key=f"chk_mem_{mem_email}")
                    if confirm_del_mem:
                        if col_m3.button("削除", key=f"del_mem_{mem_email}"):
                            del email_to_name[mem_email]
                            save_association_members_json(email_to_name)
                            st.success(f"`{mem_email}` を会員リストから削除しました。")
                            st.rerun()
                else:
                    col_m3.write("*(マスター)*")
            st.markdown("---")

    with tab3:
        st.subheader("👥 協会会員のアプリ利用状況・認証状況（詳細履歴付き）")
        st.write(f"マスター管理者: `{MASTER_ADMIN}`")
        
        storage_data = st.session_state.app_storage
        all_history = storage_data.get("exam_history", [])
        activity_history = storage_data.get("activity_history", [])
        
        user_exams_map = {}
        for h in all_history:
            u_email = h.get("user_email")
            if u_email not in user_exams_map:
                user_exams_map[u_email] = []
            user_exams_map[u_email].append(h)
            
        user_logins_map = {}
        for act in activity_history:
            u_email = act.get("user_email")
            if u_email not in user_logins_map:
                user_logins_map[u_email] = []
            user_logins_map[u_email].append(act.get("timestamp"))

        total_members_count = len(member_emails)
        active_users_set = set(user_exams_map.keys()).union(set(user_logins_map.keys())).union(set(registered_admins))
        logged_in_count = sum(1 for m in member_emails if m in active_users_set)
        
        col_st1, col_st2, col_st3 = st.columns(3)
        col_st1.metric("総登録会員数", f"{total_members_count} 名")
        col_st2.metric("アプリ利用（ログイン済）", f"{logged_in_count} 名")
        col_st3.metric("未ログイン", f"{total_members_count - logged_in_count} 名")
        
        st.markdown("---")
        st.write("**📋 全会員の利用状況・直近のテスト受験履歴（過去2回分）:**")
        
        member_status_list = []
        for m_email in member_emails:
            m_name = email_to_name.get(m_email, "登録名なし")
            is_active = m_email in active_users_set or m_email == current_user
            status_str = "✅ ログイン済" if is_active else "⏳ 未ログイン"
            
            u_hist = user_exams_map.get(m_email, [])
            u_hist_sorted = sorted(u_hist, key=lambda x: x.get("timestamp", ""), reverse=True)
            
            recent_2 = u_hist_sorted[:2]
            
            history_str_1 = f"1回前: {recent_2[0]['timestamp']} ({recent_2[0]['exam_type']} / 正答率: {recent_2[0]['rate']}%)" if len(recent_2) > 0 else "履歴なし"
            history_str_2 = f"2回前: {recent_2[1]['timestamp']} ({recent_2[1]['exam_type']} / 正答率: {recent_2[1]['rate']}%)" if len(recent_2) > 1 else "-"
            
            member_status_list.append({
                "氏名": m_name,
                "メールアドレス": m_email,
                "ステータス": status_str,
                "直近の受験① (最新)": history_str_1,
                "直近の受験②": history_str_2
            })
            
        df_member_status = pd.DataFrame(member_status_list)
        status_table_height = (len(df_member_status) + 1) * 40 + 10
        st.dataframe(df_member_status, use_container_width=True, hide_index=True, height=status_table_height)

    with tab4:
        st.subheader("📊 登録ユーザー別 成績レポート")
        
        storage = st.session_state.app_storage
        history = storage.get("exam_history", [])
        cat_stats_all = storage.get("category_stats", {})
        
        known_users = list(set(
            [h["user_email"] for h in history] + 
            list(cat_stats_all.keys()) + 
            [current_user] + 
            member_emails
        ))
        unique_users = sorted([u for u in known_users if u])
        
        if unique_users:
            user_options = {get_user_display_name(u, email_to_name, admins_dict): u for u in unique_users}
            
            # --- 【最上部配置】ユーザー検索とユーザー選択 ---
            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                search_query_tab4 = st.text_input("🔍 ユーザー検索（氏名・メール）", placeholder="例: 内藤 または gmail", key="search_user_tab4")
            
            filtered_options = {d_name: u_email for d_name, u_email in user_options.items() if search_query_tab4.lower() in d_name.lower() or search_query_tab4.lower() in u_email.lower()}
            if not filtered_options:
                filtered_options = user_options
                
            with col_f2:
                selected_display_name = st.selectbox("ユーザーを選択", list(filtered_options.keys()), key="report_user_sel_tab4")
            
            selected_user = filtered_options[selected_display_name]
            
            st.markdown("---")
            
            # --- 【すぐ下の段】データ・システム情報（カテゴリー別＆模試レポート） ---
            st.subheader(f"📁 【{selected_display_name}】のカテゴリー別成績一覧（今回 ＆ 平均）")
            categories = df_questions["category"].unique()
            user_cat_data = cat_stats_all.get(selected_user, {})
            
            summary_data = []
            for cat in categories:
                stats = user_cat_data.get(cat, {"total": 0, "correct": 0, "last_total": 0, "last_correct": 0})
                l_total = stats["last_total"]
                l_correct = stats["last_correct"]
                last_rate = f"{(l_correct / l_total * 100):.1f}% ({l_correct}/{l_total})" if l_total > 0 else "未実施"
                
                acc_total = stats["total"]
                acc_correct = stats["correct"]
                avg_rate = f"{(acc_correct / acc_total * 100):.1f}% ({acc_correct}/{acc_total})" if acc_total > 0 else "未実施"
                
                summary_data.append({
                    "カテゴリー": cat,
                    "今回の正解率": last_rate,
                    "平均正解率（累計）": avg_rate
                })
            
            summary_df = pd.DataFrame(summary_data)
            table_height = (len(summary_df) + 1) * 35 + 10
            st.dataframe(summary_df, use_container_width=True, hide_index=True, height=table_height)
            
            st.markdown("---")
            
            st.subheader(f"🎯 【{selected_display_name}】の本番模試 成績レポート")
            exam_type_choice_admin = st.selectbox("表示する模試種別を選択", ["二等 本番模擬試験", "一等 本番模擬試験"], key="admin_exam_type_sel")
            
            user_history = [h for h in history if h["user_email"] == selected_user and exam_type_choice_admin in h.get("exam_type", "")]
            
            if user_history:
                u_df = pd.DataFrame(user_history)
                u_df.columns = ["受験日時", "受験者メール", "模試の種類", "正解数", "総問題数", "正答率(%)", "合否"]
                u_df["受験者名"] = selected_display_name
                u_df = u_df[["受験日時", "受験者名", "模試の種類", "正解数", "総問題数", "正答率(%)", "合否"]]
                u_df["合否"] = u_df["合否"].apply(lambda x: "合格 🏆" if x else "不合格 💥")
                
                total_attempts = len(user_history)
                passed_count = sum(1 for h in user_history if h["passed"])
                avg_rate = sum(h["rate"] for h in user_history) / total_attempts if total_attempts > 0 else 0
                
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("総受験回数", f"{total_attempts} 回")
                col_s2.metric("合格回数", f"{passed_count} 回")
                col_s3.metric("平均正解率", f"{avg_rate:.1f}%")
                
                st.markdown("---")
                st.write(f"**【{selected_display_name}】の{exam_type_choice_admin} 受験履歴一覧**")
                u_table_height = (len(u_df) + 1) * 35 + 10
                st.dataframe(u_df, use_container_width=True, hide_index=True, height=u_table_height)
            else:
                st.info(f"【{selected_display_name}】の「{exam_type_choice_admin}」の受験履歴はまだありません。")
        else:
            st.info("登録されているユーザーがありません。")

    with tab5:
        st.subheader("⚙️ 成績データの個別管理 & 問題データExcel更新・バックアップ")
        
        # --- データバックアップ（エクスポート・インポート）機能 ---
        st.markdown("#### 💾 JSONデータ（成績・会員名簿）のバックアップ & 復元")
        st.write("システムで蓄積された成績データや会員名簿のJSONファイルをダウンロードしてバックアップしたり、別の環境から復元できます。")
        
        col_bk1, col_bk2 = st.columns(2)
        with col_bk1:
            if os.path.exists(RESULTS_JSON_FILE):
                with open(RESULTS_JSON_FILE, "r", encoding="utf-8") as f:
                    results_json_str = f.read()
                st.download_button(
                    label="📥 成績データ（exam_results.json）をダウンロード",
                    data=results_json_str,
                    file_name="exam_results_backup.json",
                    mime="application/json"
                )
        with col_bk2:
            if os.path.exists(MEMBERS_JSON_FILE):
                with open(MEMBERS_JSON_FILE, "r", encoding="utf-8") as f:
                    members_json_str = f.read()
                st.download_button(
                    label="📥 会員名簿（members.json）をダウンロード",
                    data=members_json_str,
                    file_name="members_backup.json",
                    mime="application/json"
                )
                
        uploaded_backup = st.file_uploader("バックアップJSONファイルをアップロードして復元", type=["json"], key="backup_json_uploader")
        if uploaded_backup is not None:
            try:
                backup_data = json.load(uploaded_backup)
                if "exam_history" in backup_data or "category_stats" in backup_data:
                    with open(RESULTS_JSON_FILE, "w", encoding="utf-8") as f:
                        json.dump(backup_data, f, ensure_ascii=False, indent=2)
                    st.success("🎉 成績データ（exam_results.json）を正常に復元しました！画面を再読込してください。")
                else:
                    with open(MEMBERS_JSON_FILE, "w", encoding="utf-8") as f:
                        json.dump(backup_data, f, ensure_ascii=False, indent=2)
                    st.success("🎉 会員名簿（members.json）を正常に復元しました！画面を再読込してください。")
                if st.button("🔄 アプリを再読込する", key="reload_backup_btn"):
                    st.rerun()
            except Exception as e:
                st.error(f"復元エラー: {e}")

        st.markdown("---")

        # --- 長文事例・計算問題のデータ更新フロー・説明 ---
        st.markdown("#### 📂 問題データ（Excel）の更新フロー & 長文事例・計算問題の管理")
        st.write(f"現在の問題データファイル: `{EXCEL_FILENAME}`")
        st.info(
            "💡 **長文事例・計算問題のアップデート手順**:\n"
            "1. 新規の問題や長文事例、計算パターンを追加・編集したExcelファイル（`drone_exam_questions_detailed_calc.xlsx`）を用意します。\n"
            "2. 下部のアップロード欄からファイルをアップロードすると、一等・二等の各分野演習、計算問題、長文事例のプールが即座に最新状態に反映されます。"
        )
        
        uploaded_file = st.file_uploader("新しい問題データ（Excel .xlsx）をアップロード", type=["xlsx"], key="excel_uploader")
        if uploaded_file is not None:
            try:
                with open(EXCEL_FILENAME, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("🎉 問題データ（Excel）を正常に更新しました！画面を再読込してください。")
                if st.button("🔄 アプリを再読込する", key="reload_app_btn"):
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"ファイル保存エラー: {e}")
                
        st.markdown("---")
        
        storage = st.session_state.app_storage
        
        # --- 全データリセットにも安全確認用チェックボックスを追加 ---
        if st.checkbox("⚙️ 高度な操作：すべての成績・受験履歴を完全に初期化する", key="show_reset_all_chk"):
            st.warning("⚠️ この操作を行うと、本番模試の履歴だけでなく、**すべてのユーザーのカテゴリー別成績データおよび弱点克服プールのストックが完全に削除**されます。")
            confirm_reset_all = st.checkbox("本当にすべての成績データを初期化する（確認チェック）", key="confirm_reset_all_chk")
            if confirm_reset_all:
                if st.button("🚨 【完全リセット実行】すべての成績データを初期化する", key="reset_all_data_btn"):
                    storage["exam_history"] = []
                    storage["category_stats"] = {}
                    storage["incorrect_pool"] = {}
                    storage["activity_history"] = []
                    save_exam_results(storage)
                    st.success("すべての成績データを完全にリセットしました！")
                    st.rerun()