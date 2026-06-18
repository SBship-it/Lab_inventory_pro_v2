import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta

# 1. הגדרות דף ועיצוב מותאם אישית
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    
    /* עיצוב ריבועי קטגוריות */
    .category-card {
        background-color: #1e293b;
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        border: 2px solid #334155;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }
    .category-card:hover {
        border-color: #2dd4bf;
        transform: scale(1.05);
        background-color: #26334d;
    }
    .category-icon { font-size: 3rem; margin-bottom: 10px; }
    .category-title { color: #2dd4bf; font-size: 1.5rem; font-weight: bold; }
    
    /* כרטיסי פריטים (בתוך קטגוריה) */
    .item-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border-right: 5px solid #2dd4bf;
        margin-bottom: 10px;
    }
    
    label, .stMarkdown p { color: #cbd5e1 !important; }
    h1, h2, h3 { color: #2dd4bf !important; }
    
    .stTabs [data-baseweb="tab-list"] { background-color: #1e293b; border-radius: 12px; }
    .stTabs [aria-selected="true"] { background-color: #2dd4bf !important; color: #0f172a !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. בסיס נתונים
conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

# טבלאות
cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, icon TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, category TEXT, 
    location TEXT, quantity INTEGER, expiry_date TEXT, catalog_number TEXT)''')
conn.commit()

# הכנסת קטגוריות ברירת מחדל אם הטבלה ריקה
cursor.execute("SELECT COUNT(*) FROM categories")
if cursor.fetchone()[0] == 0:
    defaults = [("נוגדנים", "🧬"), ("כימיקלים", "🧪"), ("מתכלים", "📦"), ("כללי", "🛠️")]
    cursor.executemany("INSERT INTO categories (name, icon) VALUES (?, ?)", defaults)
    conn.commit()

# 3. ניהול סשן לניווט
if 'selected_category' not in st.session_state: st.session_state.selected_category = None

# --- ממשק ראשי ---
st.title("🧪 LabInventory Pro - ניהול חכם")

tab_manage, tab_dash = st.tabs(["🛒 ניהול והזמנות", "📊 דאשבורד"])

with tab_manage:
    # כפתור חזרה אם אנחנו בתוך קטגוריה
    if st.session_state.selected_category:
        if st.button("⬅️ חזרה לכל הקטגוריות"):
            st.session_state.selected_category = None
            st.rerun()

    # תצוגת קטגוריות (ריבועים)
    if st.session_state.selected_category is None:
        st.subheader("בחר קטגוריה לניהול:")
        
        # שליפת קטגוריות
        df_cats = pd.read_sql_query("SELECT * FROM categories", conn)
        cols = st.columns(3)
        
        for idx, row in df_cats.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="category-card">
                    <div class="category-icon">{row['icon']}</div>
                    <div class="category-title">{row['name']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"פתח את {row['name']}", key=f"cat_{row['id']}", use_container_width=True):
                    st.session_state.selected_category = row['name']
                    st.rerun()
        
        st.markdown("---")
        # הוספה/מחיקה של קטגוריות
        with st.expander("⚙️ ניהול קטגוריות (הוספה/מחיקה)"):
            c1, c2 = st.columns(2)
            new_cat = c1.text_input("שם קטגוריה חדשה:")
            new_icon = c1.selectbox("אייקון:", ["🧬", "🧪", "📦", "🛠️", "🌡️", "🔍", "🧫"])
            if c1.button("הוסף קטגוריה"):
                try:
                    cursor.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (new_cat, new_icon))
                    conn.commit()
                    st.success("הקטגוריה נוספה!")
                    st.rerun()
                except: st.error("הקטגוריה כבר קיימת")
            
            del_cat = c2.selectbox("בחר קטגוריה למחיקה:", df_cats['name'].tolist())
            if c2.button("מחק קטגוריה"):
                cursor.execute("DELETE FROM categories WHERE name = ?", (del_cat,))
                conn.commit()
                st.warning(f"הקטגוריה {del_cat} נמחקה")
                st.rerun()

    # תצוגת פריטים בתוך קטגוריה נבחרת
    else:
        cat_name = st.session_state.selected_category
        st.subheader(f"ניהול פריטים בקטגוריית: {cat_name}")
        
        # הוספת פריט חדש לקטגוריה הזו
        with st.expander(f"➕ הוספת פריט חדש ל-{cat_name}"):
            with st.form("add_item"):
                i_name = st.text_input("שם הפריט:")
                i_cat_no = st.text_input("מספר קטלוגי:")
                i_loc = st.text_input("מיקום:")
                i_qty = st.number_input("כמות:", min_value=0, value=1)
                i_exp = st.date_input("תאריך תפוגה:", value=None)
                if st.form_submit_button("שמור פריט"):
                    exp_s = i_exp.strftime('%Y-%m-%d') if i_exp else None
                    cursor.execute("INSERT INTO inventory (item_name, category, location, quantity, expiry_date, catalog_number) VALUES (?,?,?,?,?,?)", 
                                   (i_name, cat_name, i_loc, i_qty, exp_s, i_cat_no))
                    conn.commit()
                    st.success("הפריט נוסף בהצלחה!")
                    st.rerun()

        # הצגת רשימת הפריטים
        df_items = pd.read_sql_query("SELECT * FROM inventory WHERE category = ?", conn, params=(cat_name,))
        if df_items.empty:
            st.info("אין עדיין פריטים בקטגוריה זו.")
        else:
            for _, item in df_items.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="item-card">
                        <div style="display: flex; justify-content: space-between;">
                            <b style="color: #2dd4bf; font-size: 1.2rem;">{item['item_name']}</b>
                            <span>📍 {item['location']}</span>
                        </div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">
                            🔢 כמות: {item['quantity']} | 🔖 קטלוג: {item['catalog_number']} | 📅 תפוגה: {item['expiry_date']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns([1, 1, 2])
                    new_q = c1.number_input("עדכן כמות:", min_value=0, value=int(item['quantity']), key=f"q_{item['id']}")
                    if c2.button("עדכן", key=f"up_{item['id']}"):
                        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_q, item['id']))
                        conn.commit()
                        st.rerun()
                    if c3.button("🗑️ מחק פריט", key=f"del_{item['id']}"):
                        cursor.execute("DELETE FROM inventory WHERE id = ?", (item['id'],))
                        conn.commit()
                        st.rerun()

with tab_dash:
    st.subheader("📊 מצב המעבדה")
    df_all = pd.read_sql_query("SELECT * FROM inventory", conn)
    if not df_all.empty:
        st.metric("סה\"כ פריטים במלאי", len(df_all))
        st.bar_chart(df_all['category'].value_counts())
    else: st.info("אין נתונים להצגה.")
