**Importação da estrutura de dados do schedule generator**

O formato usado para importação/exportação de dados do schedule generator é o JSON.

**Estrutura JSON**

**Exemplo de Payload JSON – OutRosterTeamDays e OutScheduleUseds**

O exemplo seguinte representa a estrutura de dados utilizada para envio de informação relativa a equipas *OutRosterTeamDays* e horários utilizados *OutScheduleUseds*.

Esta estrutura representa um modelo hierárquico de quadro:

Quadro \-\> Horários → Colaboradores → Dias

Os arrays representam coleções de:

* horários disponíveis

* colaboradores

* dias por colaborador

Há campos opcionais que podem ou não estar presentes, dependendo da configuração.

A nomenclatura dos campos é feita através da contração de palavras, em Inglês, por forma a facilitar o seu reconhecimento e contexto de utilização.

Tipos d e dados:

| Tipos de dados | Descrição |
| :---- | :---- |
| array | matriz |
| string | texto |
| integer | número inteiro |
| float | número real |
| boolean | Verdade/Falso |
| date | Data no formato YYYY-MM-DD |
| datetime | Data e hora no formato ISO8601  |

**Descrição**

* **OutRosterTeamDays**: Contém a lista de dias planeados por colaborador, incluindo tarefas e responsabilidades associadas.

* **OutScheduleUseds**: Contém a definição dos horários utilizados, incluindo períodos e pesos associados.

 

**Estrutura:**

* **OutRosterTeamDays: \[**

  * **RosterCode**: código numérico do quadro \- string;

  * **TeamCode**: código numérico da equipa \- string;

  * **EmployeeCode**: código numérico do empregado \- string;

  * **Date**: data em processo \- YYYY-MM-DD;

  * **ScheduleCode**: código numérico do horário \- integer,

  * **OutRosterTeamDayTasks**: **\[**

    * TaskID: **\[** código numérico da Tarefa \- string;

      * StartDate: data inicial para a execução da tarefa \- YYYY-MM-DDThh:mm:ss

      * EndDate: data final para a execução da tarefa \- YYYY-MM-DDThh:mm:ss

      * **\]**

    * **\]**

  * **OutRosterTeamDayResponsibilities**: **\[**

    * ResponsibilityCode: código numérico da Responsabilidade \- string;

    * **\]**

  * **\]**

* **OutScheduleUseds: \[**

  * **ScheduleCode**: código numérico do **horário** \- integer;

  * **DayType**: código numérico do **tipo de dia** \- integer, 

  * **ScheduleWeight**: peso do horário (h/dia) \- integer

  * **(Optional-1)** **\[**

    * StartDate1 **data inicial** do horário \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate1 **data final** do horário \- YYYY-MM-DDThh:mm:ss \- string;

    * **\]**

  * **(Optional-2)** **\[**

    * StartDate2 **data inicial** do horário \- YYYY-MM-DDThh:mm:ss \- string;

    * EndDate2 **data final** do horário \- YYYY-MM-DDThh:mm:ss \- string;

    * **\]**

  * **\]**

**Exemplo:**

