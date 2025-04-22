import streamlit as st
import mysql.connector
from mysql.connector import pooling
import pandas as pd
import re
from datetime import datetime

import { put } from "@vercel/blob";

const { url } = await put('articles/blob.txt', 'Hello World!', { access: 'public' });

# Database Connection Pool
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Tanmaychasql@123",
    "database": "blood_bank",
    "auth_plugin": "mysql_native_password"
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="bb_pool",
    pool_size=5,
    **db_config
)

# Function to execute queries with better error handling
def execute_query(query, values=None, fetch=False):
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if values:
            cursor.execute(query, values)
        else:
            cursor.execute(query)
        
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return True
            
    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Input sanitization function
def sanitize_input(input_str):
    if not input_str:
        return ""
    return re.sub(r"[;'\"]", "", input_str.strip())

# Improved query processing with parameterized queries
def process_query(user_query):
    user_query = sanitize_input(user_query.lower())
    
    patterns = {
        r"available blood$": "SELECT Blood_grp, SUM(Quantity) AS Total_Units FROM Storage_House GROUP BY Blood_grp",
        r"donors with ([a-z0-9+-]+)$": "SELECT * FROM Donor WHERE Blood_grp = %s",
        r"contact of (.+)$": "SELECT Dona_name, Dona_contact FROM Donor WHERE Dona_name LIKE %s",
        r"who donated blood$": "SELECT Dona_name, Blood_grp FROM Donor",
        r"location of blood bank$": "SELECT Emp_name, BB_address FROM Employee",
        r"hospital orders$": "SELECT o.Order_id, h.Hosp_name, o.Blood_grp, o.Quantity, o.Status FROM Orders o JOIN Hospital h ON o.Hosp_id = h.Hosp_id",
        r"blood supply$": "SELECT s.Supply_id, h.Hosp_name, s.Blood_grp, s.Quantity FROM Supply s JOIN Hospital h ON s.Hosp_id = h.Hosp_id"
    }
    
    for pattern, sql_query in patterns.items():
        match = re.search(pattern, user_query)
        if match:
            if "%s" in sql_query:
                param = match.group(1)
                if "blood_grp" in sql_query.lower():
                    param = param.upper()
                elif "dona_name" in sql_query.lower():
                    param = f"%{param}%"
                return (sql_query, [param])
            return (sql_query, None)
    
    return None

# Common form validation functions
def validate_contact(contact):
    return re.match(r"^[0-9]{10}$", contact)

def validate_id(id_str):
    return re.match(r"^[a-zA-Z0-9]+$", id_str)

