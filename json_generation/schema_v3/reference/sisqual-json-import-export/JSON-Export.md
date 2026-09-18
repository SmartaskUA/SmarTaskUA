**Exportação da estrutura de dados do schedule generator**

O formato usado para importação/exportação de dados do schedule generator é o JSON.

**Estrutura JSON**

**Exemplo de Payload JSON – InpRosterDetail, InpMasterData, InpServiceLevelDetail e InpGenerationRules**

O exemplo seguinte representa a estrutura de dados utilizada para receção de informação relativa a detalhes dos quadros *InpRosterDetail,* aos dados necessários para guiar a geração de horários *InpMasterData,* aos detalhes dos níveis de serviço necessários, por dia e/ou por período *InpServiceLevelDetail* e às regras para a geração de horários e atribuiçãos de tarefas e responsabilidades *InpGenerationRules*. 

Há campos opcionais que podem ou não estar presentes, dependendo da configuração.

A nomenclatura dos campos é feita através da contração de palavras, em Inglês, por forma a facilitar o seu reconhecimento e contexto de utilização.

| Tipos de dados: | Descrição |
| :---- | :---- |
| array | matriz |
| string | texto |
| integer | número inteiro |
| float | número real |
| boolean | Verdade/Falso |
| date | data no formato YYYY-MM-DD |
| datetime | data e hora no formato ISO8601 |

**Descrição**

* **InpRosterDetail**: Contém a lista de detalhes do quadro, nomeadamente, a lista de horários possíveis, a lista das equipas e respetivas escalas e a lista de empregados e respetivos contratos; 

* **InpMasterData**: Contém a lista de horário efetivamente utilizados, a lista tarefas e respetivas competências, a lista dos contratos possíveis, a lista de responsabilidades, a lista de competências para responsabilidades e a lista de leis e regras de trabalho aplicáveis;

* **InpServiceLevelDetail**: Contém a lista com os detalhes dos níveis de serviço necessários por dias e /ou por períodos de tempo;

* **InpGenerationRules**: Contém a lista de regras para a geração de horários e/ou atribuição de tarefas, incluindo regras de grupo e detalhes dos índices (diferentes versões) das regras;

**Estrutura:**

