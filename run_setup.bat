@echo off
echo Setting up Smart Storage environment...

python -m venv venv

call venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete. Create .env with SUPABASE_URL, SUPABASE_KEY, EMPLOYEES.
pause
