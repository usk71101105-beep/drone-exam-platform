import streamlit as st
import pandas as pd
import json
import os
import random
import re
import time
import base64
import requests
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
# 2. GitHub自動同期 & 永続化・バックアップ管理
# ==========================================
MASTER_ADMIN = "usk71101105@gmail.com"
RESULTS_JSON_FILE = "exam_results.json"
ADMINS_JSON_FILE = "admins.json"
MEMBERS_JSON_FILE = "members.json"
BACKUP_JSON_FILE = "deleted_backup_history.json"
EXCEL_FILENAME = "drone_exam_questions_detailed_calc.xlsx"

# GitHub Secretsから認証情報を取得（未設定の場合はローカル動作）
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GITHUB_REPO = st.secrets.get("GITHUB_REPO", os.environ.get("GITHUB_REPO", "usk71101105-beep/drone-exam-platform"))

def commit_to_github(file_path, file_content_str, commit_message):
    """アプリ上で変更されたJSONファイルをGitHubへ自動コミットする関数"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    sha = None
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            sha = res.json().get("sha")
    except:
        pass
        
    content_encoded = base64.b64encode(file_content_str.encode("utf-8")).decode("utf-8")
    
    data = {
        "message": commit_message,
        "content": content_encoded,
        "sha": sha
    }
    try:
        res = requests.put(url, headers=headers, json=data)
        return res.status_code in [200, 201]
    except:
        return False

def save_to_deleted_backup(item_type, target_id, target_data):
    backup_data = {"deleted_history": []}
    if os.path.exists(BACKUP_JSON_FILE):
        try:
            with open(BACKUP_JSON_FILE, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
        except:
            pass
            
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    backup_data["deleted_history"].append({
        "timestamp": now_str,
        "type": item_type,
        "target_id": target_id,
        "data": target_data
    })
    
    backup_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
    with open(BACKUP_JSON_FILE, "w", encoding="utf-8") as f:
        f.write(backup_str)
        
    commit_to_github(BACKUP_JSON_FILE, backup_str, f"Backup deleted {item_type}: {target_id}")

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
    content_str = json.dumps(admins_dict, ensure_ascii=False, indent=2)
    with open(ADMINS_JSON_FILE, "w", encoding="utf-8") as f:
        f.write(content_str)
    commit_to_github(ADMINS_JSON_FILE, content_str, "Auto-update admins.json from app")

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
    content_str = json.dumps(members_dict, ensure_ascii=False, indent=2)
    with open(MEMBERS_JSON_FILE, "w", encoding="utf-8") as f:
        f.write(content_str)
    commit_to_github(MEMBERS_JSON_FILE, content_str, "Auto-update members.json from app")

def get_user_display_name(email, email_to_name, admins_dict):
    e_low = email.strip().lower()
    if e_low in admins_dict and admins_dict[e_low].get("name"):
        return admins_dict[e_low]["name"]
    return email_to_name.get(e_low, email)

def load_exam_results():
    if os.path.exists(RESULTS_JSON_FILE):
        try:
            with open(RESULTS_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "activity_history" not in data:
                        data["activity_history"] = []
                    if "logged_in_users" not in data:
                        data["logged_in_users"] = []
                    return data
                elif isinstance(data, list):
                    return {"exam_history": data, "category_stats": {}, "incorrect_pool": {}, "activity_history": [], "logged_in_users": []}
        except:
            pass
    return {"exam_history": [], "category_stats": {}, "incorrect_pool": {}, "activity_history": [], "logged_in_users": []}

def save_exam_results(data):
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(RESULTS_JSON_FILE, "w", encoding="utf-8") as f:
        f.write(content_str)
    commit_to_github(RESULTS_JSON_FILE, content_str, "Auto-update exam_results.json from app")

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
# 4. 認証・ログイン状態の管理
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

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
                if "logged_in_users" not in storage:
                    storage["logged_in_users"] = []
                
                if input_email not in storage["logged_in_users"]:
                    storage["logged_in_users"].append(input_email)
                
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

storage_init = st.session_state.app_storage
if "logged_in_users" not in storage_init:
    storage_init["logged_in_users"] = []
if current_user not in storage_init["logged_in_users"]:
    storage_init["logged_in_users"].append(current_user)
    save_exam_results(storage_init)

st.sidebar.write(f"👤 ログイン中: `{current_user_name}`")
if is_admin:
    st.sidebar.markdown("🛠️ **【管理者権限】**")

# ==========================================
# サイドバー: 成績確認
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
        st.write("一等・二等の各分野演習、長文事例問題、本番模試、および間違えた問題を克服する**弱点克服モード**に挑戦できます。")
        
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

        exam_course = st.radio("受験する試験コースを選択してください", exam_course_options, key="exam_course_radio")
        
        two_categories = [
            "【二等】分野1：規則", "【二等】分野2：システム", "【二等】分野3：操縦者",
            "【二等】分野4：リスク管理", "【二等】計算問題・バッテリー", "【二等】長文事例"
        ]
        
        is_official_exam = "【本番模試】" in exam_course
        
        if is_official_exam:
            if "二等" in exam_course:
                target_df = df_questions[df_questions["category"].isin(two_categories)].reset_index(drop=True)
                exam_config = {"count": 50, "time_min": 30, "pass_rate": 80, "name": "二等 本番模擬試験"}
            else:
                target_df = df_questions.copy().reset_index(drop=True)
                exam_config = {"count": 70, "time_min": 75, "pass_rate": 90, "name": "一等 本番模擬試験"}
            
            st.warning(f"⚠️ **{exam_config['name']}モード**：制限時間 **{exam_config['time_min']}分** / 出題数 **{exam_config['count']}問** / 合格基準 **正答率 {exam_config['pass_rate']}%以上**")
            
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
                    st.error("問題の抽出に失敗しました。")

        else:
            if "二等" in exam_course:
                target_df = df_questions[df_questions["category"].isin(two_categories)].reset_index(drop=True)
            else:
                target_df = df_questions.copy().reset_index(drop=True)
            
            st.markdown("---")
            test_type = st.radio("出題方法を選択", ["特定カテゴリーから出題", "コース全体からランダム総合模試"], horizontal=True, key="test_type_radio")
            
            if test_type == "特定カテゴリーから出題":
                available_cats = target_df["category"].unique().tolist()
                selected_category = st.selectbox("出題カテゴリーを選択してください", available_cats, key="cat_select")
                current_pool = target_df[target_df["category"] == selected_category].reset_index(drop=True)
            else:
                current_pool = target_df
                
            num_questions = st.slider("出題数を選択", min_value=5, max_value=min(30, len(current_pool)), value=10, key="num_q_slider")
            
            if st.button("テストを開始する", key="start_practice_btn"):
                reset_quiz_state()
                temp_pool = current_pool.copy()
                chosen_rows = []
                
                def get_core_theme(q_text):
                    clean = re.sub(r"【第\d+問】\s*", "", q_text)
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
            
        if "current_quiz" in st.session_state:
            st.markdown("---")
            if st.session_state.get("exam_mode") and not st.session_state.get("submitted", False):
                elapsed = time.time() - st.session_state.start_time
                remaining = st.session_state.time_limit - elapsed
                if remaining <= 0:
                    st.warning("⏰ 制限時間が終了しました！自動採点します。")
                    st.session_state.submitted = True
                    st.rerun()
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                st.markdown(f"### ⏱️ 残り時間: {mins:02d}分 {secs:02d}秒")
            
            st.subheader("📝 テスト実施中")
            quiz_df = st.session_state.current_quiz
            if "user_answers" not in st.session_state:
                st.session_state.user_answers = {}
            
            for idx, row in quiz_df.iterrows():
                raw_q = str(row['question'])
                cleaned_q = re.sub(r"【第\d+問】\s*", "", raw_q)
                st.markdown(f"**Q{idx+1}. [{row['category']}] {cleaned_q}**")
                opts = [row["option_a"], row["option_b"], row["option_c"]]
                current_val = st.session_state.user_answers.get(idx, None)
                
                choice = st.radio(f"選択肢 (Q{idx+1})", options=[0, 1, 2], format_func=lambda x: opts[x], index=current_val, key=f"q_{idx}")
                st.session_state.user_answers[idx] = choice
                st.markdown("---")
                
            btn_label = "🏁 テスト終了して採点する" if st.session_state.get("exam_mode") else "回答を提出して採点する"
            if st.button(btn_label, key="submit_quiz_btn"):
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
                            if st.session_state.user_answers.get(idx) == int(row["correct"]) and o_val in user_inc_list:
                                user_inc_list.remove(o_val)
                else:
                    for inc_idx in current_incorrect_indices:
                        if inc_idx not in user_inc_list:
                            user_inc_list.append(inc_idx)
                
                test_name_label = "練習・カテゴリー演習" if not st.session_state.get("exam_mode") else st.session_state.exam_mode["name"]
                new_record = {
                    "timestamp": now_str, "user_email": current_user, "exam_type": test_name_label,
                    "score": score, "total": total, "rate": round((score / total * 100), 1) if total > 0 else 0,
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
                st.session_state.submitted = True
                st.rerun()
                
            if st.session_state.get("submitted", False):
                st.subheader("🎯 採点結果 & 詳細解説")
                score = 0
                total = len(quiz_df)
                for idx, row in quiz_df.iterrows():
                    user_ans = st.session_state.user_answers.get(idx)
                    correct_ans = int(row["correct"])
                    if user_ans == correct_ans:
                        score += 1
                        st.success(f"Q{idx+1}: 正解！")
                    else:
                        st.error(f"Q{idx+1}: 不正解... (弱点克服モードに登録)")
                    opt_list = [row["option_a"], row["option_b"], row["option_c"]]
                    st.write(f"あなたの回答: {opt_list[user_ans] if user_ans is not None else '未回答'} / 正解: {opt_list[correct_ans]}")
                    with st.expander("📖 解説"):
                        st.markdown(row["explanation"])
                    st.markdown("---")
                rate = int(score / total * 100) if total > 0 else 0
                st.metric(label="総合スコア", value=f"{score} / {total} 問正解 ({rate}%)")

    except Exception as e:
        st.session_state.last_system_msg = f"例外: {str(e)[:25]}"

# ------------------------------------------
# モードB: 管理者ダッシュボード
# ------------------------------------------
elif app_mode == "🛠️ 管理者ダッシュボード":
    if not is_admin:
        st.error("🔒 権限がありません。")
        st.stop()
        
    st.title("🛠️ 管理者ダッシュボード")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👑 管理者権限", "👥 会員リスト管理", "👥 会員認証状況", "📊 成績レポート", "⚙️ データ管理", "🗄️ 削除バックアップ確認"
    ])
    
    with tab1:
        st.subheader("👑 管理者ユーザーの追加・削除・名前編集")
        new_admin_input = st.text_input("追加する管理者のメールアドレス", key="new_admin_email_input")
        new_admin_name = st.text_input("追加する管理者の氏名", key="new_admin_name_input")
        
        if st.button("管理者として追加する", key="add_admin_btn"):
            email_clean = new_admin_input.strip().lower()
            name_clean = new_admin_name.strip()
            if email_clean and "@" in email_clean:
                if email_clean not in admins_dict:
                    admins_dict[email_clean] = {"role": "admin", "appointed_by": current_user, "name": name_clean}
                    save_admins(admins_dict)
                    st.success(f"🎉 `{email_clean}` を管理者に追加し、GitHubに自動同期しました！")
                    st.rerun()
                else:
                    st.warning("すでに登録されています。")
            else:
                st.warning("有効なメールアドレスを入力してください。")
                
        st.markdown("---")
        can_remove_admins = (current_user == MASTER_ADMIN) or (admins_dict.get(current_user, {}).get("appointed_by") == MASTER_ADMIN)
        for adm, info in admins_dict.items():
            adm_name = info.get("name", "")
            role = info.get("role", "admin")
            col_n1, col_n2, col_n3 = st.columns([3, 2, 1])
            col_n1.write(f"📧 `{adm}` {'*(マスター)*' if role == 'master' else ''}")
            updated_name = col_n2.text_input(f"氏名 ({adm})", value=adm_name, key=f"name_input_{adm}", label_visibility="collapsed")
            if updated_name != adm_name:
                admins_dict[adm]["name"] = updated_name
                save_admins(admins_dict)
                st.rerun()
            
            if can_remove_admins and adm != current_user and role != "master":
                if col_n3.checkbox("削除確認", key=f"chk_adm_{adm}"):
                    if col_n3.button("権限解除", key=f"del_adm_{adm}"):
                        save_to_deleted_backup("admin", adm, admins_dict[adm])
                        del admins_dict[adm]
                        save_admins(admins_dict)
                        st.success("管理者権限を解除し、バックアップに保存しました。")
                        st.rerun()

    with tab2:
        st.subheader("👥 協会員の追加・管理・バックアップ付き削除")
        new_member_email = st.text_input("追加する会員のメールアドレス", key="new_member_email_input")
        new_member_name = st.text_input("追加する会員の氏名", key="new_member_name_input")
        
        if st.button("協会員として登録する", key="add_member_btn"):
            m_email_clean = new_member_email.strip().lower()
            m_name_clean = new_member_name.strip()
            if m_email_clean and "@" in m_email_clean:
                if m_email_clean not in email_to_name:
                    email_to_name[m_email_clean] = m_name_clean
                    save_association_members_json(email_to_name)
                    st.success(f"🎉 会員 `{m_email_clean}` を登録し、GitHubに自動同期しました！")
                    st.rerun()
                else:
                    st.warning("すでに登録されています。")
            else:
                st.warning("有効なメールアドレスを入力してください。")
                
        st.markdown("---")
        for mem_email, mem_name in list(email_to_name.items()):
            col_m1, col_m2, col_m3 = st.columns([3, 2, 1])
            col_m1.write(f"📧 `{mem_email}`")
            up_m_name = col_m2.text_input(f"氏名 ({mem_email})", value=mem_name, key=f"mem_name_{mem_email}", label_visibility="collapsed")
            if up_m_name != mem_name:
                email_to_name[mem_email] = up_m_name
                save_association_members_json(email_to_name)
                st.rerun()
            
            if mem_email != MASTER_ADMIN:
                if col_m3.checkbox("削除確認", key=f"chk_mem_{mem_email}"):
                    if col_m3.button("削除", key=f"del_mem_{mem_email}"):
                        save_to_deleted_backup("member", mem_email, {"name": mem_name})
                        del email_to_name[mem_email]
                        save_association_members_json(email_to_name)
                        st.success("会員を削除し、バックアップに保存しました。")
                        st.rerun()
            else:
                col_m3.write("*(マスター)*")

    with tab3:
        st.subheader("👥 協会会員のアプリ利用状況・認証状況（永続記録）")
        storage_data = st.session_state.app_storage
        all_history = storage_data.get("exam_history", [])
        activity_history = storage_data.get("activity_history", [])
        logged_in_users_list = storage_data.get("logged_in_users", [])
        
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

        active_users_set = set(logged_in_users_list).union(set(user_exams_map.keys())).union(set(registered_admins))
        total_members_count = len(member_emails)
        logged_in_count = sum(1 for m in member_emails if m in active_users_set)
        
        col_st1, col_st2, col_st3 = st.columns(3)
        col_st1.metric("総登録会員数", f"{total_members_count} 名")
        col_st2.metric("利用実績あり（ログイン済）", f"{logged_in_count} 名")
        col_st3.metric("未利用", f"{total_members_count - logged_in_count} 名")
        
        st.markdown("---")
        st.write("**📋 全会員の利用状況・直近のテスト受験履歴（過去2回分）:**")
        
        member_status_list = []
        for m_email in member_emails:
            m_name = email_to_name.get(m_email, "登録名なし")
            is_active = m_email in active_users_set or m_email == current_user
            status_str = "✅ ログイン済（実績あり）" if is_active else "⏳ 未ログイン"
            
            u_logins = user_logins_map.get(m_email, [])
            last_login = max(u_logins) if u_logins else ("ログイン実績あり" if is_active and not u_logins else "-")
            
            u_hist = user_exams_map.get(m_email, [])
            u_hist_sorted = sorted(u_hist, key=lambda x: x.get("timestamp", ""), reverse=True)
            recent_2 = u_hist_sorted[:2]
            
            history_str_1 = f"1回前: {recent_2[0]['timestamp']} ({recent_2[0]['exam_type']} / 正答率: {recent_2[0]['rate']}%)" if len(recent_2) > 0 else "履歴なし"
            history_str_2 = f"2回前: {recent_2[1]['timestamp']} ({recent_2[1]['exam_type']} / 正答率: {recent_2[1]['rate']}%)" if len(recent_2) > 1 else "-"
            
            member_status_list.append({
                "氏名": m_name,
                "メールアドレス": m_email,
                "ステータス": status_str,
                "直近のログイン日時": last_login,
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
        known_users = sorted(list(set([h["user_email"] for h in history] + member_emails)))
        
        if known_users:
            user_options = {get_user_display_name(u, email_to_name, admins_dict): u for u in known_users}
            selected_display_name = st.selectbox("ユーザーを選択", list(user_options.keys()))
            selected_user = user_options[selected_display_name]
            
            user_history = [h for h in history if h["user_email"] == selected_user]
            
            if user_history:
                # ユーザーの成績表を日本語化し、メールアドレスを非表示にする
                report_list = []
                for h in sorted(user_history, key=lambda x: x.get("timestamp", ""), reverse=True):
                    exam_type = h.get("exam_type", "演習")
                    rate = h.get("rate", 0)
                    
                    # 同一ユーザーの過去の同種テストの平均正解率を計算
                    same_type_history = [item["rate"] for item in user_history if item.get("exam_type") == exam_type]
                    avg_rate = sum(same_type_history) / len(same_type_history) if same_type_history else rate
                    
                    # 前回（1回前）の正解率
                    prev_rates = [item["rate"] for item in sorted(user_history, key=lambda x: x.get("timestamp", "")) if item.get("exam_type") == exam_type and item.get("timestamp") < h.get("timestamp")]
                    prev_rate_str = f"{prev_rates[-1]}%" if prev_rates else "初回"

                    report_list.append({
                        "日時": h.get("timestamp"),
                        "受講テスト種類": exam_type,
                        "正解数": h.get("score"),
                        "総問題数": h.get("total"),
                        "今回の正解率(%)": f"{rate}%",
                        "前回の正解率": prev_rate_str,
                        "平均正解率": f"{avg_rate:.1f}%",
                        "合否判定": "合格 🏆" if h.get("passed") else "不合格 💥"
                    })
                
                df_report = pd.DataFrame(report_list)
                st.dataframe(df_report, use_container_width=True, hide_index=True)
            else:
                st.info("選択されたユーザーの受験履歴はまだありません。")
        else:
            st.info("登録されているユーザーがありません。")

    with tab5:
        st.subheader("⚙️ 成績データの個別管理 & 問題データExcel更新・バックアップ")
        uploaded_file = st.file_uploader("新しい問題データ（Excel .xlsx）をアップロード", type=["xlsx"], key="excel_uploader")
        if uploaded_file is not None:
            with open(EXCEL_FILENAME, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("🎉 問題データ（Excel）を更新しました！")
            st.cache_data.clear()

    with tab6:
        st.subheader("🗄️ 削除データバックアップ履歴（自動保存ログ）")
        st.write("削除された会員や管理者のデータは、すべて安全に自動バックアップされています。")
        if os.path.exists(BACKUP_JSON_FILE):
            try:
                with open(BACKUP_JSON_FILE, "r", encoding="utf-8") as f:
                    backup_content = json.load(f)
                deleted_list = backup_content.get("deleted_history", [])
                if deleted_list:
                    st.dataframe(pd.DataFrame(deleted_list), use_container_width=True)
                else:
                    st.info("バックアップされた削除履歴はありません。")
            except:
                st.info("バックアップファイルの読み込みに失敗しました。")
        else:
            st.info("現在バックアップ履歴はありません。")