{

  "OutRosterTeamDays": \[

    {

      "RosterCode": código numérico do quadro, em formato string ,

      "TeamCode": código numérico da equipa, em formato string ,

      "EmployeeCode": código numérico empregado, em formato string ,

      "Date": Data em processo, no formato  YYYY-MM-DD,

      "ScheduleCode": código numerico do horário, em formato integer,

      "OutRosterTeamDayTasks": \[

        {

          "TaskID": "8",

          "StartDate": "2025-12-01T07:30:00",

          "EndDate": "2025-12-01T09:30:00"

        },

        {

          "TaskID": "14",

          "StartDate": "2025-12-01T09:30:00",

          "EndDate": "2025-12-01T13:00:00"

        },

        {

          "TaskID": "1",

          "StartDate": "2025-12-01T18:15:00",

          "EndDate": "2025-12-01T21:00:00"

        }

      \],

      "OutRosterTeamDayResponsibilities": \[

        {

          "ResponsibilityCode": "02"

        },

        {

          "ResponsibilityCode": "01"

        }

      \]

    },

OutScheduleUseds: \[

    {

      "ScheduleCode": 1534,

      "DayType": 0,

      "ScheduleWeight": 400,

      "StartDate1": "2025-03-09T07:30:00",

      "EndDate1": "2026-03-09T14:00:00",

      "StartDate2": "2026-03-09T18:15:00",

      "EndDate2": "2026-03-09T21:15:00"

    },

    {

      "ScheduleCode": 1033,

      "DayType": 0,

      "ScheduleWeight": 390,

      "StartDate1": "2026-03-09T12:00:00",

      "EndDate1": "2026-03-09T19:00:00"

    },

    {

      "ScheduleCode": 1666,

      "DayType": 0,

      "ScheduleWeight": 480,

      "StartDate1": "2026-03-09T07:30:00",

      "EndDate1": "2026-03-09T14:00:00",

      "StartDate2": "2026-03-09T18:00:00",

      "EndDate2": "2026-03-09T21:00:00"

    },

    {

      "ScheduleCode": 1508,

      "DayType": 0,

      "ScheduleWeight": 465,

      "StartDate1": "2026-03-09T09:00:00",

      "EndDate1": "2026-03-09T13:00:00",

      "StartDate2": "2026-03-09T17:00:00",

      "EndDate2": "2026-03-09T21:15:00"

    },

    {

      "ScheduleCode": 2,

      "DayType": 1,

      "ScheduleWeight": 0

    },

    {

      "ScheduleCode": 3,

      "DayType": 2,

      "ScheduleWeight": 480

    }

  \]

  }

 

{

  "OutRosterTeamDays": \[

    {

      "RosterCode": "0533",

      "TeamCode": "09",

      "EmployeeCode": "15613",

      "Date": "2025-12-01",

      "ScheduleCode": 1534,

      "OutRosterTeamDayTasks": \[

        {

          "TaskID": "8",

          "StartDate": "2025-12-01T07:30:00",

          "EndDate": "2025-12-01T09:30:00"

        },

        {

          "TaskID": "14",

          "StartDate": "2025-12-01T09:30:00",

          "EndDate": "2025-12-01T13:00:00"

        },

        {

          "TaskID": "1",

          "StartDate": "2025-12-01T18:15:00",

          "EndDate": "2025-12-01T21:00:00"

        }

      \],

      "OutRosterTeamDayResponsibilities": \[

        {

          "ResponsibilityCode": "02"

        },

        {

          "ResponsibilityCode": "01"

        }

      \]

    },

"OutScheduleUseds": \[

    {

      "ScheduleCode": 1534,

      "DayType": 0,

      "ScheduleWeight": 400,

      "StartDate1": "2025-03-09T07:30:00",

      "EndDate1": "2026-03-09T14:00:00",

      "StartDate2": "2026-03-09T18:15:00",

      "EndDate2": "2026-03-09T21:15:00"

    },

    {

      "ScheduleCode": 1033,

      "DayType": 0,

      "ScheduleWeight": 390,

      "StartDate1": "2026-03-09T12:00:00",

      "EndDate1": "2026-03-09T19:00:00"

    },

    {

      "ScheduleCode": 1666,

      "DayType": 0,

      "ScheduleWeight": 480,

      "StartDate1": "2026-03-09T07:30:00",

      "EndDate1": "2026-03-09T14:00:00",

      "StartDate2": "2026-03-09T18:00:00",

      "EndDate2": "2026-03-09T21:00:00"

    },

    {

      "ScheduleCode": 1508,

      "DayType": 0,

      "ScheduleWeight": 465,

      "StartDate1": "2026-03-09T09:00:00",

      "EndDate1": "2026-03-09T13:00:00",

      "StartDate2": "2026-03-09T17:00:00",

      "EndDate2": "2026-03-09T21:15:00"

    },

    {

      "ScheduleCode": 2,

      "DayType": 1,

      "ScheduleWeight": 0

    },

    {

      "ScheduleCode": 3,

      "DayType": 2,

      "ScheduleWeight": 480

    }

  \]

  }

 

 

 

 

