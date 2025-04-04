Prefs= {[1]
    [1]
    [1]
    [1]
    [1 2]
    [1 2]
    [1]
    [1]
    [1]
    [1]
    [1]
    [1]
    [2 1]
    [2 1]
    [2 1]};

nTrabs= length(Prefs); % No. de trabalhadores
nDias= 365;            % No. de dias do ano
nDiasFerias= 30;       % No. de dias de férias
nDiasTrabalho= 223;    % No. de dias de trabalho
nDiasTrabalhoFDS= 22;  % No. máximo de dias de trabalho aos fins-de-semana
nDiasSeguidos= 5;      % No. máximo de dias de trabalho seguidos
nMinTrabs= 2;          % No. mínimo de trabalhadores por dia

% Criar 'Ferias' com os mapas de férias de cada trabalhador (booleanos):
% Criar 'dias' com os dias que não são férias de cada trabalhoador (inteiros):
Ferias= false(nTrabs,nDias); 
dias= zeros(nTrabs,nDias-nDiasFerias);
init= 1;
for i= 1:nTrabs
    Ferias(i,init:init+nDiasFerias-1)= true;
    dias(i,:)= find(Ferias(i,:)==false);
    init= init + 23;
end

% Criar 'fds' com os dias que são fins de semana (booleanos)
fds= false(nTrabs,nDias);
fds(:,4:7:end)= true;
fds(:,5:7:end)= true;

% Criar constantes 'manha' 'tarde' e 'folga'
manha= 1;
tarde= 2;
folga= 0;

% Gerar aleatoriamente um horário com o número de dias de trabalho sem
% calhar em dias de férias (0 ou 1):
horario= zeros(nTrabs,nDias);
for i= 1:nTrabs
    aux= sort(randperm(nDias-nDiasFerias,nDiasTrabalho));
    aux= dias(i,aux);
    horario(i,aux)= 1;
end

% Critério 1 - no. de sequencias de dias de trabalho com mais de
%                'nDiasSeguidos' dias
% Critério 2 - no. dias de trabalho nos fins-de-semana acima dos
%                'nDiasTrabalhoFDS' por trabalhador
% Criterio 3 - no. de dias com no. de trabalhadores menor que 'nMinTrabs'

f1_opt = criterio1(horario,nDiasSeguidos);
f2_opt= criterio2(horario,fds,nDiasTrabalhoFDS);
f3_opt= criterio3(horario,nMinTrabs)
[f1_opt;f2_opt]
t= tic;
cont= 0;
while toc(t)<120 && (sum(f1_opt)>0 || sum(f2_opt)>0)
    cont= cont + 1;
    i= randi(nTrabs);  % Escolha do trabalhador
    aux= randperm(nDias-nDiasFerias,2); %
    dia1= dias(i,aux(1));
    dia2= dias(i,aux(2));
    if horario(i,dia1)~=horario(i,dia2)
        hor= horario;
        t1= hor(i,dia1);
        hor(i,dia1)= hor(i,dia2);
        hor(i,dia2)= t1;
        f1 = criterio1(hor,nDiasSeguidos);
        f2= criterio2(hor,fds,nDiasTrabalhoFDS);
        f3= criterio3(hor,nMinTrabs);
        if f1(i) + f2(i) + f3 < f1_opt(i) + f2_opt(i) + f3_opt
            f1_opt(i)= f1(i);
            f2_opt(i)= f2(i);
            f3_opt= f3;
            horario= hor;
        end
    end
end
toc(t)
cont
[f1_opt;f2_opt]
f3_opt

function f1 = criterio1(horario,nDiasSeguidos)
    nTrabs= size(horario,1);
    nDias= size(horario,2);
    f1= zeros(1,nTrabs);
    for i= 1:nTrabs
        for j= 1:nDias-nDiasSeguidos
            if sum(horario(i,j:j+nDiasSeguidos)) == nDiasSeguidos + 1
                f1(i)= f1(i) + 1;
            end
        end
    end
end

function f2 = criterio2(horario,fds,nDiasTrabalhoFDS)
    f2= sum(horario.*fds,2)';
    f2= f2 - nDiasTrabalhoFDS;
    f2(f2<0)= 0;
end

function f3 = criterio3(horario,nMinTrabs)
    f3= sum(horario);
    f3= sum(f3<nMinTrabs);
end