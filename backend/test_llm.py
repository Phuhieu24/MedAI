import sys
import os
sys.path.append('backend')
from services.llm_ingestion import llm_ingestion_service

text = '{"Disease": "Common Cold", "Symptoms": "Fever, Cough"}'
try:
    res = llm_ingestion_service.parse_row(text)
    print('SUCCESS:', res)
except Exception as e:
    print('ERROR:', e)
