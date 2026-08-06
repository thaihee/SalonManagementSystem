from app.models import Services

def get_all_services():
    return Services.query.all()