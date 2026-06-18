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
    label, .stMarkdown p, .stText, [data-testid="stMarkdownContainer"] p {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }
    h1, h2, h3 {
        color: #2dd4bf !important;
    }
    
    /* עיצוב הטאבים */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 12px;
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #cbd5e1;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2dd4bf !important;
        color: #0f172a !important;
    }

    /* עיצוב כפתורים */
    .stButton>button {
        background-color: #2dd4bf;
        color: #0f172a;
        border-radius: 8px;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #14b8a6;
        color: #ffffff;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. פונקציות עזר ובסיס נתונים
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

# יצירת טבלאות
cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, catalog_number TEXT, 
    vendor TEXT, category TEXT, location TEXT, quantity INTEGER, 
    unit TEXT, min_quantity INTEGER DEFAULT 1, expiry_date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, requested_by TEXT, 
    quantity INTEGER, status TEXT, date_requested TEXT)''')
cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
conn.commit()

# יצירת אדמין אם לא קיים
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
            else: st.error("שם משתמש או סיסמה שגויים")
else:
    st.sidebar.markdown(f"### 👋 שלום, מנהל")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("🧪 LabInventory Pro - מרכז ניהול")
    tab_inv, tab_add, tab_orders, tab_dash = st.tabs(["📦 מלאי", "➕ הוספה", "🛒 הזמנות", "📊 דאשבורד"])

    # --- לשונית מלאי (כרטיסים) ---
    with tab_inv:
        df = pd.read_sql_query("SELECT * FROM inventory", conn)
        col_s1, col_s2 = st.columns([2, 1])
        search = col_s1.text_input("🔍 חיפוש חופשי (שם או קטלוג):")
        cat_filter = col_s2.selectbox("סנן קטגוריה:", ["הכל"] + list(df["category"].unique()) if not df.empty else ["הכל"])
        
        if not df.empty:
            if search: df = df[df['item_name'].str.contains(search, case=False) | df['catalog_number'].str.contains(search, case=False)]
            if cat_filter != "הכל": df = df[df['category'] == cat_filter]
            
            for _, row in df.iterrows():
                status_class, status_text = "status-normal", "תקין"
                today = datetime.now().date()
                exp_date = pd.to_datetime(row['expiry_date']).date() if row['expiry_date'] else None
                
                if exp_date and exp_date < today: status_class, status_text = "status-expired", "פג תוקף"
                elif exp_date and exp_date < today + timedelta(days=30): status_class, status_text = "status-soon", "פג בקרוב"
                elif row['quantity'] <= row['min_quantity']: status_class, status_text = "status-low", "מלאי נמוך"
                
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
                with st.expander("🔄 עדכון מהיר"):
                    new_q = st.number_input(f"עדכן כמות:", min_value=0, value=int(row['quantity']), key=f"q_{row['id']}")
                    if st.button("שמור", key=f"btn_{row['id']}"):
                        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_q, row['id']))
                        conn.commit()
                        st.rerun()
        else: st.info("המלאי ריק.")

    # --- לשונית הוספה (מלאה) ---
    with tab_add:
        st.subheader("הוספת פריט חדש")
        with st.form("add_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("שם הפריט:")
            cat_no = c1.text_input("מספר קטלוגי:")
            vend = c1.text_input("ספק:")
            cat = c2.selectbox("קטגוריה:", ["נוגדנים", "כימיקלים", "קיטים", "מתכלים", "אחר"])
            loc = c2.text_input("מיקום:")
            qty = c2.number_input("כמות:", min_value=0, value=1)
            min_q = c2.number_input("מינימום להתראה:", min_value=0, value=1)
            exp = c2.date_input("תאריך תפוגה:", value=None)
            if st.form_submit_button("➕ הוסף למלאי"):
                if name:
                    exp_s = exp.strftime('%Y-%m-%d') if exp else None
                    cursor.execute("INSERT INTO inventory (item_name, catalog_number, vendor, category, location, quantity, min_quantity, expiry_date) VALUES (?,?,?,?,?,?,?,?)", 
                                   (name, cat_no, vend, cat, loc, qty, min_q, exp_s))
                    conn.commit()
                    st.success("הפריט נוסף!")
                    st.rerun()

    # --- לשונית הזמנות ---
    with tab_orders:
        st.subheader("🛒 ניהול בקשות הזמנה")
        with st.expander("➕ בקשה חדשה"):
            with st.form("o_form"):
                oname = st.text_input("שם חומר:")
                ouser = st.text_input("חוקר מזמין:")
                oqty = st.number_input("כמות:", min_value=1)
                if st.form_submit_button("שלח"):
                    cursor.execute("INSERT INTO orders (item_name, requested_by, quantity, status, date_requested) VALUES (?,?,?,'ממתין',?)", 
                                   (oname, ouser, oqty, datetime.today().strftime('%Y-%m-%d')))
                    conn.commit()
                    st.success("נשלח!")
                    st.rerun()
        df_o = pd.read_sql_query("SELECT * FROM orders", conn)
        if not df_o.empty: st.dataframe(df_o, use_container_width=True, hide_index=True)

    # --- לשונית דאשבורד ---
    with tab_dash:
        st.subheader("📊 סטטיסטיקות")
        df_d = pd.read_sql_query("SELECT * FROM inventory", conn)
        if not df_d.empty:
            c1, c2 = st.columns(2)
            c1.metric("סה\"כ פריטים", len(df_d))
            c2.metric("מלאי נמוך", len(df_d[df_d['quantity'] <= df_d['min_quantity']]))
            st.bar_chart(df_d['category'].value_counts())
