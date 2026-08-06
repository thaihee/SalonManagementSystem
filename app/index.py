from flask import render_template
from app import app, db
from app import dao

@app.route("/")
def index():
    dich_vu_list = dao.get_all_services()
    return f"Salon Management chạy OK. Số dịch vụ hiện có: {len(dich_vu_list)}"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)