import sys; sys.stdout.reconfigure(encoding='utf-8')
import os; os.environ['CHROMA_TELEMETRY_IMPL'] = 'None'
import os; os.environ['ANONYMIZED_TELEMETRY'] = 'False'
from config import settings
from database import SessionLocal
from services.vector_db import vector_db

queries = [
    'Đau bóp nghẹt vùng ngực trái lan lên cằm và tay trái',
    'khó thở dữ dội',
    'vã mồ hôi lạnh',
    'choáng váng'
]

for q in queries:
    res = vector_db.search_symptoms(q, n_results=3)
    print(f'Query: {q}')
    for r in res:
        print(f"  Match: {r['name']} (Distance: {r['distance']:.3f})")
