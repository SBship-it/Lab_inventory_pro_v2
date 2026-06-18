import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. הגדרות דף ועיצוב מותאם אישית (Custom CSS) - החלפה מלאה לכפתורים אמיתיים וכהים
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    
    /* תיקון צבע הטקסט בלשוניות (Tabs) */
    .stTabs [data-baseweb="tab"] p {
        color: #cbd5e1 !important;
    }
    .stTabs [aria-selected="true"] p {
        color: #0f172a !important;
        font-weight: bold !important;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #1e293b; border-radius: 12px; padding: 5px; }
    .stTabs [aria-selected="true"] { background-color: #2dd4bf !important; border-radius: 8px !important; }

    /* עיצוב ישיר של כפתורי המערכת של Streamlit - הופך אותם לריבועים הכהים! */
    div[data-testid="stButton"] > button[key^="cat_btn_"] {
        background-color: #1e293b !important;
        color: #2dd4bf !important;
        border: 2px solid #334155 !important;
        border-radius: 15px !important;
        min-height: 160px !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 15px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* אפקט ריחוף על הכפתור הריבועי */
    div[data-testid="stButton"] > button[key^="cat_btn_"]:hover {
        border-color: #2dd4bf !important;
        background-color: #243049 !important;
        color: #5eead4 !important;
        transform: translateY(-4px) !important;
        box-shadow: 0 10px 20px rgba(45, 212, 191, 0.15) !important;
    }

    /* תיקון פונט וגודל הטקסט בתוך כפתור המערכת המעוצב */
    div[data-testid="stButton"] > button[key^="cat_btn_"] p {
        color: #2dd4bf !important;
        font-size: 1.4rem !important;
        font-weight: bold !important;
        margin: 0 !important;
    }

    /* כרטיסי פריטים (כשנכנסים לקטגוריה) */
    .item-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 20px;
        border-right: 6px solid #2dd4bf;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .item-card.expired { border-right-color: #ef4444 !important; background: #2d1e1e; }
    .item-card.warning { border-right-color: #f59e0b !important; background: #2d271e; }
    
    label, .stMarkdown p { color: #cbd5e1 !important; }
    h1, h2, h3 { color: #2dd4bf !important; font-family: 'Segoe UI', sans-serif; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. חיבור לבסיס נתונים (SQLite)
conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, icon TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, category TEXT, 
    location TEXT, quantity INTEGER, expiry_date TEXT, catalog_number TEXT)''')
conn.commit()

# הכנסת קטגוריות ברירת מחדל אם ריק
cursor.execute("SELECT COUNT(*) FROM categories")
if cursor.fetchone()[0] == 0:
    defaults = [("נוגדנים", "🧬"), ("כימיקלים", "🧪"), ("מתכלים", "📦"), ("כללי", "🛠️")]
    cursor.executemany("INSERT INTO categories (name, icon) VALUES (?, ?)", defaults)
    conn.commit()

# 3. ניהול סשן לניווט בין קטגוריות
if 'selected_category' not in st.session_state: 
    st.session_state.selected_category = None

# --- ממשק ראשי ---
st.title("🧪 LabInventory Pro - ניהול חכם")

tab_manage, tab_dash = st.tabs(["🛒 ניהול והזמנות", "📊 דאשבורד ומעקב תפוגה"])

# ----------------- לשונית 1: ניהול והזמנות -----------------
with tab_manage:
    # כפתור חזרה אם אנחנו בתוך קטגוריה
    if st.session_state.selected_category:
        if st.button("⬅️ חזרה לכל הקטגוריות"):
            st.session_state.selected_category = None
            st.rerun()

    # תצוגת קטגוריות (ריבועים לחיצים אמיתיים ללא כפתור כפול מתחת)
    if st.session_state.selected_category is None:
        st.subheader("בחר קטגוריה לניהול המלאי:")
        
        df_cats = pd.read_sql_query("SELECT * FROM categories", conn)
        cols = st.columns(3) 
        
        for idx, row in df_cats.iterrows():
            with cols[idx % 3]:
                # יצירת מחרוזת המשלבת אייקון וטקסט עם ירידת שורה, שתופיע בתוך כפתור המערכת המעוצב
                button_content = f"{row['icon']}\n\n{row['name']}"
                if st.button(button_content, key=f"cat_btn_{row['id']}", use_container_width=True):
                    st.session_state.selected_category = row['name']
                    st.rerun()
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.expander("⚙️ הגדרות מערכת: ניהול קטגוריות (הוספה/מחיקה)"):
            c1, c2 = st.columns(2)
            new_cat = c1.text_input("שם קטגוריה חדשה:")
            new_icon = c1.selectbox("אייקון:", ["🧬", "🧪", "📦", "🛠️", "🌡️", "🔍", "🧫"])
            if c1.button("הוסף קטגוריה", use_container_width=True):
                if new_cat:
                    try:
                        cursor.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (new_cat, new_icon))
                        conn.commit()
                        st.success("הקטגוריה נוספה!")
                        st.rerun()
                    except: 
                        st.error("הקטגוריה כבר קיימת")
            
            del_cat = c2.selectbox("בחר קטגוריה למחיקה:", df_cats['name'].tolist())
            if c2.button("🗑️ מחק קטגוריה", use_container_width=True):
                cursor.execute("DELETE FROM categories WHERE name = ?", (del_cat,))
                conn.commit()
                st.warning(f"הקטגוריה {del_cat} נמחקה")
                st.rerun()

    # תצוגת פריטים בתוך קטגוריה נבחרת
    else:
        cat_name = st.session_state.selected_category
        st.subheader(f"ניהול פריטים בקטגוריית: {cat_name}")
        
        with st.expander(f"➕ הוספת פריט חדש ל-{cat_name}"):
            with st.form("add_item"):
                c_i1, c_i2 = st.columns(2)
                i_name = c_i1.text_input("שם הפריט / החומר:")
                i_cat_no = c_i1.text_input("מספר קטלוגי (Cat No.):")
                i_loc = c_i2.text_input("מיקום פיזי (לדוגמה: Freezer -20C, Box B):")
                i_qty = c_i2.number_input("כמות במלאי:", min_value=0, value=1)
                i_exp = st.date_input("תאריך תפוגה (פג תוקף):", value=None)
                
                if st.form_submit_button("💾 שמור פריט במערכת", use_container_width=True):
                    exp_s = i_exp.strftime('%Y-%m-%d') if i_exp else "אין תפוגה"
                    cursor.execute("INSERT INTO inventory (item_name, category, location, quantity, expiry_date, catalog_number) VALUES (?,?,?,?,?,?)", 
                                   (i_name, cat_name, i_loc, i_qty, exp_s, i_cat_no))
                    conn.commit()
                    st.success("הפריט נוסף בהצלחה!")
                    st.rerun()

        # הצגת רשימת הפריטים
        df_items = pd.read_sql_query("SELECT * FROM inventory WHERE category = ?", conn, params=(cat_name,))
        if df_items.empty:
            st.info("אין עדיין פריטים בקטגוריה זו. לחצי על הפלוס למעלה כדי להוסיף.")
        else:
            today = datetime.today()
            for _, item in df_items.iterrows():
                card_class = "item-card"
                expiry_status_text = ""
                
                if item['expiry_date'] and item['expiry_date'] != "אין תפוגה":
                    try:
                        exp_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d')
                        days_to_expire = (exp_date - today).days
                        if days_to_expire < 0:
                            card_class = "item-card expired"
                            expiry_status_text = "❌ פג תוקף!"
                        elif days_to_expire <= 30:
                            card_class = "item-card warning"
                            expiry_status_text = f"⚠️ עומד לפוג (בעוד {days_to_expire} ימים)"
                    except ValueError: 
                        pass

                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <b style="color: #2dd4bf; font-size: 1.3rem;">{item['item_name']}</b>
                        <span style="background: #334155; padding: 4px 10px; border-radius: 20px; font-size: 0.9rem;">📍 {item['location']}</span>
                    </div>
                    <div style="font-size: 0.95rem; margin-top: 10px; color: #cbd5e1;">
                        🔢 כמות: <b>{item['quantity']}</b> | 🔖 קטלוג: {item['catalog_number']} | 📅 תפוגה: {item['expiry_date']} <b style="color:#ef4444;">{expiry_status_text}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([2, 1, 1])
                new_q = c1.number_input("עדכון כמות מהיר:", min_value=0, value=int(item['quantity']), key=f"q_{item['id']}", label_visibility="collapsed")
                
                if c2.button("🔄 עדכן", key=f"up_{item['id']}", use_container_width=True):
                    cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_q, item['id']))
                    conn.commit()
                    st.rerun()
                if c3.button("🗑️ מחק", key=f"del_{item['id']}", use_container_width=True):
                    cursor.execute("DELETE FROM inventory WHERE id = ?", (item['id'],))
                    conn.commit()
                    st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

# ----------------- לשונית 2: דאשבורד ומעקב תפוגה -----------------
with tab_dash:
    st.subheader("📊 ניתוח ומצב המלאי במעבדה")
    
    df_all = pd.read_sql_query("SELECT * FROM inventory", conn)
    
    if df_all.empty:
        st.info("אין עדיין נתונים במערכת כדי לייצר דאשבורד.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("סה\"כ פריטים שונים במערכת", len(df_all))
        m2.metric("סה\"כ יחידות מלאי כולל", int(df_all['quantity'].sum()))
        
        st.markdown("---")
        st.markdown("### 📦 התפלגות חומרים לפי קטגוריות")
        st.bar_chart(df_all['category'].value_counts())
        
        st.markdown("### 🔔 התראות תפוגה דחופות (30 יום הקרובים)")
        today = datetime.today()
        alert_triggered = False
        
        for idx, row in df_all.iterrows():
            if row['expiry_date'] and row['expiry_date'] != "אין תפוגה":
                try:
                    exp_date = datetime.strptime(row['expiry_date'], '%Y-%m-%d')
                    days_to_expire = (exp_date - today).days
                    if days_to_expire < 0:
                        st.error(f"🚨 **{row['item_name']}** (קטלוג: {row['catalog_number']}) נמצא ב- {row['location']} ו**פג תוקפו** לפני {abs(days_to_expire)} ימים!")
                        alert_triggered = True
                    elif days_to_expire <= 30:
                        st.warning(f"⚠️ **{row['item_name']}** (קטלוג: {row['catalog_number']}) נמצא ב- {row['location']} ו**יפוג בעוד {days_to_expire} ימים**.")
                        alert_triggered = True
                except ValueError: 
                    pass
                
        if not alert_triggered:
            st.success("✅ אין חומרים פגי תוקף או קרובים לתפוגה במעבדה.")
