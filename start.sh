#!/bin/bash

uvicorn backend.main_v2:app --host 0.0.0.0 --port 8855 &

streamlit run FRONTEND_PROJECT/app.py
