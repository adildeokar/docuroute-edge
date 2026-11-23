@echo off
REM Starts the edge service and opens the dashboard
cd /d "%~dp0backend"
if not exist "..\models\document_classifier.joblib" (
  echo Model not found - generating dataset and training model...
  python generate_dataset.py
  python train_model.py
)
start "" http://localhost:5000
python app.py
pause
