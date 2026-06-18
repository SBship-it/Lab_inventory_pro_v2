import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta

# 1. הגדרות דף ועיצוב מותאם אישית (Custom CSS) למראה יוקרתי
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    /* עיצוב רקע כללי וגופנים */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
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
    
    /* עיצוב שורות מלאי נמוך */
    .low-stock-row {
        background-color: #4a0e0e !important; /* כהה יותר, אדום עמוק */
        color: #ffcccc !important;
    }
    
    /* עיצוב שורות פג תוקף */
    .expired-row {
        background-color: #6b21a8 !important; /* סגול כהה */
        color: #e9d5ff !important;
    }
    
    /* עיצוב שורות קרוב לתפוגה */
    .expiring-soon-row {
        background-color: #854d0e !important; /* כתום כהה */
        color: #fde68a !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. פונקציות אבטחה והצפנת סיסמאות
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# 3. חיבור לבסיס הנתונים (שומר את המידע לצמיתות בקובץ מקומי)
conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()

# יצירת טבלאות (מלאי, הזמנות, משתמשים ומצב מנוי)
# עדכון טבלת inventory עם min_quantity כ-INTEGER ו-expiry_date
cursor.execute("PRAGMA table_info(inventory)")
columns = [col[1] for col in cursor.fetchall()]

# יצירת טבלאות (מלאי, הזמנות, משתמשים)
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


cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT, catalog_number TEXT, vendor TEXT,
        category TEXT, location TEXT, quantity INTEGER, unit TEXT, min_quantity INTEGER, expiry_date TEXT
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

# יצירת משתמש מנהל ברירת מחדל לבדיקה (שם משתמש: admin, סיסמה: lab2026)
try:
    cursor.execute('INSERT INTO users (username, password, account_status) VALUES (?, ?, ?)', 
                   ("admin", make_hashes("lab2026"), "active"))
    conn.commit()
except sqlite3.IntegrityError:
    pass

# 4. מנגנון ניהול סשן (Session State)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- מסך התחברות מאובטח ---
if not st.session_state['logged_in']:
    st.title("🧪 LabInventory Pro")
    st.subheader("מערכת ניהול מלאי והזמנות מעבדה ברמה ארגונית")
    
    col_login, _ = st.columns([1, 1])
    with col_login:
        with st.form("login_form"):
            st.markdown("### כניסת חוקרים ומנהלים")
            user = st.text_input("שם משתמש")
            passwd = st.text_input("סיסמה", type='password')
            login_btn = st.form_submit_button("התחבר למערכת")
            
            if login_btn:
                cursor.execute('SELECT password, account_status FROM users WHERE username = ?', (user,))
                user_data = cursor.fetchone()
                if user_data and check_hashes(passwd, user_data[0]):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")
                    
    st.markdown("---")
    st.info("💡 משתמש בדיקה מובנה במערכת: שם משתמש `admin` | סיסמה `lab2026`")

# --- המערכת המרכזית (לאחר התחברות) ---
else:
    # סרגל צדי (Sidebar) לפרופיל והתנתקות
    st.sidebar.markdown(f"### 👋 שלום, {st.session_state['username']}")
    
    # סימולציה של בדיקת סטטוס מנוי (כאן יתחבר הקישור ל-Stripe בעתיד)
    cursor.execute('SELECT account_status FROM users WHERE username = ?', (st.session_state['username'],))
    account_status = cursor.fetchone()[0]
    
    st.sidebar.markdown(f"**סטטוס חשבון:** המנוי פעיל 👑" if account_status == "active" else "**סטטוס חשבון:** גרסה חינמית")
    
    if st.sidebar.button("🚪 התנתק מהמערכת", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    # כותרת האפליקציה
    st.title("🧪 LabInventory Pro - מרכז ניהול מעבדה")
    st.markdown("---")
    
    # חלוקה ללשוניות מעוצבות
    tab_inv, tab_add, tab_orders, tab_dashboard = st.tabs(["📦 מלאי המחסן והמעבדה", "➕ הוספת פריט חדש למלאי", "🛒 עגלת הזמנות ומעקב", "📊 דאשבורד וסטטיסטיקות"])
    
    # ----------------- לשונית 1: מלאי המחסן -----------------
    with tab_inv:
        st.subheader("חיפוש וניהול פריטים במלאי")
        
        # שליפת המידע מבסיס הנתונים
        df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
        
        if df_inv.empty:
            st.info("המחסן ריק כרגע. עברי ללשונית 'הוספת פריט חדש' כדי להזין את הציוד הראשון.")
        else:
            # הוספת עמודות סטטוס למלאי
            df_inv['status'] = 'רגיל'
            today = datetime.now().date()
            
            # בדיקת תאריכי תפוגה
            df_inv['expiry_date'] = pd.to_datetime(df_inv['expiry_date'], errors='coerce')
            df_inv.loc[df_inv['expiry_date'].notna() & (df_inv['expiry_date'].dt.date < today), 'status'] = 'פג תוקף'
            df_inv.loc[df_inv['expiry_date'].notna() & (df_inv['expiry_date'].dt.date >= today) & (df_inv['expiry_date'].dt.date < today + timedelta(days=30)), 'status'] = 'קרוב לתפוגה'
            
            # בדיקת מלאי נמוך (רק לפריטים שאינם פגי תוקף או קרובים לתפוגה)
            df_inv.loc[(df_inv['quantity'] <= df_inv['min_quantity']) & (df_inv['status'] == 'רגיל'), 'status'] = 'מלאי נמוך'

            # שורת חיפוש חכמה
            col_search, col_filter, col_status_filter = st.columns([2, 1, 1])
            with col_search:
                search_query = st.text_input("🔍 חפש לפי שם חומר, נוגדן או מספר קטלוגי:")
            with col_filter:
                categories = ["הכל"] + list(df_inv["category"].unique())
                selected_cat = st.selectbox("סנן לפי קטגוריה:", categories)
            with col_status_filter:
                statuses = ["הכל"] + list(df_inv["status"].unique())
                selected_status = st.selectbox("סנן לפי סטטוס:", statuses)
            
            # סינון הנתונים בהתאם לחיפוש
            filtered_df = df_inv.copy()
            if search_query:
                filtered_df = filtered_df[
                    filtered_df["item_name"].str.contains(search_query, case=False, na=False) |
                    filtered_df["catalog_number"].str.contains(search_query, case=False, na=False)
                ]
            if selected_cat != "הכל":
                filtered_df = filtered_df[filtered_df["category"] == selected_cat]
            if selected_status != "הכל":
                filtered_df = filtered_df[filtered_df["status"] == selected_status]
            
            # פונקציה לעיצוב שורות בטבלה
            def highlight_rows(row):
                if row['status'] == 'מלאי נמוך':
                    return ['background-color: #4a0e0e; color: #ffcccc'] * len(row) # אדום כהה
                elif row['status'] == 'פג תוקף':
                    return ['background-color: #6b21a8; color: #e9d5ff'] * len(row) # סגול כהה
                elif row['status'] == 'קרוב לתפוגה':
                    return ['background-color: #854d0e; color: #fde68a'] * len(row) # כתום כהה
                return [''] * len(row)

            # הצגת טבלה בעיצוב נקי עם סטטוסים
            st.dataframe(
                filtered_df[["id", "item_name", "catalog_number", "vendor", "category", "location", "quantity", "unit", "min_quantity", "expiry_date", "status"]]
                .style.apply(highlight_rows, axis=1),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "expiry_date": st.column_config.DateColumn("תאריך תפוגה", format="YYYY-MM-DD"),
                    "min_quantity": "כמות מינימלית",
                    "status": "סטטוס"
                }
            )
            
            # כפתור ייצוא ל-CSV
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ ייצוא מלאי ל-CSV",
                data=csv_data,
                file_name="lab_inventory.csv",
                mime="text/csv",
                use_container_width=True
            )

            # עדכון מהיר של כמויות (למשל כשחוקר לוקח בקבוק מהמקרר)
            st.markdown("### 🔄 עדכון כמות מהיר")
            col_up_name, col_up_qty, col_up_btn = st.columns([2, 1, 1])
            with col_up_name:
                item_to_update = st.selectbox("בחר פריט לעדכון:", filtered_df["item_name"].unique())
            with col_up_qty:
                current_qty = df_inv[df_inv['item_name'] == item_to_update]['quantity'].iloc[0] if item_to_update else 0
                new_qty = st.number_input("כמות מעודכנת במלאי:", min_value=0, value=int(current_qty), step=1)
            with col_up_btn:
                st.write("<br>", unsafe_allow_html=True)
                if st.button("עדכן מלאי", use_container_width=True):
                    cursor.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (new_qty, item_to_update))
                    conn.commit()
                    st.success(f"הכמות עבור {item_to_update} עודכנה ל-{new_qty}")
                    st.rerun()

    # ----------------- לשונית 2: הוספת פריט -----------------
    with tab_add:
        st.subheader("הוספת חומר או ציוד חדש למערכת")
        
        with st.form("add_item_form"):
            col1, col2 = st.columns(2)
            with col1:
                item_name = st.text_input("שם הפריט / החומר (לדוגמה: Anti-GFP Antibody, Trizol):")
                catalog_number = st.text_input("מספר קטלוגי (Cat No.):")
                vendor = st.text_input("חברה / ספק (לדוגמה: Abcam, Thermo, Sigma):")
            with col2:
                category = st.selectbox("קטגוריה:", ["נוגדנים (Antibodies)", "קיטים (Kits)", "כימיקלים (Chemicals)", "תרביות תאים (Cell Culture)", "מתכלים ופלסטיקה", "אחר"])
                location = st.text_input("מיקום מדויק (לדוגמה: Freezer -80C Rack A3, Shelf B2):")
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    quantity = st.number_input("כמות התחלתית:", min_value=0, value=1)
                with col_q2:
                    unit = st.selectbox("יחידות:", ["בקבוקים", "מבחנות", "קופסאות", "אליקווטים", "מ\"ל"])
                min_quantity = st.number_input("כמות מינימלית להתראה:", min_value=0, value=1)
                expiry_date = st.date_input("תאריך תפוגה (אופציונלי):", value=None)
            
            submit_btn = st.form_submit_button("➕ הוסף למלאי המעבדה")
            
            if submit_btn:
                if item_name:
                    expiry_date_str = expiry_date.strftime('%Y-%m-%d') if expiry_date else None
                    cursor.execute('''
                        INSERT INTO inventory (item_name, catalog_number, vendor, category, location, quantity, unit, min_quantity, expiry_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (item_name, catalog_number, vendor, category, location, quantity, unit, min_quantity, expiry_date_str))
                    conn.commit()
                    st.success(f"החומר '{item_name}' נקלט בהצלחה בבסיס הנתונים!")
                    st.rerun()
                else:
                    st.error("חובה להזין את שם החומר.")

    # ----------------- לשונית 3: ניהול הזמנות -----------------
    with tab_orders:
        st.subheader("📝 בקשות הזמנה ומעקב רכש")
        
        # טופס פנימי לחוקרים שרוצים לבקש חומר
        with st.expander("➕ פתיחת בקשת הזמנה חדשה (עבור חוקרי המעבדה)"):
            with st.form("order_form"):
                o_name = st.text_input("שם החומר המבוקש:")
                o_cat = st.text_input("מספר קטלוגי:")
                o_vendor = st.text_input("חברה ספק:")
                o_user = st.text_input("שם החוקר המזמין:")
                o_qty = st.number_input("כמות מבוקשת:", min_value=1, value=1)
                
                order_submit = st.form_submit_button("שלח בקשת הזמנה לאישור מנהל")
                if order_submit:
                    if o_name and o_user:
                        today_str = datetime.today().strftime('%Y-%m-%d')
                        cursor.execute('''
                            INSERT INTO orders (item_name, catalog_number, vendor, requested_by, quantity, status, date_requested)
                            VALUES (?, ?, ?, ?, ?, 'ממתין לאישור', ?)
                        ''', (o_name, o_cat, o_vendor, o_user, o_qty, today_str))
                        conn.commit()
                        st.success("בקשת ההזמנה נרשמה בהצלחה וממתינה לאישור רכש.")
                        st.rerun()
                    else:
                        st.error("נא למלא שם חומר ושם חוקר.")

        # הצגת רשימת ההזמנות הקיימות
        st.markdown("### 📊 לוח מעקב הזמנות")
        df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
        
        if df_orders.empty:
            st.info("אין בקשות הזמנה פתוחות כרגע.")
        else:
            st.dataframe(df_orders[["id", "item_name", "catalog_number", "vendor", "requested_by", "quantity", "status", "date_requested"]], use_container_width=True, hide_index=True)
            
            # כפתור ייצוא ל-CSV
            csv_orders_data = df_orders.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ ייצוא הזמנות ל-CSV",
                data=csv_orders_data,
                file_name="lab_orders.csv",
                mime="text/csv",
                use_container_width=True
            )

            # שינוי סטטוס הזמנה על ידי מנהל המעבדה
            st.markdown("### ⚙️ ניהול סטטוס (למנהלי מעבדה / רכש)")
            col_o_id, col_o_stat, col_o_btn = st.columns([1, 1, 1])
            with col_o_id:
                selected_order_id = st.selectbox("בחר מספר הזמנה (ID):", df_orders["id"].unique())
            with col_o_stat:
                new_status = st.selectbox("עדכן סטטוס ל:", ["ממתין לאישור", "אושר והוזמן", "הגיע למעבדה - סגור"])
            with col_o_btn:
                st.write("<br>", unsafe_allow_html=True)
                if st.button("עדכן סטטוס", use_container_width=True):
                    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, selected_order_id))
                    conn.commit()
                    st.success(f"הזמנה מספר {selected_order_id} עודכנה בהצלחה!")
                    st.rerun()

    # ----------------- לשונית 4: דאשבורד וסטטיסטיקות -----------------
    with tab_dashboard:
        st.subheader("📊 דאשבורד וסטטיסטיקות")
        
        df_inv_dashboard = pd.read_sql_query("SELECT * FROM inventory", conn)
        
        if df_inv_dashboard.empty:
            st.info("אין נתונים להצגה בדאשבורד. אנא הוסף פריטים למלאי.")
        else:
            # גרף התפלגות מלאי לפי קטגוריה
            st.markdown("### התפלגות פריטים לפי קטגוריה")
            category_counts = df_inv_dashboard['category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            st.bar_chart(category_counts.set_index('Category'))

            # גרף מלאי נמוך ופג תוקף
            st.markdown("### סטטוס מלאי")
            low_stock_count = df_inv_dashboard[df_inv_dashboard['quantity'] <= df_inv_dashboard['min_quantity']].shape[0]
            expired_count = df_inv_dashboard[pd.to_datetime(df_inv_dashboard['expiry_date'], errors='coerce').dt.date < today].shape[0]
            expiring_soon_count = df_inv_dashboard[(pd.to_datetime(df_inv_dashboard['expiry_date'], errors='coerce').dt.date >= today) & (pd.to_datetime(df_inv_dashboard['expiry_date'], errors='coerce').dt.date < today + timedelta(days=30))].shape[0]

            status_data = pd.DataFrame({
                'Status': ['מלאי נמוך', 'פג תוקף', 'קרוב לתפוגה', 'רגיל'],
                'Count': [low_stock_count, expired_count, expiring_soon_count, df_inv_dashboard.shape[0] - low_stock_count - expired_count - expiring_soon_count]
            })
            st.bar_chart(status_data.set_index('Status'))

            # טבלת פריטים במלאי נמוך
            st.markdown("### פריטים במלאי נמוך")
            low_stock_items = df_inv_dashboard[df_inv_dashboard['quantity'] <= df_inv_dashboard['min_quantity']]
            if not low_stock_items.empty:
                st.dataframe(low_stock_items[['item_name', 'quantity', 'min_quantity', 'category', 'location']], use_container_width=True, hide_index=True)
            else:
                st.info("אין פריטים במלאי נמוך כרגע.")

            # טבלת פריטים פגי תוקף או קרובים לתפוגה
            st.markdown("### פריטים פגי תוקף או קרובים לתפוגה")
            expiring_items = df_inv_dashboard[(pd.to_datetime(df_inv_dashboard['expiry_date'], errors='coerce').dt.date < today + timedelta(days=30)) & (pd.to_datetime(df_inv_dashboard['expiry_date'], errors='coerce').notna())]
            if not expiring_items.empty:
                st.dataframe(expiring_items[['item_name', 'expiry_date', 'category', 'location']], use_container_width=True, hide_index=True)
            else:
                st.info("אין פריטים פגי תוקף או קרובים לתפוגה בקרוב.")
