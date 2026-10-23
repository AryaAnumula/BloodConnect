FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home app
COPY --chown=app:app . /app
USER app
EXPOSE 8000
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