* **InpRosterDetail: \[**

  * **RosterCode**: código do quadro \- string;

  * **StartDate**: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

  * **EndDate**: data final \- YYYY-MM-DDThh:mm:ss \- string;

  * **InpRosterSchedulesCollection**: **\[** array de horários do quadro disponíveis \- array; 

    * ScheduleCode: código do horário \- string;

    * Legend: Legenda \- Lhh:mm (inicial) \- hh:mm (final) \- string;

    * Description: descrição \- hh:mm (inicial) \- hh:mm (final) \- string;

    * Date: data em processo \- YYYY-MM-DD \- string;

    * StartDate: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate: data final \- YYYY-MM-DDThh:mm:ss \- string;

    * IsHolliday: é feriado \- V/F \- boolean;

    * **\]**

  * **InpRosterLines**: **\[** array de linhas de horários do quadro (uma por cada empregado) 

    * EmployeeCode: código do empregado \- string;

    * TeamCode: código da equipa \- string;

    * InpRosterTeamDays: **\[** array com a escala das equipas do quadro 

      * Date: data em processo \- YYYY-MM-DD \- string;

      * AbsenceCodeFullDay: código de ausência de dia completo \- integer;

      * AbsenceCodeCountAsDayOff: ausência conta como para limites (Férias) \- V/F \- boolean;

      * ScheduleCode: código do horário \- integer;

      * Locked: fecho \- V/F \- boolean;

      * LockedResponsibilities: responsabilidades de fecho \- V/F \- boolean;

      * IsHolliday: é feriado \- V/F \- boolean;

      * ScheduleAvailabilityCode: código da disponibilidade de horário \- integer;

      * (Optional) PotentialCycleScheduleWeightWhenScheduleIsSpace: **\[** peso potencial do ciclo do horário quando o horário em espaço vazio 

        * **\]**

      * **\]**

  * **InpRosterLineDataCollection**: **\[** array de linhas do quadro \- array;

    * EmployeeCode: código do empregado \- string;

    * InpEmployeeContracts: **\[** array de contratos dos empregados \- array;

      * EmployeeCode: código do empregado \- string;

      * ContractCode: código do contrato- string;

      * StartDate: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

      * EndDate: data final \- YYYY-MM-DDThh:mm:ss \- string;

      * **\]**

    * InpEmployeeAbilities: **\[** array de competências do empregado

      * EmployeeCode: código do empregado \- string;

      * AbilityID: id. hexadecimal da competência \- string;

      * StartDate: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

      * EndDate: data final \- YYYY-MM-DDThh:mm:ss \- string;

      * Level: nível de competência \- integer;

      * **\]**

    * InpEmployeeLLabourLawLegislationCollection: **\[**

      * EmployeeCode: código do empregado \- string;

      * LegislationLaborLawCode: código da legislação- string;

      * StartDate: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

      * EndDate: data final \- YYYY-MM-DDThh:mm:ss \- string;

      * **\]**

    * InpEmployeeGeneratedParameterCollection (**optional**): **\[** array de parâmetros de geração do empregado \- array;

      * **\]**

    * **\]**

* **InpMasterData: \[**

  * **InpScheduleUsedCollection**: **\[** array de horários utilizados

    * ScheduleCode: código do horário \- integer;

    * Description: descrição \- hh:mm (inicial) \- hh:mm (final) \- string;

    * Legend: legenda \- string;

    * DayType: código do tipo de dia \- integer;

      *     WeekDay \= 0, Dia de Trabalho

      *     WeekEndSaturday \= 1, Folga Complementar

      *     WeekEndSunday \= 2, Folga Obrigatória

      *     Empty \= 3 \- V Folga

 

* ScheduleWeight: peso do horário (unidade minutos) \- integer;

  * StartDate: data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate: data final \- YYYY-MM-DDThh:mm:ss \- string;

    * **\]**

  * **InpTaskAbilityCollection**: **\[** array de tarefas/competências;

    * TaskID: código da tarefa- integer;

    * AbilityCode: código da competência \- Guid;

    * **\]**

  * **InpContractCollection**: **\[** array de contratos

    * ContractCode: código do contrato \- string;

    * TotalDailyMinutes: total de minutos por dia \- integer;

    * TotalWeeklyMinutes: total de minutos por semana \- integer;

    * TotalMonthlyMinutes: total de minutos por mês \- integer;

    * TotalYearMinutes: total de minutos por ano \- integer;

    * TotalWeeklyWorkDays: total de dias de trabalho na semana \- integer;

    * TotalWeeklyWorkDaysMax: total máximo de dias de trabalho na semana \- integer;

    * WeightMonday: peso do horário na segunda feira \- integer;

    * WeightTuesday: peso do horário na terça feira \- integer;

    * WeightWednesday: peso do horário na quarta feira \- integer;

    * WeightThursday: peso do horário na quinta feira \- integer;

    * WeightFriday: peso do horário na segunda feira \- integer;

    * WeightSaturday: peso do horário no sábado \- integer;

    * WeightSunday: peso do horário no domingo \- integer;

    * WeightHolidayBusinessDay: peso do horário num feriado em dia útil \- integer;

    * WeightHolidaySaturday: peso do horário num feriado ao sábado \- integer;

    * WeightHolidaySunday: peso do horário em feriado ao domingo \- integer;

    * **\]**

  * **InResponsabilityCollection**: **\[** array de responabilidades

    * Code código da responsabilidade \- string;

    * Description descrição da responsabilidade \- string;

    * Legend legenda \- string;

    * CostCenterCode código do centro de custo \- string;

    * ResponsabilityGroupCode código do grupo de responsabilidade \- string;

    * ResponsabilityPoolerCode código do agregador de responsabilidades \- string;

    * ResponsabilityProfile perfil de responsabilidade \- integer;

    * ResponsabilityTypeCode código do tipo de responsabilidade \- integer;

    * ResponsabilityPoolerIndex indice do agregador de responsabilidades \- integer;

    * **\]**

  * **InpResponsibilityAbilityCollection**: **\[** array de responsabilidades/competências 

    * ResponsibilityCode código da responsabilidade \- string;

    * AbilityID id. hexadecimal da responsabilidade \- string;

    * StartDate data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate data final \- YYYY-MM-DDThh:mm:ss \- string;

    * **\]**

  * **InpLabourLawCollection**: **\[** array de leis da legislação laboral

    * legislationLaborLawCode código da lei laboral \- string;

    * StartDate data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * DistanceBetweenShiftsInMinutes distancia entre turnos, em minutos \- integer;

    * MaxConsecutiveWorkDaysInWeek número máximo de dias consecutivos de trabalho, na semana \- integer

    * DayOfWeek dia inicial da Semana (0-Dom, 1-Seg, …., 6-Sáb)

    * **\]**

  * **\]**

* **InpServiceLevelDetail: \[** array de detalhes de níveis de serviço

  * **InpServiceLevelByDays**: **\[** array de níveis de serviço por dias (nº de minutos por periodo de tempo HoraInicio-Hora Fim)

    * RosterCode código do quadro \- string;

    * TableName nome da tabela \- string;

    * TableValue valor da tabela \- string;

    * Date data \- YYYY-MM-DDThh:mm:ss \- string;

    * TotalValue valor total \- integer;

    * MinimumValue valor mínimo \- integer;

    * EmpiricValue valor empirico \- integer;

    * EstimatedValue valor estimado \- integer;

    * MaximumValue valor máximo \- integer;

    * **\]**

  * **InpServiceLevelByPeriods**: **\[** array de níveis de serviço (nº de colaboradores) por períodos (Hora inicio \- Hora Fim)

    * RosterCode código do quadro \- string;

    * TableName nome da tabela \- string;

    * TableValue valor da tabela \- string;

    * Date data \- YYYY-MM-DDThh:mm:ss \- string;

    * StartDate data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate data final \- YYYY-MM-DDThh:mm:ss \- string;

    * MinimumValue valor mínimo \- float;

    * MaximumValue valor máximo \- float;

    * EmpiricValue valor empirico \- float;

    * EstimatedValue valor estimado \- float;

    * TotalValue valor total \- float;

    * **\]**

  * **\]**

  * **InpServiceLevelByShifts**: **\[** array de níveis de serviço (nº de colaboradores) por turnos

    * RosterCode código do quadro \- string;

    * TableName nome da tabela \- string;

    * TableValue valor da tabela \- string;

    * Date data \- YYYY-MM-DDThh:mm:ss \- string;

    * ShiftTypeCode código to tipo de turno (M, T, N) \- string;

    * MinimumValue valor mínimo \- float;

    * MaximumValue valor máximo \- float;

    * EmpiricValue valor empirico \- float;

    * EstimatedValue valor estimado \- float;

    * TotalValue valor total \- float;

    * **\]**

    * **\]**

* **InpGenerationRules: \[** array de regras de geração

  * **InpGroupRulesIndexDatesToExecuteCollection**: **\[** array de indices de datas de execução regras de grupo para executar

    * StartDate data inicial \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate data final \- YYYY-MM-DDThh:mm:ss \- string;

    * OrderGroupRuleIndex ordem do índice da regra de grupo \- integer; 

    * GroupRuleIndexId Id do índice da regra de grupo \- integer;

    * RuleIndexId Id do índice de regra \- integer;

    * Order ordem \- integer;

    * **\]**

  * **InpGroupRuleIndexDetailCollection**: **\[**

    * GroupRuleIndexID Id do índice da regra de grupo \- integer;

    * RuleIndex índice da regra \- integer;

    * RuleOrder ordem da regra \- integer;

    * Description descrição do índice da regra de grupo \- string;

    * AlarmTableType tipo de tabela de alarme \- string;

    * AlarmTable tabela de alarme \- string;

    * Tasks: **\[** array de tarefas \- array

      * 

      * **\]**

    * AbilityLevelSignal sinal do nível de competência (ex.menor ou igual) \- string;

    * AbilityLevelValue nível de competência \- integer; 

    * GenerationSequenceType tipo de sequência de geração \- string;

    * AlarmLevelMinimum alarme por nível mínimo \- integer;

    * AlarmLevelMaximum alarme por nível máximo \- integer;

    * AlarmLevelPercentage alarme por nível percentual \- integer;

    * AlgorithmStep passo do algoritmo \- integer;

    * GenerateScheduleGetPriorityType tipo de prioridade para o gerador de horários-string;

    * DaysForwardToValidateLegislation dias para validar a legislação \- integer;

    * FindScheduleType tipo de procura de horário \- string;

    * ResponsabilityMaximumWaste desperdício máximo de responsabilidade \- integer;

    * ResponsabilityOverride substituição de responsabilidade \- integer;

    * ResponsabilityOverrideInResponsabilityPooler substituição de responsabilidade no agregador de responsabilidade \- integer;

    * ResponsabilityMinimumCover cobertura mínima de responsabilidade \- integer;

    * PreferenceWithResponsibilities responsabilidades com preferências \- string;

    * PreferenceWithResponsibilitiesType tipo de responsabilidades com preferências-string;

    * RespectPreferenceWithResponsibilities respeita responsabilidades com preferências \-string;

    * AlgorithmRuleType tipo de regra do algoritmo \- string;

      * RuleTypeDescription descrição do tipo de regra \- string;

    * MaximumTime tempo máximo \- integer;

    * AtStart desde o início V/F \- boolean;

    * CanDuplicateResponsibility pode duplicar aresponsabilidade V/F \- boolean;

    * InpGenerateSchedulePeriods: **\[** períodos para geração de horários

      * Index índice \- integer;

      * StartGenerationSchedulePeriodType tipo de início do período de geração \- string;

      * EndGenerationSchedulePeriodType tipo de final do período de geração \- string;

      * StartDate data inicial \- YYYY-MM-DDThh:mm:ss \- string;

      * EndDate data final \- YYYY-MM-DDThh:mm:ss \- string;

      * Percentage percentagem \- integer;

      * AlgorithmRuleType tipo de regra de algoritmo \- string;

      * RuleTypeDescription descrição do tipo de regra \- string;

      * **\]**

    * MinimumTime tempo mínimo \- integer; 

    * GenerateOnMonday geração na segunda feira \- V/F \- boolean;

    * GenerateOnTuesday geração na terça feira \- V/F \- boolean;

    * GenerateOnWednesday geração na quarta feira \- V/F \- boolean;

    * GenerateOnThursday geração na quinta feira \- V/F \- boolean;

    * GenerateOnFriday geração na sexta feira \- V/F \- boolean;

    * GenerateOnSaturday geração no sábado \- V/F \- boolean;

    * GenerateOnSunday geração no domingo \- V/F \- boolean;

    * GenerateOnHoliday geração nos feriados \- V/F \- boolean;

    * ScheduleBlackListProfileID Id do perfil de lista negra de horários \- string;

    * FollowLevelByLevel seguir nível a nível de competência V/F \- boolean;

    * DontGrowSchedule horário não pode ser estendido \- V/F \- boolean;

    * SolveOnlyStartEndDefinitionAlarm resolve só o início e o final do período de alarme definido \- V/F \- boolean;

    * MinimumScheduleWeightTotalWeek peso mínimo do horário total semanal \- integer;

    * MaximumScheduleWeightTotalWeek peso máximo do horário total semanal \- integer;

    * **\]**

  * **\]**

* **\]**

