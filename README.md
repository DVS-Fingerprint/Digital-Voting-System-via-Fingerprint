Fingerprint Based Digital Voting System

1. Install Python : https://www.python.org/downloads/ ( Don't forget toclick : Add to environment path,pip)
2. Open cmd : python --version
3. cmd : pip --version

Virtual Environment: python -m venv env

activate : env\Scripts\activate.bat

4. cmd : pip install django
5. cmd : pip-admin --version

 Main Django project folder : django-admin startproject core
 cmd: cd core
 creating App: 
python manage.py startapp users
python manage.py startapp voting

python manage.py runserver  (Starting development server at http://127.0.0.1:8000/   )
