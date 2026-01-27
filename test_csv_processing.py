#!/usr/bin/env python3
"""
Script de teste para verificar como o CSV está a ser processado
"""

import csv
import sys
sys.path.insert(0, '/home/hugo/Desktop/SmarTaskUA/src/scheduler')

from algorithms.utils import rows_to_req_dicts

# Ler o CSV
csv_path = '/home/hugo/Desktop/SmarTaskUA/src/analyzer/Mins_R10-R62_30min.csv'

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print(f"Total rows in CSV: {len(rows)}")
print(f"\nFirst 5 rows:")
for i, row in enumerate(rows[:5]):
    print(f"  Row {i}: {row[:5]}... (showing first 5 columns)")

# Processar
mins, ideals = rows_to_req_dicts(rows)

print(f"\n{'='*80}")
print(f"PROCESSAMENTO COMPLETO")
print(f"{'='*80}")
print(f"Total entries in mins dict: {len(mins)}")
print(f"Total entries in ideals dict: {len(ideals)}")

# Analisar estrutura
from collections import defaultdict

by_team = defaultdict(set)
by_day = defaultdict(set)
by_hour = defaultdict(set)

for (day, hour, team_id), val in mins.items():
    by_team[team_id].add(hour)
    by_day[day].add(hour)
    by_hour[str(hour)].add(day)

print(f"\nTeams found: {list(by_team.keys())}")
for team_id, hours in by_team.items():
    print(f"  Team {team_id}: {len(hours)} unique hour intervals")
    print(f"    Sample: {sorted(hours)[:5]}")

print(f"\nTotal days with data: {len(by_day)}")
print(f"  First day has {len(by_day[1])} hours" if 1 in by_day else "  No data for day 1")

print(f"\nTotal unique hour strings: {len(by_hour)}")
print(f"  Sample hours: {sorted(by_hour.keys())[:10]}")

# Verificar um dia específico
day_1_data = [(h, t, mins[(1, h, t)]) for (d, h, t) in mins.keys() if d == 1]
print(f"\n{'='*80}")
print(f"DAY 1 DATA (should be closed = -1 for all)")
print(f"{'='*80}")
print(f"Total entries for day 1: {len(day_1_data)}")
for hour, team, val in sorted(day_1_data)[:10]:
    print(f"  Hour {hour}, Team {team}: {val}")

# Verificar dia 2
day_2_data = [(h, t, mins[(2, h, t)]) for (d, h, t) in mins.keys() if d == 2]
print(f"\n{'='*80}")
print(f"DAY 2 DATA (Segunda-feira - should have requirements)")
print(f"{'='*80}")
print(f"Total entries for day 2: {len(day_2_data)}")
for hour, team, val in sorted(day_2_data)[:15]:
    print(f"  Hour {hour}, Team {team}: {val}")

# Calcular requisitos totais
total_requirements = sum(v for v in mins.values() if v > 0)
total_slots = sum(1 for v in mins.values() if v > 0)

print(f"\n{'='*80}")
print(f"ESTATÍSTICAS GLOBAIS")
print(f"{'='*80}")
print(f"Total requirement (sum of all positive values): {total_requirements}")
print(f"Total slots with requirements: {total_slots}")
print(f"Average per slot: {total_requirements / total_slots if total_slots > 0 else 0:.2f}")

# DIAGNÓSTICO: Verificar se há duplicação
print(f"\n{'='*80}")
print(f"DIAGNÓSTICO DE DUPLICAÇÃO")
print(f"{'='*80}")

# Conta quantas vezes cada (dia, equipa) aparece
from collections import Counter
day_team_counts = Counter((d, t) for (d, h, t) in mins.keys())

# Dia 2, Team A deveria ter 26 intervalos (09:00-09:30, 09:30-10:00, ..., 21:30-22:00)
if (2, 'A') in day_team_counts:
    count = day_team_counts[(2, 'A')]
    print(f"Day 2, Team A: {count} hour intervals")
    if count == 26:
        print("  ✅ CORRETO: 26 intervalos de 30 minutos")
    else:
        print(f"  ❌ ERRO: Esperado 26, encontrado {count}")

# Listar todas as horas do dia 2, Team A
day_2_team_a_hours = sorted([h for (d, h, t) in mins.keys() if d == 2 and t == 'A'])
print(f"\nDay 2, Team A - All hours:")
for h in day_2_team_a_hours:
    print(f"  {h}")

print(f"\n{'='*80}")
