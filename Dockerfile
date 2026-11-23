# Edge Document Classification & Routing Service - container image
# Build:  docker build -t docuroute-edge .
# Run:    docker run -p 5000:5000 --env-file backend/.env -v docuroute-data:/app/data docuroute-edge
FROM python:3.12-slim

# libgl/glib are needed by OpenCV (used inside RapidOCR); DejaVu font for the dataset renderer
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
WORKDIR /app/backend
# Build the dataset + model only if they were not copied in
RUN test -f ../models/document_classifier.joblib || (python generate_dataset.py && python train_model.py)

EXPOSE 5000
CMD ["python", "app.py"]