**Exemplo:**

{

  "InpRosterDetail": {

    "RosterCode": "0533",

    "StartDate": "2025-12-01",

    "EndDate": "2025-12-07",

    "InpRosterSchedulesCollection": \[

      {

        "ScheduleCode": 10005,

        "Legend": "L07:00-21:15",

        "Description": "07:00-21:15",

        "Date": "2025-12-01",

        "StartDate1": "2025-12-01T07:00:00",

        "EndDate1": "2025-12-01T21:15:00",

        "IsHolliday": false

      },

      {

        "ScheduleCode": 10005,

        "Legend": "L07:00-21:15",

        "Description": "07:00-21:15",

        "Date": "2025-12-02",

        "StartDate1": "2025-12-02T07:00:00",

        "EndDate1": "2025-12-02T21:15:00",

        "IsHolliday": false

      },

      {

        "ScheduleCode": 10005,

        "Legend": "L07:00-21:15",

        "Description": "07:00-21:15",

        "Date": "2025-12-03",

        "StartDate1": "2025-12-03T07:00:00",

        "EndDate1": "2025-12-03T21:15:00",

        "IsHolliday": false

      },

      {

        "ScheduleCode": 10005,

        "Legend": "L07:00-21:15",

        "Description": "07:00-21:15",

        "Date": "2025-12-04",

        "StartDate1": "2025-12-04T07:00:00",

        "EndDate1": "2025-12-04T21:15:00",

        "IsHolliday": false

      },

 }

  "InpMasterData": {

    "InpScheduleUsedCollection": \[

      {

        "ScheduleCode": 100000,

        "Description": "00:00-03:00",

        "Legend": "R000",

        "DayType": 0,

        "ScheduleWeight": 180,

        "StartDate1": "2026-03-09T00:00:00+00:00",

        "EndDate1": "2026-03-09T03:00:00+00:00"

      },

      {

        "ScheduleCode": 100001,

        "Description": "00:00-03:15",

        "Legend": "R000",

        "DayType": 0,

        "ScheduleWeight": 195,

        "StartDate1": "2026-03-09T00:00:00+00:00",

        "EndDate1": "2026-03-09T03:15:00+00:00"

      },

      {

        "ScheduleCode": 100002,

        "Description": "00:00-03:30",

        "Legend": "R000",

        "DayType": 0,

        "ScheduleWeight": 210,

        "StartDate1": "2026-03-09T00:00:00+00:00",

        "EndDate1": "2026-03-09T03:30:00+00:00"

      },

      {

        "ScheduleCode": 100003,

        "Description": "00:00-03:45",

        "Legend": "R000",

        "DayType": 0,

        "ScheduleWeight": 225,

        "StartDate1": "2026-03-09T00:00:00+00:00",

        "EndDate1": "2026-03-09T03:45:00+00:00"

      },

      {

        "ScheduleCode": 100004,

        "Description": "00:00-04:00",

        "Legend": "R000",

        "DayType": 0,

        "ScheduleWeight": 240,

        "StartDate1": "2026-03-09T00:00:00+00:00",

        "EndDate1": "2026-03-09T04:00:00+00:00"

      },

      }

  "InpServiceLevelDetail": {

    "InpServiceLevelByDays": \[

      {

        "RosterCode": "0533",

        "TableName": "Task",

        "TableValue": "7",

        "Date": "2025-12-01T00:00:00",

        "TotalValue": 770.0,

        "MinimumValue": 770.0,

        "EmpiricValue": 0.0,

        "EstimatedValue": 0.0,

        "MaximumValue": 0.0

      },

      {

        "RosterCode": "0533",

        "TableName": "Task",

        "TableValue": "7",

        "Date": "2025-12-02T00:00:00",

        "TotalValue": 770.0,

        "MinimumValue": 770.0,

        "EmpiricValue": 0.0,

        "EstimatedValue": 0.0,

        "MaximumValue": 0.0

      },

      {

        "RosterCode": "0533",

        "TableName": "Task",

        "TableValue": "7",

        "Date": "2025-12-03T00:00:00",

        "TotalValue": 770.0,

        "MinimumValue": 770.0,

        "EmpiricValue": 0.0,

        "EstimatedValue": 0.0,

        "MaximumValue": 0.0

      },

      {

        "RosterCode": "0533",

        "TableName": "Task",

        "TableValue": "7",

        "Date": "2025-12-04T00:00:00",

        "TotalValue": 770.0,

        "MinimumValue": 770.0,

        "EmpiricValue": 0.0,

        "EstimatedValue": 0.0,

        "MaximumValue": 0.0

      },

      }

  "InpGenerationRules": {

    "InpGroupRulesIndexDatesToExecuteCollection": \[

      {

        "StartDate": "2025-12-01T00:00:00",

        "EndDate": "2025-12-07T00:00:00",

        "OrderGroupRuleIndex": 1,

        "GroupRuleIndexId": 2,

        "RuleIndexId": 4,

        "Order": 1

      },

      {

        "StartDate": "2025-12-01T00:00:00",

        "EndDate": "2025-12-07T00:00:00",

        "OrderGroupRuleIndex": 1,

        "GroupRuleIndexId": 2,

        "RuleIndexId": 16,

        "Order": 2

      },

      {

        "StartDate": "2025-12-01T00:00:00",

        "EndDate": "2025-12-07T00:00:00",

        "OrderGroupRuleIndex": 1,

        "GroupRuleIndexId": 2,

        "RuleIndexId": 5,

        "Order": 3

      },

      {

        "StartDate": "2025-12-01T00:00:00",

        "EndDate": "2025-12-07T00:00:00",

        "OrderGroupRuleIndex": 1,

        "GroupRuleIndexId": 2,

        "RuleIndexId": 1,

        "Order": 4

      },

      }

      }

 

 

