import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta

# 1. הגדרות דף ועיצוב מותאם אישית (Custom CSS)
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    /* עיצוב רקע כללי וגופנים */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* תיקון נראות תוויות (Labels) מעל תיבות הקלט - צבע אפור בהיר וברור */
    label, .stMarkdown p, .stText, [data-testid="stMarkdownContainer"] p, .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
    }
    
    /* עיצוב כותרות */
    h1, h2, h3 {
        color: #2dd4bf !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* עיצוב הטאבים (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #1e293b;
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #cbd5e1;
        background-color: transparent;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
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
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #14b8a6;
        color: #ffffff;
        transform: translateY(-2px);
    }
    
    /* קופסאות מידע וטפסים */
    .stForm, .stExpander {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    
    /* התראות */
    .stAlert {
        background-color: #334155 !important;
        color: #2dd4bf !important;
        border: 1px solid #2dd4bf !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. פונקציות אבטחה
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# 3. חיבור לבסיס הנתונים
conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

# יצירת טבלאות בצורה בטוחה ויציבה
cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT, catalog_number TEXT, vendor TEXT,
        category TEXT, location TEXT, quantity INTEGER, unit TEXT, 
        min_quantity INTEGER DEFAULT 1, expiry_date TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT, catalog_number TEXT, vendor TEXT,
        requested_by TEXT, quantity INTEGER, status TEXT, date_requested TEXT
    )
''')
cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, account_status TEXT)')
conn.commit()

# יצירת משתמש מנהל אם לא קיים (מונע שגיאות כפילות)
cursor.execute('SELECT * FROM users WHERE username = ?', ("admin",))
if not cursor.fetchone():
    cursor.execute('INSERT INTO users (username, password, account_status) VALUES (?, ?, ?)', 
                   ("admin", make_hashes("lab2026"), "active"))
    conn.commit()

# 4. ניהול סשן
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- מסך התחברות ---
if not st.session_state['logged_in']:
    st.title("🧪 LabInventory Pro")
    st.subheader("מערכת ניהול מלאי והזמנות מעבדה")
    
    col_login, _ = st.columns([1, 1])
    with col_login:
        with st.form("login_form"):
            st.markdown("### כניסת חוקרים ומנהלים")
            user = st.text_input("שם משתמש")
            passwd = st.text_input("סיסמה", type='password')
            login_btn = st.form_submit_button("התחבר למערכת")
            
            if login_btn:
                cursor.execute('SELECT password FROM users WHERE username = ?', (user,))
                user_data = cursor.fetchone()
                if user_data and check_hashes(passwd, user_data[0]):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")
    st.info("💡 משתמש בדיקה: `admin` | סיסמה `lab2026`")

# --- המערכת המרכזית ---
else:
    st.sidebar.markdown(f"### 👋 שלום, {st.session_state['username']}")
    if st.sidebar.button("🚪 התנתק", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    st.title("🧪 LabInventory Pro - מרכז ניהול")
    st.markdown("---")
    
    tab_inv, tab_add, tab_orders, tab_dashboard = st.tabs(["📦 מלאי", "➕ הוספה", "🛒 הזמנות", "📊 דאשבורד"])
    
    with tab_inv:
        st.subheader("חיפוש וניהול פריטים")
        df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
        
        if df_inv.empty:
            st.info("המחסן ריק כרגע.")
        else:
            df_inv['status'] = 'רגיל'
            today = datetime.now().date()
            df_inv['expiry_date_dt'] = pd.to_datetime(df_inv['expiry_date'], errors='coerce').dt.date
            
            df_inv.loc[df_inv['expiry_date_dt'].notna() & (df_inv['expiry_date_dt'] < today), 'status'] = 'פג תוקף'
            df_inv.loc[df_inv['expiry_date_dt'].notna() & (df_inv['expiry_date_dt'] >= today) & (df_inv['expiry_date_dt'] < today + timedelta(days=30)), 'status'] = 'קרוב לתפוגה'
            df_inv.loc[(df_inv['quantity'] <= df_inv['min_quantity']) & (df_inv['status'] == 'רגיל'), 'status'] = 'מלאי נמוך'

            col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
            search = col_s1.text_input("🔍 חפש לפי שם או קטלוג:")
            cat_filter = col_s2.selectbox("סנן קטגוריה:", ["הכל"] + list(df_inv["category"].unique()))
            stat_filter = col_s3.selectbox("סנן סטטוס:", ["הכל"] + list(df_inv["status"].unique()))
            
            filtered = df_inv.copy()
            if search:
                filtered = filtered[filtered["item_name"].str.contains(search, case=False, na=False) | filtered["catalog_number"].str.contains(search, case=False, na=False)]
            if cat_filter != "הכל":
                filtered = filtered[filtered["category"] == cat_filter]
            if stat_filter != "הכל":
                filtered = filtered[filtered["status"] == stat_filter]
            
            def highlight(row):
                if row['status'] == 'מלאי נמוך': return ['background-color: #4a0e0e; color: #ffcccc'] * len(row)
                if row['status'] == 'פג תוקף': return ['background-color: #6b21a8; color: #e9d5ff'] * len(row)
                if row['status'] == 'קרוב לתפוגה': return ['background-color: #854d0e; color: #fde68a'] * len(row)
                return [''] * len(row)

            st.dataframe(filtered[["id", "item_name", "catalog_number", "vendor", "category", "location", "quantity", "unit", "min_quantity", "expiry_date", "status"]].style.apply(highlight, axis=1), use_container_width=True, hide_index=True)
            
            st.markdown("### 🔄 עדכון כמות מהיר")
            col_u1, col_u2, col_u3 = st.columns([2, 1, 1])
            item_up = col_u1.selectbox("בחר פריט לעדכון:", filtered["item_name"].unique() if not filtered.empty else [])
            current_q = int(df_inv[df_inv['item_name']==item_up]['quantity'].iloc[0]) if item_up else 0
            new_q = col_u2.number_input("כמות חדשה במלאי:", min_value=0, value=current_q)
            if col_u3.button("עדכן מלאי", use_container_width=True):
                cursor.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (new_q, item_up))
                conn.commit()
                st.success(f"הכמות של {item_up} עודכנה!")
                st.rerun()

    with tab_add:
        st.subheader("הוספת פריט חדש")
        with st.form("add_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("שם הפריט / החומר:")
            cat_no = c1.text_input("מספר קטלוגי:")
            vend = c1.text_input("חברה / ספק:")
            cat = c2.selectbox("קטגוריה:", ["נוגדנים", "קיטים", "כימיקלים", "תרביות תאים", "מתכלים", "אחר"])
            loc = c2.text_input("מיקום במעבדה:")
            qty = c2.number_input("כמות התחלתית:", min_value=0, value=1)
            min_q = c2.number_input("כמות מינימלית להתראה:", min_value=0, value=1)
            exp = c2.date_input("תאריך תפוגה (אופציונלי):", value=None)
            if st.form_submit_button("➕ הוסף למלאי"):
                if name:
                    exp_str = exp.strftime('%Y-%m-%d') if exp else None
                    cursor.execute("INSERT INTO inventory (item_name, catalog_number, vendor, category, location, quantity, unit, min_quantity, expiry_date) VALUES (?,?,?,?,?,?,?,?,?)", (name, cat_no, vend, cat, loc, qty, "יחידות", min_q, exp_str))
                    conn.commit()
                    st.success(f"הפריט {name} נוסף בהצלחה!")
                    st.rerun()
                else: st.error("חובה להזין שם פריט.")

    with tab_orders:
        st.subheader("📝 ניהול בקשות הזמנה")
        with st.expander("➕ פתח בקשת הזמנה חדשה"):
            with st.form("o_form"):
                oname = st.text_input("שם החומר המבוקש:")
                ouser = st.text_input("שם החוקר המזמין:")
                oqty = st.number_input("כמות מבוקשת:", min_value=1)
                if st.form_submit_button("שלח בקשה"):
                    cursor.execute("INSERT INTO orders (item_name, requested_by, quantity, status, date_requested) VALUES (?,?,?,'ממתין',?)", (oname, ouser, oqty, datetime.today().strftime('%Y-%m-%d')))
                    conn.commit()
                    st.success("בקשת ההזמנה נשלחה!")
                    st.rerun()
        
        st.markdown("### לוח מעקב הזמנות")
        df_o = pd.read_sql_query("SELECT * FROM orders", conn)
        if not df_o.empty:
            st.dataframe(df_o[["id", "item_name", "requested_by", "quantity", "status", "date_requested"]], use_container_width=True, hide_index=True)
        else:
            st.info("אין הזמנות פתוחות.")

    with tab_dashboard:
        st.subheader("📊 דאשבורד וסטטיסטיקות")
        df_d = pd.read_sql_query("SELECT * FROM inventory", conn)
        if not df_d.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("סה\"כ פריטים", len(df_d))
            c2.metric("מלאי נמוך", len(df_d[df_d['quantity'] <= df_d['min_quantity']]))
            c3.metric("פגי תוקף", len(df_d[pd.to_datetime(df_d['expiry_date'], errors='coerce').dt.date < datetime.now().date()]))
            
            st.markdown("### התפלגות לפי קטגוריות")
            st.bar_chart(df_d['category'].value_counts())
