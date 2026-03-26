# Digital Lab Record Entry Management System

A clean, beginner-friendly Flask web application to manage student lab check-in/check-out entries.

---

## Admin Credentials

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

---

## Project Structure

```
lab_record_system/
├── app.py               ← Main Flask application
├── database.db          ← SQLite database (auto-created on first run)
├── README.md
├── templates/
│   ├── base.html        ← Shared layout with navbar
│   ├── index.html       ← Student entry page
│   ├── admin_login.html ← Admin login
│   ├── admin_dashboard.html ← Stats dashboard
│   ├── admin_entries.html   ← All entries with filter
│   └── admin_students.html  ← Student management
└── static/
    └── css/
        └── style.css    ← Custom styles
```

---

## How to Run Locally

### Step 1 — Install Python
Make sure Python 3.8+ is installed: https://python.org

### Step 2 — Install Flask
```bash
pip install flask
```

### Step 3 — Run the App
```bash
cd lab_record_system
python app.py
```

### Step 4 — Open in Browser
- **Student Entry:** http://127.0.0.1:5000
- **Admin Panel:**  http://127.0.0.1:5000/admin/login

---

## Features

### Student Entry Page
- Enter Register Number → automatic Time In
- Separate Exit form → Time Out recorded
- Prevents duplicate open entries
- Live clock display

### Admin Panel
- Secure login session
- Dashboard with today's stats
- View all entries with date filter
- Add / Delete students
- Export entries to CSV

---

## Sample Data (Optional)

To quickly test, add a student via Admin → Students with:
- Name: `Enter Full Name`
- Reg No: `Enter Reg No`
- Dept: `Computer Science`

Then go to the Student Entry page and enter `CS2024001`.
