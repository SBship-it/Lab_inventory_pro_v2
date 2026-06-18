import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta

# 1. הגדרות דף ועיצוב מותאם אישית (Custom CSS)
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    /* עיצוב רקע כללי */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* עיצוב כרטיסי פריטים */
    .inventory-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #334155;
        transition: transform 0.2s, border-color 0.2s;
    }
    .inventory-card:hover {
        transform: translateY(-3px);
        border-color: #2dd4bf;
    }
    
    /* תגיות סטטוס */
    .status-badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        text-transform: uppercase;
    }
    .status-normal { background-color: #065f46; color: #34d399; }
    .status-low { background-color: #7f1d1d; color: #fca5a5; }
    .status-expired { background-color: #581c87; color: #d8b4fe; }
    .status-soon { background-color: #78350f; color: #fcd34d; }
    
    /* טקסטים ותוויות */
    label, .stMarkdown p {
        color: #cbd5e1 !important;
    }
    h1, h2, h3 {
        color: #2dd4bf !important;
    }
    
    /* עיצוב הטאבים */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2dd4bf !important;
        color: #0f172a !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. פונקציות עזר ובסיס נתונים
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, catalog_number TEXT, 
    vendor TEXT, category TEXT, location TEXT, quantity INTEGER, 
    unit TEXT, min_quantity INTEGER DEFAULT 1, expiry_date TEXT)''')
cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
conn.commit()

cursor.execute('SELECT * FROM users WHERE username = ?', ("admin",))
if not cursor.fetchone():
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ("admin", make_hashes("lab2026")))
    conn.commit()

# 3. ניהול כניסה
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🧪 LabInventory Pro")
    with st.form("login"):
        user = st.text_input("שם משתמש")
        passwd = st.text_input("סיסמה", type='password')
        if st.form_submit_button("התחבר"):
            cursor.execute('SELECT password FROM users WHERE username = ?', (user,))
            data = cursor.fetchone()
            if data and check_hashes(passwd, data[0]):
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("שגיאה בפרטים")
else:
    st.title("🧪 LabInventory Pro - ניהול חכם")
    tab_inv, tab_add = st.tabs(["📦 המלאי שלי", "➕ הוספת פריט"])

    with tab_inv:
        df = pd.read_sql_query("SELECT * FROM inventory", conn)
        
        # חיפוש וסינון
        col_s1, col_s2 = st.columns([2, 1])
        search = col_s1.text_input("🔍 חיפוש חופשי:")
        cat_filter = col_s2.selectbox("סינון קטגוריה:", ["הכל"] + list(df["category"].unique()) if not df.empty else ["הכל"])
        
        if not df.empty:
            # לוגיקת סינון
            if search: df = df[df['item_name'].str.contains(search, case=False)]
            if cat_filter != "הכל": df = df[df['category'] == cat_filter]
            
            # הצגת כרטיסים
            for _, row in df.iterrows():
                # קביעת סטטוס
                status_class = "status-normal"
                status_text = "תקין"
                
                today = datetime.now().date()
                exp_date = pd.to_datetime(row['expiry_date']).date() if row['expiry_date'] else None
                
                if exp_date and exp_date < today:
                    status_class, status_text = "status-expired", "פג תוקף"
                elif exp_date and exp_date < today + timedelta(days=30):
                    status_class, status_text = "status-soon", "פג בקרוב"
                elif row['quantity'] <= row['min_quantity']:
                    status_class, status_text = "status-low", "מלאי נמוך"
                
                # רינדור הכרטיס
                with st.container():
                    st.markdown(f"""
                    <div class="inventory-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: #2dd4bf;">{row['item_name']}</h3>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
                            <div><small>📦 כמות:</small>  
<b>{row['quantity']} {row['unit'] if row['unit'] else 'יחידות'}</b></div>
                            <div><small>📍 מיקום:</small>  
<b>{row['location']}</b></div>
                            <div><small>🔖 קטלוג:</small>  
<b>{row['catalog_number']}</b></div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.85rem; color: #94a3b8;">
                            🏢 ספק: {row['vendor']} | 📅 תפוגה: {row['expiry_date'] if row['expiry_date'] else 'ללא'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # כפתור עדכון מהיר מתחת לכל כרטיס
                    with st.expander("🔄 עדכון מהיר"):
                        new_q = st.number_input(f"עדכן כמות ל-{row['item_name']}:", min_value=0, value=int(row['quantity']), key=f"q_{row['id']}")
                        if st.button("שמור שינוי", key=f"btn_{row['id']}"):
                            cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_q, row['id']))
                            conn.commit()
                            st.rerun()
        else:
            st.info("אין פריטים במלאי.")

    with tab_add:
        with st.form("add"):
            name = st.text_input("שם הפריט:")
            cat = st.selectbox("קטגוריה:", ["נוגדנים", "כימיקלים", "מתכלים", "אחר"])
            loc = st.text_input("מיקום:")
            qty = st.number_input("כמות:", min_value=0, value=1)
            exp = st.date_input("תאריך תפוגה:", value=None)
            if st.form_submit_button("הוסף"):
                cursor.execute("INSERT INTO inventory (item_name, category, location, quantity, expiry_date) VALUES (?,?,?,?,?)", 
                               (name, cat, loc, qty, exp.strftime('%Y-%m-%d') if exp else None))
                conn.commit()
                st.success("נוסף!")
                st.rerun()
