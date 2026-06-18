import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. הגדרות דף ועיצוב מותאם אישית (Custom CSS)
st.set_page_config(page_title="LabInventory Pro", layout="wide", initial_sidebar_state="expanded")

custom_css = """
<style>
    /* רקע כללי של האפליקציה */
    .stApp { background-color: #0f172a; color: #f8fafc; }

    /* עיצוב הלשוניות (Tabs) */
    .stTabs [data-baseweb="tab"] p { color: #cbd5e1 !important; font-size: 1.1rem; }
    .stTabs [aria-selected="true"] p { color: #0f172a !important; font-weight: bold !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1e293b; border-radius: 12px; padding: 5px; }
    .stTabs [aria-selected="true"] { background-color: #2dd4bf !important; border-radius: 8px !important; }

    /* דריסה מוחלטת של כפתורי המערכת - הפיכתם לכרטיסים כהים וגדולים */
    div[data-testid="stButton"] > button {
        background-color: #1e293b !important;
        color: #2dd4bf !important;
        border: 2px solid #334155 !important;
        border-radius: 15px !important;
        min-height: 140px !important;
        width: 100% !important;
        padding: 20px !important;
        font-size: 1.4rem !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    div[data-testid="stButton"] > button:focus,
    div[data-testid="stButton"] > button:active,
    div[data-testid="stButton"] > button:focus-visible,
    div[data-testid="stButton"] > button:focus-within {
        background-color: #1e293b !important;
        color: #2dd4bf !important;
        border-color: #334155 !important;
    }

    div[data-testid="stButton"] > button:hover {
        border-color: #2dd4bf !important;
        background-color: #243049 !important;
        color: #5eead4 !important;
        transform: translateY(-4px) !important;
        box-shadow: 0 10px 20px rgba(45, 212, 191, 0.15) !important;
    }

    div[data-testid="stButton"] > button p {
        color: #2dd4bf !important;
        font-size: 1.4rem !important;
        font-weight: bold !important;
    }

    /* כפתורים "קטנים" (לא כרטיסי קטגוריה) - חזרה, פעולות על פריטים/הזמנות */
    .small-btn div[data-testid="stButton"] > button {
        min-height: auto !important;
        padding: 8px 16px !important;
        font-size: 0.95rem !important;
    }
    .small-btn div[data-testid="stButton"] > button p {
        font-size: 0.95rem !important;
    }

    /* כרטיסי פריטים בתוך הקטגוריות */
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
    .item-card.low-stock { border-right-color: #a855f7 !important; background: #281e3a; }

    /* כרטיסי הזמנות */
    .order-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 18px;
        border-right: 6px solid #64748b;
        margin-bottom: 12px;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        color: #0f172a;
    }
    .low-stock-banner {
        background: #281e3a;
        border-right: 6px solid #a855f7;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }

    label, .stMarkdown p { color: #cbd5e1 !important; }
    h1, h2, h3 { color: #2dd4bf !important; font-family: 'Segoe UI', sans-serif; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# צבעי תגיות לסטטוס הזמנה
STATUS_COLORS = {
    "ממתין לאישור": "#f59e0b",
    "הוזמן": "#3b82f6",
    "התקבל": "#22c55e",
    "בוטל": "#ef4444",
}

# 2. חיבור לבסיס נתונים (SQLite)
conn = sqlite3.connect("lab_storage_pro.db", check_same_thread=False)
cursor = conn.cursor()
conn.execute("PRAGMA journal_mode=WAL")

cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, icon TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, category TEXT,
    location TEXT, quantity INTEGER, expiry_date TEXT, catalog_number TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    category TEXT,
    catalog_number TEXT,
    supplier TEXT,
    quantity_requested INTEGER,
    status TEXT DEFAULT 'ממתין לאישור',
    request_date TEXT,
    expected_date TEXT,
    received_date TEXT,
    notes TEXT,
    inventory_item_id INTEGER)''')
conn.commit()


def add_column_if_missing(table, column, col_def):
    """מיגרציה רכה: מוסיף עמודה חדשה לטבלה קיימת אם היא לא קיימת, בלי לאבד מידע."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if column not in existing_cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        conn.commit()


add_column_if_missing("inventory", "min_quantity", "INTEGER DEFAULT 0")
add_column_if_missing("inventory", "supplier", "TEXT")