# Streamlit UI Configuration
st.set_page_config(page_title="Blood Bank Management", layout="wide")

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #dc3545;
        color: white;
        border-radius: 5px;
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 5px;
    }
    .sidebar .sidebar-content {
        background-color: #343a40;
        color: white;
    }
    h1, h2, h3 {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Main App
st.title("🩸 Blood Bank Management System")

menu = st.sidebar.selectbox("MENU", ["Dashboard", "Employees", "Donors", "Hospitals", "Blood Inventory", "Orders", "Supply", "Search Database"])

# Dashboard
if menu == "Dashboard":
    st.header("Blood Bank Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Blood Inventory")
        blood_inventory = execute_query("SELECT Blood_grp, SUM(Quantity) AS Total FROM Storage_House GROUP BY Blood_grp", fetch=True)
        if blood_inventory:
            st.dataframe(pd.DataFrame(blood_inventory).set_index("Blood_grp"), height=300)
    
    with col2:
        st.subheader("Recent Donors")
        recent_donors = execute_query("SELECT Dona_name, Blood_grp, Dona_contact FROM Donor ORDER BY Dona_name LIMIT 5", fetch=True)
        if recent_donors:
            st.dataframe(pd.DataFrame(recent_donors), height=300)
    
    with col3:
        st.subheader("Pending Orders")
        pending_orders = execute_query("SELECT o.Order_id, h.Hosp_name, o.Blood_grp, o.Quantity FROM Orders o JOIN Hospital h ON o.Hosp_id = h.Hosp_id WHERE o.Status = 'Pending' LIMIT 5", fetch=True)
        if pending_orders:
            st.dataframe(pd.DataFrame(pending_orders), height=300)
    
    st.subheader("Recent Activities")
    activities = execute_query("""
        (SELECT 'Order' AS Type, Order_id AS ID, Blood_grp, Quantity, Order_date AS Date FROM Orders ORDER BY Order_date DESC LIMIT 3)
        UNION
        (SELECT 'Supply' AS Type, Supply_id AS ID, Blood_grp, Quantity, Supply_date AS Date FROM Supply ORDER BY Supply_date DESC LIMIT 3)
        ORDER BY Date DESC
    """, fetch=True)
    if activities:
        st.dataframe(pd.DataFrame(activities), height=200)

# Search Feature
elif menu == "Search Database":
    st.header("🔍 Search Blood Bank Database")
    user_query = st.text_input("Ask your question (e.g., 'available blood', 'donors with A+', 'contact of John'):")
    
    if user_query:
        query_info = process_query(user_query)
        if query_info:
            sql_query, params = query_info
            result = execute_query(sql_query, params, fetch=True)
            if result:
                st.write("### Results:")
                df = pd.DataFrame(result)
                st.dataframe(df.style.set_properties(**{'background-color': '#333333'}))
            else:
                st.warning("No relevant data found.")
        else:
            st.error("Invalid query. Try asking about: blood availability, donors, hospital orders, or contact info.")

# Employee Management
elif menu == "Employees":
    st.header("👨‍⚕️ Employee Management")
    
    tab1, tab2 = st.tabs(["View Employees", "Add Employee"])
    
    with tab1:
        employees = execute_query("SELECT * FROM Employee", fetch=True)
        if employees:
            st.dataframe(pd.DataFrame(employees))
    
    with tab2:
        with st.form("add_employee", clear_on_submit=True):
            st.subheader("Add New Employee")
            cols = st.columns(2)
            
            with cols[0]:
                emp_name = st.text_input("Full Name*")
                email = st.text_input("Email*")
                salary = st.number_input("Salary*", min_value=0)
                designation = st.selectbox("Designation*", ["Manager", "Lab Technician", "Nurse", "Receptionist", "Other"])
            
            with cols[1]:
                joining_date = st.date_input("Joining Date*").strftime('%Y-%m-%d')
                bb_contact = st.text_input("Contact Number*")
                bb_id = st.number_input("Blood Bank ID*", min_value=1)
                bb_address = st.text_area("Address*")
            
            submitted = st.form_submit_button("Add Employee")
            
            if submitted:
                if not all([emp_name, email, salary, designation, bb_contact, bb_address]):
                    st.error("Please fill all required fields (*)")
                elif not validate_contact(bb_contact):
                    st.error("Please enter a valid 10-digit phone number")
                else:
                    success = execute_query(
                        """INSERT INTO Employee 
                        (Emp_name, Email, Salary, Designation, Joining_date, BB_contact, BB_id, BB_address) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (emp_name, email, salary, designation, joining_date, bb_contact, bb_id, bb_address)
                    )
                    if success:
                        st.success("Employee added successfully!")
                        st.balloons()

# Donor Management
elif menu == "Donors":
    st.header("🩸 Donor Management")
    
    tab1, tab2 = st.tabs(["View Donors", "Add Donor"])
    
    with tab1:
        donors = execute_query("SELECT * FROM Donor", fetch=True)
        if donors:
            st.dataframe(pd.DataFrame(donors))
    
    with tab2:
        with st.form("add_donor", clear_on_submit=True):
            st.subheader("Register New Donor")
            cols = st.columns(2)
            
            with cols[0]:
                donor_id = st.text_input("Donor ID* (e.g., DON100)")
                donor_name = st.text_input("Full Name*")
            
            with cols[1]:
                donor_blood = st.selectbox("Blood Group*", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                donor_contact = st.text_input("Contact Number*")
            
            submitted = st.form_submit_button("Register Donor")
            
            if submitted:
                if not all([donor_id, donor_name, donor_contact]):
                    st.error("Please fill all required fields (*)")
                elif not validate_id(donor_id):
                    st.error("Invalid Donor ID format (letters and numbers only)")
                elif not validate_contact(donor_contact):
                    st.error("Please enter a valid 10-digit phone number")
                else:
                    success = execute_query(
                        "INSERT INTO Donor (Dona_id, Dona_name, Blood_grp, Dona_contact) VALUES (%s, %s, %s, %s)",
                        (donor_id, donor_name, donor_blood, donor_contact)
                    )
                    if success:
                        st.success("Donor registered successfully!")
                        st.balloons()

# Hospital Management
elif menu == "Hospitals":
    st.header("🏥 Hospital Management")
    
    tab1, tab2 = st.tabs(["View Hospitals", "Add Hospital"])
    
    with tab1:
        hospitals = execute_query("SELECT * FROM Hospital", fetch=True)
        if hospitals:
            st.dataframe(pd.DataFrame(hospitals))
    
    with tab2:
        with st.form("add_hospital", clear_on_submit=True):
            st.subheader("Add New Hospital")
            cols = st.columns(2)
            
            with cols[0]:
                hosp_id = st.text_input("Hospital ID* (e.g., HOSP100)")
                hosp_name = st.text_input("Hospital Name*")
            
            with cols[1]:
                location = st.text_input("Location*")
            
            submitted = st.form_submit_button("Add Hospital")
            
            if submitted:
                if not all([hosp_id, hosp_name, location]):
                    st.error("Please fill all required fields (*)")
                elif not validate_id(hosp_id):
                    st.error("Invalid Hospital ID format (letters and numbers only)")
                else:
                    success = execute_query(
                        "INSERT INTO Hospital (Hosp_id, Hosp_name, Location) VALUES (%s, %s, %s)",
                        (hosp_id, hosp_name, location)
                    )
                    if success:
                        st.success("Hospital added successfully!")
                        st.balloons()

# Blood Inventory Management
elif menu == "Blood Inventory":
    st.header("🧪 Blood Inventory Management")
    
    tab1, tab2 = st.tabs(["View Inventory", "Update Inventory"])
    
    with tab1:
        inventory = execute_query("SELECT * FROM Storage_House", fetch=True)
        if inventory:
            st.dataframe(pd.DataFrame(inventory))
        
        st.subheader("Blood Availability Summary")
        blood_summary = execute_query("""
            SELECT Blood_grp, SUM(Quantity) AS Total_Units 
            FROM Storage_House 
            GROUP BY Blood_grp 
            ORDER BY Total_Units DESC
        """, fetch=True)
        if blood_summary:
            st.bar_chart(pd.DataFrame(blood_summary).set_index("Blood_grp"))
    
    with tab2:
        with st.form("update_inventory", clear_on_submit=True):
            st.subheader("Update Blood Inventory")
            cols = st.columns(2)
            
            with cols[0]:
                storage_id = st.text_input("Storage ID* (e.g., STO100)")
                blood_type = st.selectbox("Blood Type*", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
            
            with cols[1]:
                action = st.radio("Action*", ["Add", "Remove"])
                quantity = st.number_input("Quantity (units)*", min_value=1, max_value=100, value=1)
            
            submitted = st.form_submit_button("Update Inventory")
            
            if submitted:
                if not storage_id:
                    st.error("Please enter a Storage ID")
                else:
                    if action == "Add":
                        # Check if record exists
                        existing = execute_query(
                            "SELECT * FROM Storage_House WHERE Storage_id = %s",
                            (storage_id,),
                            fetch=True
                        )
                        
                        if existing:
                            # Update existing record
                            success = execute_query(
                                "UPDATE Storage_House SET Quantity = Quantity + %s WHERE Storage_id = %s",
                                (quantity, storage_id)
                            )
                        else:
                            # Insert new record
                            success = execute_query(
                                "INSERT INTO Storage_House (Storage_id, Blood_grp, Quantity) VALUES (%s, %s, %s)",
                                (storage_id, blood_type, quantity)
                            )
                    else:  # Remove action
                        success = execute_query(
                            "UPDATE Storage_House SET Quantity = GREATEST(0, Quantity - %s) WHERE Storage_id = %s",
                            (quantity, storage_id)
                        )
                    
                    if success:
                        st.success("Inventory updated successfully!")
                        st.balloons()

# Order Management
elif menu == "Orders":
    st.header("📦 Order Management")
    
    tab1, tab2, tab3 = st.tabs(["View Orders", "Place Order", "Update Status"])
    
    with tab1:
        orders = execute_query("""
            SELECT o.Order_id, h.Hosp_name, o.Blood_grp, o.Quantity, o.Order_date, o.Status 
            FROM Orders o JOIN Hospital h ON o.Hosp_id = h.Hosp_id
            ORDER BY o.Order_date DESC
        """, fetch=True)
        if orders:
            st.dataframe(pd.DataFrame(orders))
    
    with tab2:
        with st.form("place_order", clear_on_submit=True):
            st.subheader("Place New Order")
            cols = st.columns(2)
            
            with cols[0]:
                order_id = st.text_input("Order ID* (e.g., ORD100)")
                hosp_id = st.selectbox("Hospital*", 
                    [h["Hosp_id"] for h in execute_query("SELECT Hosp_id FROM Hospital", fetch=True)])
                blood_type = st.selectbox("Blood Type*", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
            
            with cols[1]:
                quantity = st.number_input("Quantity (units)*", min_value=1, max_value=50, value=1)
            
            submitted = st.form_submit_button("Place Order")
            
            if submitted:
                if not order_id:
                    st.error("Please enter an Order ID")
                else:
                    # Check blood availability
                    available = execute_query(
                        "SELECT SUM(Quantity) AS available FROM Storage_House WHERE Blood_grp = %s",
                        (blood_type,),
                        fetch=True
                    )
                    
                    if available and available[0]["available"] >= quantity:
                        success = execute_query(
                            """INSERT INTO Orders 
                            (Order_id, Hosp_id, Blood_grp, Quantity, Status) 
                            VALUES (%s, %s, %s, %s, 'Pending')""",
                            (order_id, hosp_id, blood_type, quantity)
                        )
                        
                        if success:
                            # Deduct from inventory
                            execute_query(
                                "UPDATE Storage_House SET Quantity = Quantity - %s WHERE Blood_grp = %s LIMIT 1",
                                (quantity, blood_type)
                            )
                            st.success("Order placed successfully!")
                            st.balloons()
                    else:
                        st.error("Insufficient blood available in inventory")

    with tab3:
        st.subheader("Update Order Status")
        order_id = st.selectbox("Select Order", 
            [o["Order_id"] for o in execute_query("SELECT Order_id FROM Orders WHERE Status = 'Pending'", fetch=True)])
        
        new_status = st.selectbox("New Status", ["Fulfilled", "Cancelled"])
        
        if st.button("Update Status"):
            success = execute_query(
                "UPDATE Orders SET Status = %s WHERE Order_id = %s",
                (new_status, order_id)
            )
            
            if success:
                if new_status == "Cancelled":
                    # Return blood to inventory if order is cancelled
                    order_details = execute_query(
                        "SELECT Blood_grp, Quantity FROM Orders WHERE Order_id = %s",
                        (order_id,),
                        fetch=True
                    )
                    if order_details:
                        execute_query(
                            "UPDATE Storage_House SET Quantity = Quantity + %s WHERE Blood_grp = %s",
                            (order_details[0]["Quantity"], order_details[0]["Blood_grp"])
                        )
                
                st.success(f"Order {order_id} status updated to {new_status}")

# Supply Management
elif menu == "Supply":
    st.header("🚚 Supply Management")
    
    tab1, tab2 = st.tabs(["View Supply History", "Add Supply Record"])
    
    with tab1:
        supply = execute_query("""
            SELECT s.Supply_id, h.Hosp_name, s.Blood_grp, s.Quantity, s.Supply_date 
            FROM Supply s JOIN Hospital h ON s.Hosp_id = h.Hosp_id
            ORDER BY s.Supply_date DESC
        """, fetch=True)
        if supply:
            st.dataframe(pd.DataFrame(supply))
    
    with tab2:
        with st.form("add_supply", clear_on_submit=True):
            st.subheader("Add New Supply Record")
            cols = st.columns(2)
            
            with cols[0]:
                supply_id = st.text_input("Supply ID* (e.g., SUP100)")
                hosp_id = st.selectbox("Hospital*", 
                    [h["Hosp_id"] for h in execute_query("SELECT Hosp_id FROM Hospital", fetch=True)])
            
            with cols[1]:
                blood_type = st.selectbox("Blood Type*", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                quantity = st.number_input("Quantity (units)*", min_value=1, max_value=50, value=1)
            
            submitted = st.form_submit_button("Record Supply")
            
            if submitted:
                if not supply_id:
                    st.error("Please enter a Supply ID")
                else:
                    success = execute_query(
                        "INSERT INTO Supply (Supply_id, Hosp_id, Blood_grp, Quantity) VALUES (%s, %s, %s, %s)",
                        (supply_id, hosp_id, blood_type, quantity)
                    )
                    
                    if success:
                        # Add to inventory
                        execute_query(
                            """INSERT INTO Storage_House (Storage_id, Blood_grp, Quantity) 
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE Quantity = Quantity + VALUES(Quantity)""",
                            (f"SUP{supply_id}", blood_type, quantity)
                        )
                        st.success("Supply recorded successfully!")
                        st.balloons()
