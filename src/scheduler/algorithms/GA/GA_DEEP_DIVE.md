# GA Deep Dive — `problem.py` + `ga.py`

Este documento explica em detalhe o que acontece nos dois ficheiros centrais da implementação,
desde o carregamento dos dados até ao output final.
A implementação é feita **de raiz**, sem bibliotecas de algoritmos evolutivos externas.

---

## Índice

1. [Visão Geral — Dois Ficheiros, Uma Responsabilidade Cada](#1-visão-geral)
2. [Passo 0 — Encoding: a linguagem do GA](#2-passo-0--encoding)
3. [Passo 1 — Carregar os dados (`load_problem`)](#3-passo-1--carregar-os-dados)
4. [Passo 2 — Criar um indivíduo aleatório (`random_schedule`)](#4-passo-2--criar-um-indivíduo-aleatório)
5. [Passo 3 — Representação do indivíduo](#5-passo-3--representação-do-indivíduo)
6. [Passo 4 — Criar e avaliar a população inicial](#6-passo-4--criar-e-avaliar-a-população-inicial)
7. [Passo 5 — O loop evolutivo (geração a geração)](#7-passo-5--o-loop-evolutivo)
   - 5a. Seleção por torneio
   - 5b. Clonagem
   - 5c. Crossover (3 operadores)
   - 5d. Mutação (4 operadores)
   - 5e. Re-avaliação dos inválidos (Lamarckiano)
   - 5f. Elitismo
   - 5g. Early stopping
8. [Passo 6 — Fitness: o que o GA está realmente a otimizar](#8-passo-6--fitness)
9. [Passo 7 — Repair: as restrições duras (Phase 2)](#9-passo-7--repair-phase-2)
   - Repair 1: Férias
   - Repair 2: Sem turno invertido
   - Repair 3: Cap de dias especiais
   - Repair 4: Janela de 6 dias
   - Repair 5: Contagem de dias trabalhados
10. [Passo 8 — Output final](#10-passo-8--output-final)
11. [Fluxo Completo em Diagrama](#11-fluxo-completo-em-diagrama)
12. [Referência Rápida: Constantes e Pesos](#12-referência-rápida)

---

## 1. Visão Geral

Os dois ficheiros têm responsabilidades completamente separadas:

| Ficheiro | Responsabilidade |
|---|---|
| `problem.py` | Define **o problema**: encoding, dados, fitness, repair. Não sabe nada do algoritmo. |
| `ga.py` | Define **o algoritmo**: operadores genéticos, loop evolutivo, hiperparâmetros. Importa só o que precisa de `problem.py`. |

`ga.py` importa de `problem.py`:
```python
from problem import (
    load_problem, compute_fitness, random_schedule,
    decode_schedule, print_summary, export_schedule, repair_schedule,
    GENE_OFF, GENE_TO_SHIFT_TEAM, SHIFT_IDX, TEAM_IDX,
)
```

Ou seja, `ga.py` é o "motor" e `problem.py` é o "combustível + as regras da estrada".

---

## 2. Passo 0 — Encoding

Antes de qualquer execução, o código define uma linguagem para representar
um horário. Cada **gene** é um inteiro de 0 a 4:

```
0 → OFF              (não trabalha)
1 → Manhã  + Equipa A
2 → Tarde  + Equipa A
3 → Manhã  + Equipa B
4 → Tarde  + Equipa B
```

Definido em `problem.py`:
```python
SHIFT_TEAM_TO_GENE = {
    ("M", "A"): 1,
    ("T", "A"): 2,
    ("M", "B"): 3,
    ("T", "B"): 4,
}
GENE_OFF = 0
```

**Porquê um único inteiro e não dois genes (turno + equipa)?**
Porque assim a lista de valores válidos por funcionário é simples e explícita.
Cada funcionário tem a sua própria lista `allowed_genes[i]`, por exemplo:
- Funcionário só na Equipa A → `[0, 1, 2]`
- Funcionário em ambas as Equipas → `[0, 1, 2, 3, 4]`

Se fossem dois genes separados, o crossover e a mutação podiam criar
combinações ilegais (turno válido + equipa inválida) que precisariam
de repair extra. O `allowed_genes` é a fonte única de verdade sobre
que genes cada funcionário pode ter — garante que todas as restrições
de equipa são sempre respeitadas automaticamente.

---

## 3. Passo 1 — Carregar os dados

**Função:** `load_problem(data_dir)` em `problem.py`

Lê 3 ficheiros da pasta `SMARTASK_SIMPLE_2025/`:

### `problem.json`
Contém:
- `n_days` = 365 (dias do ano)
- `year` = 2025
- Lista de funcionários com os seus nomes e equipas

A partir da lista de funcionários, calcula `allowed_genes`:
```python
for emp in employees:
    vals = [GENE_OFF]  # OFF é sempre permitido
    for shift in ["M", "T"]:
        for team in emp.get("teams", []):
            gene = SHIFT_TEAM_TO_GENE.get((shift, team))
            if gene is not None:
                vals.append(gene)
    allowed_genes.append(sorted(set(vals)))
```

O problema tem 12 funcionários: 7 só na Equipa A (employees 1–7), 3 em
ambas A e B (employees 8–10) e 2 só na Equipa B (employees 11–12).

### `vacations.csv`
Formato: `nome_funcionario, dia1, dia2, ..., dia365` (sem header).
`0` = trabalha, `1` = férias.

```python
vac_df   = pd.read_csv(base / "vacations.csv", header=None)
vac_mask = vac_df.iloc[:, 1:].values.astype(bool)  # (n_employees, n_days)
```

`vac_mask[i, d] = True` significa que o funcionário `i` está de férias no dia `d`.
Este array é usado em **toda** a lógica de repair e mutação para nunca
atribuir trabalho em dias de férias.

### `demand.csv`
Formato: `date, shift, team, minimum, ideal, estimated`

O código transforma isto em dois arrays numpy 3D:
- `min_demand[day, shift_idx, team_idx]` → mínimo de trabalhadores necessários
- `ideal_demand[day, shift_idx, team_idx]` → número ideal de trabalhadores

Onde `shift_idx`: M=0, T=1 e `team_idx`: A=0, B=1.

### Output de `load_problem`
Um dicionário com tudo:
```python
{
    "n_employees":   int,
    "n_days":        int,            # 365
    "year":          int,            # 2025
    "employees":     list[dict],
    "allowed_genes": list[list[int]],# valores válidos por funcionário
    "vac_mask":      ndarray bool,   # (n_employees, n_days)
    "min_demand":    ndarray int,    # (n_days, 2, 2)
    "ideal_demand":  ndarray int,    # (n_days, 2, 2)
    "special_days":  set[int],       # índices de domingos + feriados PT
}
```

Este dicionário é passado a **todas** as funções seguintes.

---

## 4. Passo 2 — Criar um indivíduo aleatório

**Função:** `random_schedule(problem_data)` em `problem.py`

Gera um horário aleatório com consciência de procura (*demand-aware*).
Em vez de atribuir turnos puramente ao acaso, tenta preencher primeiro os
slots onde a cobertura ainda está abaixo do mínimo exigido:

```
Para cada dia d (em ordem crescente):
  Baralha a ordem dos funcionários (sem favorecimento sistemático)
  Para cada funcionário i:
    Se férias → GENE_OFF
    Senão:
      greedy_genes = genes que cobrem slots ainda abaixo do min_demand
      Se há greedy_genes → escolhe aleatoriamente de entre eles
      Senão              → escolhe aleatoriamente de allowed_genes[i] (inclui OFF)
```

Isto produz populações iniciais com cobertura mais próxima do mínimo,
reduzindo o trabalho que o GA tem de fazer nas primeiras gerações.

Devolve um `ndarray (n_employees, n_days)`.

**A conversão 2D → 1D:**
```python
def make_individual(problem_data):
    return {"genes": random_schedule(problem_data).flatten().tolist(), "fitness": None}
```

O cromossoma é armazenado como lista 1D de comprimento `n_employees × n_days`.
Os operadores de crossover e mutação trabalham nesta lista 1D e reconstroem
o array 2D quando precisam de lógica por funcionário.

---

## 5. Passo 3 — Representação do indivíduo

Cada indivíduo é um dicionário simples:
```python
{"genes": list[int], "fitness": float | None}
```

- `genes`: lista plana de `n_emp × n_days` inteiros (0–4)
- `fitness`: valor calculado pela última avaliação, ou `None` se o cromossoma
  foi modificado e precisa de ser reavaliado

Esta representação é implementada de raiz, sem dependências externas.
`fitness = None` é o mecanismo que sinaliza que o indivíduo foi alterado
e precisa de ser reavaliado antes de participar na seleção.

---

## 6. Passo 4 — Criar e avaliar a população inicial

Em `run_ga()` em `ga.py`:

```python
pop = [make_individual(problem_data) for _ in range(pop_size)]
for ind in pop:
    ind["fitness"] = evaluate(ind, problem_data)

hof = clone(max(pop, key=lambda ind: ind["fitness"]))
```

**Hall of Fame (`hof`):** variável que guarda sempre o melhor indivíduo
visto em toda a execução (uma cópia independente). Garante que o elitismo
funciona mesmo se o melhor for eliminado por crossover/mutação numa geração.

---

## 7. Passo 5 — O loop evolutivo

Para cada geração de 1 a `num_generations` (máximo 1000):

### 5a. Seleção por Torneio

```python
offspring = select_tournament(pop, len(pop) - elite_size, tournament_size)
```

Torneio de tamanho 5: escolhe 5 indivíduos aleatoriamente da população,
o melhor dos 5 vence e vai para `offspring`. Repete `pop_size - 1` vezes.
O mesmo indivíduo pode ser escolhido várias vezes — isto é intencional,
é a pressão seletiva: os melhores aparecem mais vezes na descendência.

### 5b. Clonagem

```python
offspring = [clone(ind) for ind in offspring]
```

Os indivíduos são dicionários com listas mutáveis. Sem clonagem, modificar
um offspring modificaria o original em `pop`. A clonagem cria cópias independentes.

### 5c. Crossover — 3 operadores disponíveis

Selecionado via `params["crossover_type"]`.

#### `cx_row_swap` (padrão)
Para cada funcionário, com 50% de probabilidade, troca a linha inteira
(os 365 dias desse funcionário) entre os dois pais.

```python
for i in range(n_emp):
    if random.random() < 0.5:
        start, end = i * n_days, (i + 1) * n_days
        ind1["genes"][start:end], ind2["genes"][start:end] = ...
```

Preserva a coerência interna de cada funcionário (férias, padrão de turnos).
Um crossover gene-a-gene misturaria dias de funcionários diferentes, criando
horários sem sentido estrutural.

#### `cx_day_point`
Corte num dia D aleatório, aplicado a **todos** os funcionários ao mesmo tempo.
O filho 1 fica com os dias 0..D-1 do pai 1 e os dias D..364 do pai 2.

```python
D = random.randint(1, n_days - 1)
child1 = np.hstack([arr1[:, :D], arr2[:, D:]])
child2 = np.hstack([arr2[:, :D], arr1[:, D:]])
```

Preserva blocos temporais contíguos de cada pai. A junção no dia D pode
violar a restrição de turno invertido, que é corrigida pelo repair na avaliação.

#### `cx_nbts` (Nurse-Based Tournament Selection)
Para cada funcionário, escolhe a linha do pai que mais cobre a procura
mínima ainda não satisfeita — greedy e sequencial.

```python
for i in range(n_emp):
    s1 = _coverage_contribution(arr1[i], coverage, min_demand, ideal_demand)
    s2 = _coverage_contribution(arr2[i], coverage, min_demand, ideal_demand)
    row = arr1[i] if s1 >= s2 else arr2[i]   # empates resolvidos aleatoriamente
    child1[i] = row
    _update_coverage(row, coverage)  # cobertura acumulada para a decisão seguinte
```

O filho 2 faz o mesmo mas na ordem inversa (n_emp-1 → 0), produzindo
um segundo filho com contexto de cobertura diferente.

### 5d. Mutação — 4 operadores disponíveis

Selecionado via `params["mutation_type"]`. Todos os indivíduos passam pela
mutação (`mutation_prob = 1.0`); a estocasticidade vem da probabilidade interna.

#### `mut_respect_constraints` (padrão)
Cada gene muda com probabilidade `gene_mut_prob` (0.001 = 0.1%):
- Dia de férias → força GENE_OFF
- Outro dia → escolhe aleatoriamente de `allowed_genes[i]`

Num cromossoma de 4380 genes, em média **~4 genes** mudam por geração.

#### `mut_swap_days`
Para cada funcionário (com probabilidade `indpb_emp = 0.3`), troca dois
dias aleatórios não-férias entre si. Preserva o número de dias trabalhados
exatamente — reorganiza sem introduzir novos turnos.

#### `mut_demand_guided`
Cada gene é selecionado para mutação com probabilidade `gene_mut_prob`.
Em vez de escolher aleatoriamente, escolhe o gene que mais cobre a procura
mínima ainda não satisfeita nesse dia. Mantém cobertura acumulada ao longo
da iteração para decisões incrementalmente melhores.

#### `both`
Aplica `mut_respect_constraints` seguido de `mut_swap_days` — mais disruptivo.

### 5e. Re-avaliação — Repair Lamarckiano

```python
def evaluate(individual, problem_data):
    schedule = np.array(individual["genes"], dtype=int).reshape(n_emp, n_days)
    schedule = repair_schedule(schedule, problem_data)
    individual["genes"] = schedule.flatten().tolist()   # ← Lamarckiano
    return compute_fitness(schedule, problem_data)
```

**Lamarckiano** significa que o repair é escrito de volta no cromossoma.
Nas gerações seguintes, o crossover e a mutação já operam sobre um
cromossoma válido, não sobre um com violações por corrigir.

Alternativa seria **Baldwiniano** (repair só para avaliação, cromossoma original
inalterado), mas testes mostraram que o Lamarckiano melhora muito os resultados
(de ~171 para ~30 worker-days de cobertura mínima não satisfeita).

Só os indivíduos com `fitness = None` são reavaliados — eficiência.

### 5f. Elitismo

```python
current_best = max(offspring, key=lambda ind: ind["fitness"])
if current_best["fitness"] > hof["fitness"]:
    hof = clone(current_best)
pop = [clone(hof)] + offspring
```

O melhor indivíduo de sempre (Hall of Fame) é sempre colocado na nova população.
Garante que a qualidade nunca decresce entre gerações.

### 5g. Early Stopping

```python
if record["best"] > best_so_far + early_stop_min_delta:
    best_so_far = record["best"]
    no_improve  = 0
else:
    no_improve += 1
if no_improve >= early_stop_patience:
    stopped_at = gen
    break
```

Se `early_stop_patience` (50) gerações consecutivas passarem sem que o melhor
fitness melhore mais de `early_stop_min_delta` (10) pontos, o GA para.
Evita desperdício de tempo quando o algoritmo já convergiu.

---

## 8. Passo 6 — Fitness

**Função:** `compute_fitness(schedule, problem_data)` em `problem.py`

Só existem **penalidades de cobertura** (Phase 1). O máximo possível é 0
(cobertura perfeita em todos os turnos).

```
fitness = -(min_unmet × 100 + ideal_unmet × 1)
```

**`min_unmet`**: total de worker-days abaixo do mínimo exigido.
Por exemplo, se num dia o turno M-A precisa de 3 pessoas e só há 1,
`min_unmet += 2`.

**`ideal_unmet`**: total de worker-days abaixo do ideal (mas acima do mínimo).
Penalidade muito menor (peso 1 vs 100) porque não é crítico.

```python
for s_idx, s_code in enumerate(SHIFTS):      # M e T
    for t_idx, t_code in enumerate(TEAMS):   # A e B
        gene_val = SHIFT_TEAM_TO_GENE[(s_code, t_code)]
        assigned = np.sum(schedule == gene_val, axis=0)  # (n_days,)
        min_unmet   += sum(max(0, min_demand[d,s,t] - assigned[d]) for all d)
        ideal_unmet += sum(max(0, ideal_demand[d,s,t] - assigned[d]) for all d)
```

O fitness **não avalia** as restrições duras (férias, janela de 6 dias, etc.)
— essas são garantidas pelo **repair** antes de chegar aqui.

---

## 9. Passo 7 — Repair (Phase 2)

**Função:** `repair_schedule(schedule, problem_data)` em `problem.py`

O repair é chamado dentro de `evaluate` (Lamarckiano — escreve de volta no
cromossoma) e a ordem dos repairs importa.

### Repair 1 — Férias (`_repair_vacations`)
```python
schedule[vac_mask & (schedule > 0)] = GENE_OFF
```
Uma linha. Qualquer gene que atribua trabalho num dia de férias é forçado
a OFF. Rápido, vectorizado.

### Repair 2 — Sem turno invertido (`_repair_no_backward_shift`)
Regra: se hoje é Tarde, amanhã não pode ser Manhã.
```
Hoje: Tarde-A (gene 2, order=2)
Amanhã: Manhã-B (gene 3, order=1) → VIOLAÇÃO
Fix: upgrada amanhã para Tarde-B (gene 4, order=2)
     Se Tarde-B não é permitido para este funcionário → OFF
```
Usa `GENE_SHIFT_ORDER = {0:0, 1:1, 2:2, 3:1, 4:2}` para comparar.

### Repair 3 — Cap de dias especiais (`_repair_special_days`)
Regra: máximo 22 dias especiais (domingos + feriados PT) trabalhados.
```python
worked_special = [d for d in special_days if schedule[i, d] > 0]
random.shuffle(worked_special)   # remoção aleatória → justo
while len(worked_special) > 22:
    schedule[i, worked_special.pop()] = GENE_OFF
```

Este repair vem **antes** do de 6 dias porque o cap de especiais pode
forçar dias a OFF que depois seriam mal contados pela janela de 6 dias.

### Repair 4 — Janela de 6 dias (`_repair_6day_window`)
Regra: em qualquer janela de 6 dias consecutivos, no máximo 5 trabalhados.
```python
while changed:
    for each window of 6 days:
        if worked_days > 5:
            set last worked non-vacation day to OFF
            changed = True
```
O `while changed` é necessário porque corrigir uma janela pode
criar uma violação na janela seguinte.

### Repair 5 — Contagem de dias trabalhados (`_repair_workday_count`)
Regra: exactamente 223 dias trabalhados por funcionário.

**Demasiados** → remove aleatoriamente dias trabalhados até chegar a 223.

**Poucos** → não pode simplesmente ligar dias aleatórios (podiam violar
a janela de 6 dias, o cap de especiais, ou criar turnos invertidos).
Por isso usa `_workday_candidates()` que pré-filtra dias seguros, e
depois re-verifica cada candidato com o estado atual da linha antes de
o adicionar (porque adições anteriores podem ter mudado o contexto local).

**Ordem dos repairs:**
Os repairs 1–4 podem reduzir o número de dias trabalhados abaixo de 223.
O repair 5 vem no fim e reequilibra — mas só adiciona dias que não violam
nenhum dos constraints anteriores.

---

## 10. Passo 8 — Output final

Em `main()` de `ga.py`:

```python
best_schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
print_summary(best_schedule, pd_data, label="Best Schedule")
export_schedule(best_schedule, pd_data, path="schedule_ga.csv")
```

O cromossoma do Hall of Fame já está reparado (Lamarckiano), por isso
não é necessário aplicar repair novamente antes de exportar.

**`print_summary`** imprime:
- Fitness final
- `min_unmet` e `ideal_unmet` (Phase 1)
- Contagem de violações Phase 2 (devem ser 0 após repair)

**`export_schedule`** cria dois CSVs:
1. `schedule_ga.csv` — tabela wide: linhas = funcionários, colunas = datas,
   células = `OFF/M-A/T-A/M-B/T-B`
2. `schedule_ga_coverage.csv` — cobertura diária por (dia, turno, equipa):
   assigned, minimum, ideal, min_unmet, ideal_unmet

---

## 11. Fluxo Completo em Diagrama

```
main()
  │
  ├─ load_problem()                           [problem.py]
  │     ├─ lê problem.json → n_emp, n_days, allowed_genes
  │     ├─ lê vacations.csv → vac_mask
  │     ├─ lê demand.csv → min_demand, ideal_demand
  │     └─ _build_special_days() → special_days
  │
  └─ run_ga(problem_data, params)             [ga.py]
        │
        ├─ cria população (150 indivíduos via make_individual)
        │     └─ cada indivíduo: random_schedule().flatten()  [demand-aware]
        │
        ├─ avalia todos → evaluate() [Lamarckiano: repair + fitness + escrita]
        ├─ Hall of Fame (clone do melhor)
        │
        └─ LOOP (até 1000 gerações ou early stop a 50 sem melhoria)
              │
              ├─ select_tournament (torneio de 5) → 149 offspring
              ├─ clone → cópias independentes
              ├─ crossover (50%) → row_swap | day_point | nbts
              ├─ mutação (100% × prob por gene) → respect_constraints
              │                                   | swap_days
              │                                   | demand_guided
              │                                   | both
              ├─ avalia inválidos → evaluate() [Lamarckiano]
              ├─ elitismo → Hall of Fame entra na nova população
              └─ early stop check (50 gerações sem melhoria > 10)
```

---

## 12. Referência Rápida

### Encoding
| Gene | Significado |
|---|---|
| 0 | OFF |
| 1 | Manhã + Equipa A |
| 2 | Tarde + Equipa A |
| 3 | Manhã + Equipa B |
| 4 | Tarde + Equipa B |

### Hiperparâmetros GA
| Parâmetro | Valor | Notas |
|---|---|---|
| `POP_SIZE` | 150 | população |
| `NUM_GENERATIONS` | 1000 | máximo |
| `CROSSOVER_PROB` | 0.5 | 50% dos pares cruzam |
| `MUTATION_PROB` | 1.0 | todos mutam |
| `GENE_MUT_PROB` | 0.001 | 0.1% dos genes mudam |
| `TOURNAMENT_SIZE` | 5 | pressão seletiva |
| `ELITE_SIZE` | 1 | melhor sempre sobrevive |
| `early_stop_patience` | 50 | gerações sem melhoria |
| `early_stop_min_delta` | 10 | melhoria mínima considerada |

### Pesos de Fitness (Phase 1)
| Penalidade | Peso |
|---|---|
| Abaixo do mínimo de cobertura | 100 por worker-day |
| Abaixo do ideal de cobertura | 1 por worker-day |

### Constraints Duras (Phase 2)
| Constraint | Valor |
|---|---|
| `TARGET_WORKDAYS` | 223 dias trabalhados por funcionário |
| `WINDOW_SIZE` | 6 dias |
| `WINDOW_MAX` | 5 dias trabalhados em qualquer janela de 6 |
| `SPECIAL_DAYS_CAP` | 22 dias especiais (dom + feriados PT) por funcionário |

### Operadores disponíveis
| Tipo | Nome | Descrição curta |
|---|---|---|
| Crossover | `row_swap` | troca linhas de funcionários com 50% de prob |
| Crossover | `day_point` | corte num dia D, todos os funcionários ao mesmo tempo |
| Crossover | `nbts` | escolhe a linha que mais cobre procura mínima |
| Mutação | `respect_constraints` | gene aleatório válido por employee (padrão) |
| Mutação | `swap_days` | troca dois dias do mesmo funcionário |
| Mutação | `demand_guided` | escolhe gene que mais cobre procura não satisfeita |
| Mutação | `both` | respect_constraints + swap_days em sequência |