# הכנסת קטגוריות ברירת מחדל אם ריק
cursor.execute("SELECT COUNT(*) FROM categories")
if cursor.fetchone()[0] == 0:
    defaults = [("נוגדנים", "🧬"), ("כימיקלים", "🧪"), ("מתכלים", "📦"), ("כללי", "🛠️")]
    cursor.executemany("INSERT INTO categories (name, icon) VALUES (?, ?)", defaults)
    conn.commit()

# 3. ניהול סשן לניווט
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'reorder_prefill' not in st.session_state:
    st.session_state.reorder_prefill = None

# --- ממשק ראשי ---
st.title("🧪 LabInventory Pro - ניהול חכם")

tab_manage, tab_dash = st.tabs(["🛒 ניהול והזמנות", "📊 דאשבורד ומעקב תפוגה"])

# ----------------- לשונית 1: ניהול והזמנות -----------------
with tab_manage:
    sub_tab_inventory, sub_tab_orders = st.tabs(["📦 ניהול מלאי", "🛒 הזמנות"])

    # ===================== תת-לשונית: ניהול מלאי =====================
    with sub_tab_inventory:
        if st.session_state.selected_category:
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)
            if st.button("⬅️ חזרה לכל הקטגוריות"):
                st.session_state.selected_category = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.selected_category is None:
            st.subheader("בחר קטגוריה לניהול המלאי:")

            df_cats = pd.read_sql_query("SELECT * FROM categories", conn)
            cols = st.columns(3)

            for idx, row in df_cats.iterrows():
                with cols[idx % 3]:
                    button_text = f"{row['icon']}  {row['name']}"
                    if st.button(button_text, key=f"cat_btn_{row['id']}", use_container_width=True):
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
                        except sqlite3.IntegrityError:
                            st.error("הקטגוריה כבר קיימת")

                del_cat = c2.selectbox("בחר קטגוריה למחיקה:", df_cats['name'].tolist())
                if c2.button("🗑️ מחק קטגוריה", use_container_width=True):
                    cursor.execute("SELECT COUNT(*) FROM inventory WHERE category = ?", (del_cat,))
                    items_in_cat = cursor.fetchone()[0]
                    if items_in_cat > 0:
                        st.error(f"לא ניתן למחוק - יש {items_in_cat} פריטים בקטגוריה זו. העברי או מחקי אותם קודם.")
                    else:
                        cursor.execute("DELETE FROM categories WHERE name = ?", (del_cat,))
                        conn.commit()
                        st.warning(f"הקטגוריה {del_cat} נמחקה")
                        st.rerun()

        else:
            cat_name = st.session_state.selected_category
            st.subheader(f"ניהול פריטים בקטגוריית: {cat_name}")

            with st.expander(f"➕ הוספת פריט חדש ל-{cat_name}"):
                with st.form("add_item"):
                    c_i1, c_i2 = st.columns(2)
                    i_name = c_i1.text_input("שם הפריט / החומר:")
                    i_cat_no = c_i1.text_input("מספר קטלוגי (Cat No.):")
                    i_supplier = c_i1.text_input("ספק:")
                    i_loc = c_i2.text_input("מיקום פיזי (לדוגמה: Freezer -20C, Box B):")
                    i_qty = c_i2.number_input("כמות במלאי:", min_value=0, value=1)
                    i_min_qty = c_i2.number_input("כמות מינימלית להתראת מלאי נמוך (0 = ללא התראה):", min_value=0, value=0)
                    i_exp = st.date_input("תאריך תפוגה (פג תוקף):", value=None)

                    if st.form_submit_button("💾 שמור פריט במערכת", use_container_width=True):
                        if not i_name:
                            st.error("יש להזין שם פריט.")
                        else:
                            exp_s = i_exp.strftime('%Y-%m-%d') if i_exp else "אין תפוגה"
                            cursor.execute(
                                "INSERT INTO inventory (item_name, category, location, quantity, expiry_date, catalog_number, min_quantity, supplier) VALUES (?,?,?,?,?,?,?,?)",
                                (i_name, cat_name, i_loc, i_qty, exp_s, i_cat_no, i_min_qty, i_supplier))
                            conn.commit()
                            st.success("הפריט נוסף בהצלחה!")
                            st.rerun()

            df_items = pd.read_sql_query("SELECT * FROM inventory WHERE category = ?", conn, params=(cat_name,))
            if df_items.empty:
                st.info("אין עדיין פריטים בקטגוריה זו. לחצי על הפלוס למעלה כדי להוסיף.")
            else:
                today = datetime.today()
                for _, item in df_items.iterrows():
                    card_class = "item-card"
                    status_tags = []

                    if item['expiry_date'] and item['expiry_date'] != "אין תפוגה":
                        try:
                            exp_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d')
                            days_to_expire = (exp_date - today).days
                            if days_to_expire < 0:
                                card_class = "item-card expired"
                                status_tags.append("❌ פג תוקף!")
                            elif days_to_expire <= 30:
                                card_class = "item-card warning"
                                status_tags.append(f"⚠️ עומד לפוג (בעוד {days_to_expire} ימים)")
                        except ValueError:
                            pass

                    min_q = item['min_quantity'] if pd.notna(item['min_quantity']) else 0
                    if min_q and min_q > 0 and item['quantity'] <= min_q:
                        if card_class == "item-card":
                            card_class = "item-card low-stock"
                        status_tags.append(f"📉 מלאי נמוך (סף: {int(min_q)})")

                    status_text = " | ".join(status_tags)
                    supplier_text = f" | 🏭 ספק: {item['supplier']}" if item['supplier'] else ""

                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b style="color: #2dd4bf; font-size: 1.3rem;">{item['item_name']}</b>
                            <span style="background: #334155; padding: 4px 10px; border-radius: 20px; font-size: 0.9rem;">📍 {item['location']}</span>
                        </div>
                        <div style="font-size: 0.95rem; margin-top: 10px; color: #cbd5e1;">
                            🔢 כמות: <b>{item['quantity']}</b> | 🔖 קטלוג: {item['catalog_number']} | 📅 תפוגה: {item['expiry_date']}{supplier_text} <b style="color:#ef4444;">{status_text}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    new_q = c1.number_input("עדכון כמות מהיר:", min_value=0, value=int(item['quantity']), key=f"q_{item['id']}", label_visibility="collapsed")

                    if c2.button("🔄 עדכן", key=f"up_{item['id']}", use_container_width=True):
                        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_q, item['id']))
                        conn.commit()
                        st.rerun()
                    if c3.button("🗑️ מחק", key=f"del_{item['id']}", use_container_width=True):
                        cursor.execute("DELETE FROM inventory WHERE id = ?", (item['id'],))
                        conn.commit()
                        st.rerun()
                    if c4.button("🛒 הזמן", key=f"reorder_{item['id']}", use_container_width=True):
                        suggested_qty = int(min_q * 2 - item['quantity']) if min_q and min_q > 0 else 1
                        st.session_state.reorder_prefill = {
                            "item_name": item['item_name'],
                            "category": item['category'],
                            "catalog_number": item['catalog_number'],
                            "supplier": item['supplier'] or "",
                            "inventory_item_id": int(item['id']),
                            "suggested_qty": max(suggested_qty, 1),
                        }
                        st.info("✅ הפריט נוסף לטופס הזמנה - עברי ללשונית '🛒 הזמנות' להשלים ולשלוח.")
                st.markdown("<br>", unsafe_allow_html=True)

    # ===================== תת-לשונית: הזמנות =====================
    with sub_tab_orders:
        st.subheader("🛒 ניהול הזמנות")

        # --- התראות מלאי נמוך עם קיצור דרך להזמנה ---
        df_low_stock = pd.read_sql_query(
            "SELECT * FROM inventory WHERE min_quantity > 0 AND quantity <= min_quantity", conn)
        if not df_low_stock.empty:
            st.markdown("#### 📉 פריטים במלאי נמוך - מומלץ להזמין")
            for _, item in df_low_stock.iterrows():
                lc1, lc2 = st.columns([4, 1])
                with lc1:
                    st.markdown(f"""
                    <div class="low-stock-banner">
                        <b style="color:#a855f7;">{item['item_name']}</b> ({item['category']}) -
                        כמות נוכחית: <b>{item['quantity']}</b> | סף התראה: <b>{int(item['min_quantity'])}</b>
                    </div>
                    """, unsafe_allow_html=True)
                with lc2:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("🛒 הזמן עכשיו", key=f"quickorder_{item['id']}", use_container_width=True):
                        suggested_qty = int(item['min_quantity'] * 2 - item['quantity'])
                        st.session_state.reorder_prefill = {
                            "item_name": item['item_name'],
                            "category": item['category'],
                            "catalog_number": item['catalog_number'],
                            "supplier": item['supplier'] or "",
                            "inventory_item_id": int(item['id']),
                            "suggested_qty": max(suggested_qty, 1),
                        }
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")

        # --- טופס הזמנה חדשה (כולל מילוי מוקדם אם הופעל מקיצור דרך) ---
        prefill = st.session_state.reorder_prefill
        expander_label = "📝 הזמנה חדשה" if not prefill else f"📝 הזמנת חידוש מלאי: {prefill['item_name']}"
        with st.expander(expander_label, expanded=bool(prefill)):
            df_cats_o = pd.read_sql_query("SELECT * FROM categories", conn)
            cat_names = df_cats_o['name'].tolist()

            with st.form("new_order_form", clear_on_submit=True):
                oc1, oc2 = st.columns(2)
                o_name = oc1.text_input("שם הפריט:", value=prefill['item_name'] if prefill else "")
                o_cat_no = oc1.text_input("מספר קטלוגי:", value=prefill['catalog_number'] if prefill else "")
                o_supplier = oc1.text_input("ספק:", value=prefill['supplier'] if prefill else "")
                default_cat_idx = cat_names.index(prefill['category']) if prefill and prefill['category'] in cat_names else 0
                o_cat = oc2.selectbox("קטגוריה:", cat_names, index=default_cat_idx if cat_names else 0)
                o_qty = oc2.number_input("כמות לבקש:", min_value=1, value=prefill['suggested_qty'] if prefill else 1)
                o_expected = oc2.date_input("תאריך משוער להגעה (אופציונלי):", value=None)
                o_notes = st.text_area("הערות (אופציונלי):")

                if st.form_submit_button("📤 שלח הזמנה", use_container_width=True):
                    if not o_name:
                        st.error("יש להזין שם פריט.")
                    else:
                        # ניסיון לקשר אוטומטית לפריט קיים במלאי (לפי שם + קטגוריה)
                        linked_id = prefill['inventory_item_id'] if prefill else None
                        if linked_id is None:
                            match = cursor.execute(
                                "SELECT id FROM inventory WHERE item_name = ? AND category = ?",
                                (o_name, o_cat)).fetchone()
                            if match:
                                linked_id = match[0]

                        expected_s = o_expected.strftime('%Y-%m-%d') if o_expected else None
                        cursor.execute("""INSERT INTO orders
                            (item_name, category, catalog_number, supplier, quantity_requested,
                             status, request_date, expected_date, notes, inventory_item_id)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (o_name, o_cat, o_cat_no, o_supplier, o_qty, "ממתין לאישור",
                             datetime.today().strftime('%Y-%m-%d'), expected_s, o_notes, linked_id))
                        conn.commit()
                        st.session_state.reorder_prefill = None
                        st.success("ההזמנה נשלחה ונמצאת בסטטוס 'ממתין לאישור'.")
                        st.rerun()

            if prefill:
                st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                if st.button("❌ ביטול מילוי מוקדם", key="cancel_prefill"):
                    st.session_state.reorder_prefill = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # --- הזמנות פעילות ---
        df_orders = pd.read_sql_query("SELECT * FROM orders ORDER BY request_date DESC, id DESC", conn)
        df_active = df_orders[df_orders['status'].isin(["ממתין לאישור", "הוזמן"])]
        df_done = df_orders[df_orders['status'].isin(["התקבל", "בוטל"])]

        st.markdown(f"#### 📋 הזמנות פעילות ({len(df_active)})")
        if df_active.empty:
            st.info("אין הזמנות פעילות כרגע.")
        else:
            for _, order in df_active.iterrows():
                badge_color = STATUS_COLORS.get(order['status'], "#64748b")
                expected_text = f" | 🚚 צפי: {order['expected_date']}" if order['expected_date'] else ""
                notes_text = f"<br>📝 {order['notes']}" if order['notes'] else ""

                st.markdown(f"""
                <div class="order-card" style="border-right-color: {badge_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#2dd4bf; font-size:1.15rem;">{order['item_name']}</b>
                        <span class="status-badge" style="background:{badge_color};">{order['status']}</span>
                    </div>
                    <div style="font-size:0.95rem; margin-top:8px; color:#cbd5e1;">
                        🏷️ {order['category']} | 🔢 כמות: <b>{order['quantity_requested']}</b> | 🏭 ספק: {order['supplier'] or '-'} |
                        🔖 קטלוג: {order['catalog_number'] or '-'} | 📅 בוקש: {order['request_date']}{expected_text}{notes_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                oc1, oc2, oc3 = st.columns([1, 1, 4])
                st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                if order['status'] == "ממתין לאישור":
                    if oc1.button("📦 סמן כהוזמן", key=f"mark_ordered_{order['id']}", use_container_width=True):
                        cursor.execute("UPDATE orders SET status='הוזמן' WHERE id=?", (order['id'],))
                        conn.commit()
                        st.rerun()
                elif order['status'] == "הוזמן":
                    if oc1.button("✅ סמן כהתקבל", key=f"mark_received_{order['id']}", use_container_width=True):
                        today_s = datetime.today().strftime('%Y-%m-%d')
                        if order['inventory_item_id'] and pd.notna(order['inventory_item_id']):
                            cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
                                           (order['quantity_requested'], int(order['inventory_item_id'])))
                        else:
                            match = cursor.execute(
                                "SELECT id FROM inventory WHERE item_name = ? AND category = ?",
                                (order['item_name'], order['category'])).fetchone()
                            if match:
                                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
                                               (order['quantity_requested'], match[0]))
                            else:
                                cursor.execute("""INSERT INTO inventory
                                    (item_name, category, location, quantity, expiry_date, catalog_number, min_quantity, supplier)
                                    VALUES (?,?,?,?,?,?,?,?)""",
                                    (order['item_name'], order['category'], "⚠️ יש להגדיר מיקום",
                                     order['quantity_requested'], "אין תפוגה", order['catalog_number'], 0, order['supplier']))
                        cursor.execute("UPDATE orders SET status='התקבל', received_date=? WHERE id=?",
                                       (today_s, order['id']))
                        conn.commit()
                        st.success("המלאי עודכן אוטומטית!")
                        st.rerun()

                if oc2.button("❌ בטל", key=f"cancel_order_{order['id']}", use_container_width=True):
                    cursor.execute("UPDATE orders SET status='בוטל' WHERE id=?", (order['id'],))
                    conn.commit()
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with st.expander(f"📜 היסטוריית הזמנות שהושלמו/בוטלו ({len(df_done)})"):
            if df_done.empty:
                st.info("אין עדיין הזמנות שהושלמו.")
            else:
                for _, order in df_done.iterrows():
                    badge_color = STATUS_COLORS.get(order['status'], "#64748b")
                    date_label = "התקבל" if order['status'] == "התקבל" else "עודכן"
                    date_val = order['received_date'] if order['status'] == "התקבל" else order['request_date']
                    st.markdown(f"""
                    <div class="order-card" style="border-right-color:{badge_color}; opacity:0.8;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>{order['item_name']}</b>
                            <span class="status-badge" style="background:{badge_color};">{order['status']}</span>
                        </div>
                        <div style="font-size:0.9rem; margin-top:6px; color:#cbd5e1;">
                            🏷️ {order['category']} | 🔢 כמות: {order['quantity_requested']} | 📅 {date_label}: {date_val or '-'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ----------------- לשונית 2: דאשבורד ומעקב תפוגה -----------------
with tab_dash:
    st.subheader("📊 ניתוח ומצב המלאי במעבדה")

    df_all = pd.read_sql_query("SELECT * FROM inventory", conn)
    df_orders_all = pd.read_sql_query("SELECT * FROM orders", conn)
    open_orders_count = len(df_orders_all[df_orders_all['status'].isin(["ממתין לאישור", "הוזמן"])]) if not df_orders_all.empty else 0
    low_stock_count = len(df_all[(df_all['min_quantity'] > 0) & (df_all['quantity'] <= df_all['min_quantity'])]) if not df_all.empty else 0

    if df_all.empty:
        st.info("אין עדיין נתונים במערכת כדי לייצר דאשבורד.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("סה\"כ פריטים שונים במערכת", len(df_all))
        m2.metric("סה\"כ יחידות מלאי כולל", int(df_all['quantity'].sum()))
        m3.metric("📉 פריטים במלאי נמוך", low_stock_count)
        m4.metric("🛒 הזמנות פתוחות", open_orders_count)

        st.markdown("---")
        st.markdown("### 📦 התפלגות חומרים לפי קטגוריות")
        st.bar_chart(df_all['category'].value_counts())

        if open_orders_count > 0:
            st.markdown("### 🛒 סטטוס הזמנות פתוחות")
            df_open = df_orders_all[df_orders_all['status'].isin(["ממתין לאישור", "הוזמן"])][
                ['item_name', 'category', 'quantity_requested', 'status', 'supplier', 'request_date']]
            df_open.columns = ['פריט', 'קטגוריה', 'כמות', 'סטטוס', 'ספק', 'תאריך בקשה']
            st.dataframe(df_open, use_container_width=True, hide_index=True)

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
